import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app
import mobile_portal
import token_pool_settings


CURRENT_ID = "01a0201d-93fd-7682-a3e1-335a70661cc9"
CORRECT_CWD = r"D:\codex\codex-session-manager-windows\codex-session-manager-windows-main"


class FakeVar:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value


def make_mobile_session() -> mobile_portal.SessionItem:
    return mobile_portal.SessionItem(
        session_id=CURRENT_ID,
        ts=1,
        text="current",
        note="",
        history_count=1,
        cwd=r"D:\paper",
        model="gpt-5.6-sol",
        approval_policy="never",
        sandbox_mode="danger-full-access",
        turn_id="",
        session_file="",
        reasoning_effort="max",
    )


class SessionCwdOverrideTests(unittest.TestCase):
    def test_mobile_session_override_replaces_rollout_cwd(self) -> None:
        items = mobile_portal.apply_session_overrides(
            [make_mobile_session()],
            {CURRENT_ID: {"cwd": CORRECT_CWD}},
        )

        self.assertEqual(CORRECT_CWD, items[0].cwd)

    def test_mobile_setting_update_preserves_cwd_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "session_settings.json"
            settings_file.write_text(
                json.dumps({CURRENT_ID: {"cwd": CORRECT_CWD}}),
                encoding="utf-8",
            )
            with mock.patch.object(mobile_portal, "SETTINGS_FILE", settings_file):
                store = mobile_portal.CodexDataStore()
                store.set_session_settings(
                    CURRENT_ID,
                    "gpt-5.6-sol",
                    "never",
                    "danger-full-access",
                    "max",
                )
                saved = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(CORRECT_CWD, saved[CURRENT_ID]["cwd"])

    def test_desktop_loader_uses_cwd_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_file = root / "history.jsonl"
            settings_file = root / "session_settings.json"
            history_file.write_text(
                json.dumps({"session_id": CURRENT_ID, "ts": 1, "text": "current"}) + "\n",
                encoding="utf-8",
            )
            settings_file.write_text(
                json.dumps({CURRENT_ID: {"cwd": CORRECT_CWD}}),
                encoding="utf-8",
            )
            manager = object.__new__(app.SessionManagerApp)
            manager.items = []
            manager.session_notes = {}
            manager._history_signature = None
            manager._find_session_file = mock.Mock(return_value="rollout.jsonl")
            manager._extract_session_details = mock.Mock(return_value={"cwd": r"D:\paper"})

            with (
                mock.patch.object(app, "HISTORY_FILE", history_file),
                mock.patch.object(app, "SETTINGS_FILE", settings_file, create=True),
            ):
                items = manager._load_sessions(force=True)

        self.assertEqual(CORRECT_CWD, items[0].cwd)

    def test_resume_commands_force_the_session_cwd_override(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.use_global_defaults_var = FakeVar(False)
        manager.model_var = FakeVar("gpt-5.6-sol")
        manager.approval_var = FakeVar("never")
        manager.sandbox_var = FakeVar("danger-full-access")
        manager.reasoning_effort_var = FakeVar("max")
        manager.search_var = FakeVar(False)
        item = app.SessionItem(
            session_id=CURRENT_ID,
            ts=1,
            text="current",
            note="",
            history_count=1,
            cwd=CORRECT_CWD,
            model="gpt-5.6-sol",
            approval_policy="never",
            sandbox_mode="danger-full-access",
            turn_id="",
            session_file="",
        )
        backend = {"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        with (
            mock.patch.object(token_pool_settings, "build_codex_auth_model_catalog_override_args", return_value=[]),
            mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"),
        ):
            desktop_args = manager._build_codex_resume_args(item, backend)
            with tempfile.TemporaryDirectory() as temp_dir:
                settings_file = Path(temp_dir) / "backend.json"
                token_pool_settings.save_backend_settings(
                    backend_mode=token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                    settings_file=settings_file,
                )
                mobile_args = mobile_portal.build_resume_args(
                    Path(temp_dir) / "output.json",
                    CURRENT_ID,
                    "continue",
                    "gpt-5.6-sol",
                    "default",
                    "default",
                    "default",
                    backend_settings_file=settings_file,
                    cwd=CORRECT_CWD,
                )

        self.assertIn(["-C", CORRECT_CWD], [desktop_args[i:i + 2] for i in range(len(desktop_args) - 1)])
        self.assertIn(["-C", CORRECT_CWD], [mobile_args[i:i + 2] for i in range(len(mobile_args) - 1)])


if __name__ == "__main__":
    unittest.main()
