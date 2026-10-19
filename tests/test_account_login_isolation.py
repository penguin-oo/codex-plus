import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app
import auth_slots
import mobile_portal


class AccountLoginIsolationTests(unittest.TestCase):
    def test_binding_current_account_does_not_replace_newer_slot_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_home = Path(temp_dir) / "codex-home"
            slots_dir = base_home / "account_slots"
            account_home = slots_dir / "slot-2"
            account_home.mkdir(parents=True)
            auth_slots.save_slot_registry([{"slot_id": "slot-2", "label": "Account 2"}], slots_dir=slots_dir)
            current_auth = base_home / "auth.json"
            saved_auth = account_home / "auth.json"
            current_auth.write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "old"}}),
                encoding="utf-8",
            )
            saved_auth.write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "new"}}),
                encoding="utf-8",
            )
            os.utime(current_auth, ns=(1_000_000_000, 1_000_000_000))
            os.utime(saved_auth, ns=(2_000_000_000, 2_000_000_000))

            with mock.patch.object(auth_slots, "CODEX_HOME", base_home):
                auth_slots.save_current_auth_to_slot("slot-2", codex_home=base_home, slots_dir=slots_dir)

            self.assertEqual("new", json.loads(saved_auth.read_text(encoding="utf-8"))["tokens"]["refresh_token"])

    def test_mobile_refresh_uses_selected_slot_auth_not_stale_global_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_home = Path(temp_dir) / "codex-home"
            slots_dir = base_home / "account_slots"
            account_home = slots_dir / "slot-2"
            account_home.mkdir(parents=True)
            (account_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "new"}}),
                encoding="utf-8",
            )
            (base_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "old"}}),
                encoding="utf-8",
            )
            service = object.__new__(mobile_portal.PortalService)
            service.proxy_settings_file = base_home / "mobile-settings.json"
            with (
                mock.patch.object(mobile_portal, "CODEX_HOME", base_home),
                mock.patch.object(mobile_portal.auth_slots, "detect_active_slot", return_value="slot-2"),
                mock.patch.object(mobile_portal, "refresh_current_chatgpt_auth", return_value={"status": "ok"}) as refresh,
                mock.patch.object(mobile_portal.auth_slots, "switch_to_auth_slot") as switch,
                mock.patch.object(service, "request_desktop_refresh"),
                mock.patch.object(service, "account_slots_payload", return_value={"ok": True}),
            ):
                service.refresh_current_account()

            self.assertEqual(account_home / "auth.json", refresh.call_args.kwargs["auth_file"])
            switch.assert_called_once()

    def test_active_slot_survives_refresh_in_persistent_account_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_home = Path(temp_dir) / "codex-home"
            slots_dir = base_home / "account_slots"
            account_home = slots_dir / "slot-2"
            account_home.mkdir(parents=True)
            auth_slots.save_slot_registry([{"slot_id": "slot-2", "label": "Account 2"}], slots_dir=slots_dir)
            (base_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "old"}}),
                encoding="utf-8",
            )
            (account_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "account-2", "refresh_token": "new"}}),
                encoding="utf-8",
            )
            self.assertEqual("slot-2", auth_slots.detect_active_slot(codex_home=base_home, slots_dir=slots_dir))

    def test_login_binding_saves_installation_identity_with_slot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            login_home = root / "login-home"
            login_home.mkdir()
            (login_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "isolated-account"}}),
                encoding="utf-8",
            )
            (login_home / "installation_id").write_text("login-installation\n", encoding="utf-8")
            slots_dir = root / "account_slots"
            auth_slots.save_slot_registry([{"slot_id": "slot-2", "label": "Account 2"}], slots_dir=slots_dir)

            auth_slots.save_current_auth_to_slot("slot-2", codex_home=login_home, slots_dir=slots_dir)

            self.assertEqual(
                "login-installation",
                (slots_dir / "slot-2" / "installation_id").read_text(encoding="utf-8").strip(),
            )

    def test_desktop_login_binding_reads_auth_from_login_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            login_home = Path(temp_dir) / "login-home"
            login_home.mkdir()
            (login_home / "auth.json").write_text(
                json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "isolated-account"}}),
                encoding="utf-8",
            )
            result = subprocess.CompletedProcess(["codex.cmd", "login"], 0, stdout="")

            with mock.patch.object(
                app.auth_slots,
                "save_current_auth_to_slot",
                return_value={"slot_id": "slot-2"},
            ) as save_auth:
                bound = app.finalize_login_and_bind_account_slot(
                    "slot-2",
                    "",
                    result,
                    auth_home=login_home,
                )

            self.assertEqual({"slot_id": "slot-2"}, bound)
            save_auth.assert_called_once_with("slot-2", codex_home=login_home)

    def test_mobile_login_binding_passes_isolated_home_to_slot_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_home = Path(temp_dir) / "codex-home"
            base_home.mkdir()
            settings_file = base_home / "mobile-settings.json"
            settings_file.write_text("{}", encoding="utf-8")
            service = object.__new__(mobile_portal.PortalService)
            service.proxy_settings_file = settings_file

            def fake_login(*, settings_file: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
                login_home = Path(env["CODEX_HOME"])
                (login_home / "auth.json").write_text(
                    json.dumps({"auth_mode": "chatgpt", "tokens": {"account_id": "isolated-account"}}),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(["codex.cmd", "login"], 0, stdout="")

            with (
                mock.patch.object(mobile_portal, "CODEX_HOME", base_home),
                mock.patch.object(mobile_portal, "build_codex_subprocess_env", return_value={}),
                mock.patch.object(mobile_portal, "run_codex_browser_login", side_effect=fake_login),
                mock.patch.object(mobile_portal.auth_slots, "load_slot_registry", return_value=[{"slot_id": "slot-2"}]),
                mock.patch.object(
                    mobile_portal.auth_slots,
                    "save_current_auth_to_slot",
                    return_value={"slot_id": "slot-2"},
                ) as save_auth,
                mock.patch.object(service, "has_running_jobs", return_value=False),
                mock.patch.object(service, "request_desktop_refresh"),
                mock.patch.object(service, "account_slots_payload", return_value={"ok": True}),
            ):
                payload = service.login_and_bind_account("slot-2")

            self.assertEqual({"ok": True}, payload)
            save_auth.assert_called_once()
            saved_home = save_auth.call_args.kwargs["codex_home"]
            self.assertNotEqual(base_home, saved_home)
            self.assertIn("window_profiles", str(saved_home))
            self.assertFalse(base_home.joinpath("auth.json").exists())


if __name__ == "__main__":
    unittest.main()
