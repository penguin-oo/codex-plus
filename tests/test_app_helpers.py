import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app


class AppHelperTests(unittest.TestCase):
    def test_public_product_name_is_codex_plus(self) -> None:
        self.assertEqual("Codex+", app.APP_TITLE)
        self.assertEqual("Codex+", app.mobile_portal.APP_TITLE)

    def test_desktop_ui_declares_refreshed_ttk_styles(self) -> None:
        source = Path(app.__file__).read_text(encoding="utf-8")

        self.assertIn("Toolbar.TFrame", source)
        self.assertIn("Primary.TButton", source)
        self.assertIn("Inspector.TLabelframe", source)
        self.assertIn("#f8fafc", source)

    def test_desktop_toolbar_and_launch_options_are_not_single_row_overflow(self) -> None:
        source = Path(app.__file__).read_text(encoding="utf-8")

        self.assertIn("toolbar_actions", source)
        self.assertIn("toolbar_context", source)
        self.assertIn("self.search_check.grid(row=2", source)
        self.assertIn("self.use_global_defaults_check.grid(row=2", source)

    def test_compact_status_message_limits_long_launch_paths(self) -> None:
        long_status = (
            "Started codex resume cwd="
            + "D:\\codex\\codex-session-manager-windows\\codex-session-manager-windows-main\\" * 3
            + " (admin, proxy)"
        )

        compact = app.compact_status_message(long_status)

        self.assertLessEqual(len(compact), app.MAX_DESKTOP_STATUS_CHARS)
        self.assertTrue(compact.startswith("Started codex resume cwd="))
        self.assertIn("...", compact)

    def test_account_status_label_is_compact_for_toolbar(self) -> None:
        label = app.format_account_status_label(
            "work",
            {"email": "very-long-account-name-for-toolbar-layout@example-with-a-long-domain.test"},
            {"label": "Primary Work Account"},
        )

        self.assertLessEqual(len(label), app.ACCOUNT_STATUS_DISPLAY_LIMIT)
        self.assertIn("...", label)

    def test_desktop_window_geometry_keeps_margin_on_small_scaled_displays(self) -> None:
        width, height = app.desktop_window_geometry(1280, 720)

        self.assertEqual((1040, 620), (width, height))

    def test_desktop_window_placement_uses_safe_initial_offset(self) -> None:
        self.assertEqual((1040, 620, 40, 40), app.desktop_window_placement(1280, 720))

    def test_default_launch_options_match_desktop_picker_defaults(self) -> None:
        self.assertEqual(
            {
                "model": "gpt-5.5",
                "approval": "never",
                "sandbox": "danger-full-access",
            },
            app.default_launch_options(),
        )
        self.assertFalse(app.DEFAULT_LAUNCH_ADMIN)

    def test_render_models_selects_primary_model_when_current_missing(self) -> None:
        class FakeVar:
            def __init__(self, value: str) -> None:
                self.value = value

            def get(self) -> str:
                return self.value

            def set(self, value: str) -> None:
                self.value = value

        manager = object.__new__(app.SessionManagerApp)
        manager.available_models = ["gpt-5.5", "gpt-5.4"]
        manager.model_box = {}
        manager.model_var = FakeVar("")

        app.SessionManagerApp._render_models(manager)

        self.assertEqual("gpt-5.5", manager.model_var.get())
        self.assertEqual(["default", "gpt-5.5", "gpt-5.4"], manager.model_box["values"])

    def test_update_details_panel_preserves_focused_note_draft(self) -> None:
        class FakeVar:
            def __init__(self, value: str) -> None:
                self.value = value

            def get(self) -> str:
                return self.value

            def set(self, value: str) -> None:
                self.value = value

        class FakeWidget:
            def configure(self, **_kwargs: object) -> None:
                pass

            def delete(self, *_args: object) -> None:
                pass

            def insert(self, *_args: object) -> None:
                pass

        class FakeTree:
            def selection(self) -> list[str]:
                return ["session-1"]

        note_entry = FakeWidget()
        manager = object.__new__(app.SessionManagerApp)
        manager.tree = FakeTree()
        manager.note_entry = note_entry
        manager.note_var = FakeVar("draft note")
        manager.details_text = FakeWidget()
        manager.root = mock.Mock()
        manager.root.focus_get.return_value = note_entry
        manager.session_notes = {"session-1": "saved note"}
        manager.item_by_id = {
            "session-1": app.SessionItem(
                session_id="session-1",
                ts=1,
                text="hello",
                note="saved note",
                history_count=1,
                cwd="",
                model="",
                approval_policy="",
                sandbox_mode="",
                turn_id="",
                session_file="",
            )
        }

        app.SessionManagerApp._update_details_panel(manager)

        self.assertEqual("draft note", manager.note_var.get())

    def test_path_signature_reads_mtime_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "history.jsonl"
            target.write_text("hello", encoding="utf-8")

            signature = app.path_signature(target)

            self.assertIsNotNone(signature)
            self.assertEqual(target.stat().st_size, signature[1])

    def test_primary_session_jsonl_name_rejects_recovery_artifacts(self) -> None:
        self.assertTrue(app.is_primary_session_jsonl_name("rollout-session-1.jsonl"))
        self.assertFalse(app.is_primary_session_jsonl_name("rollout-session-1.jsonl.context-overflow-backup-20260507-010101.jsonl"))
        self.assertFalse(app.is_primary_session_jsonl_name("rollout-session-1.jsonl.restore-current-backup-20260507-010101.jsonl"))
        self.assertFalse(app.is_primary_session_jsonl_name("rollout-session-1.jsonl.merged-restore-candidate-20260507-010101.jsonl"))
        self.assertFalse(app.is_primary_session_jsonl_name("rollout-session-1.jsonl.full-restored-archive-20260507-010101.jsonl"))

    def test_apply_session_notes_updates_matching_items_only(self) -> None:
        items = [
            app.SessionItem(
                session_id="session-1",
                ts=1,
                text="hello",
                note="old",
                history_count=1,
                cwd="",
                model="",
                approval_policy="",
                sandbox_mode="",
                turn_id="",
                session_file="",
            ),
            app.SessionItem(
                session_id="session-2",
                ts=2,
                text="world",
                note="keep",
                history_count=2,
                cwd="",
                model="",
                approval_policy="",
                sandbox_mode="",
                turn_id="",
                session_file="",
            ),
        ]

        updated = app.apply_session_notes(items, {"session-1": "new"})

        self.assertEqual("new", updated[0].note)
        self.assertEqual("keep", updated[1].note)
        self.assertEqual("old", items[0].note)

    def test_terminal_proxy_schemes_include_socks5h(self) -> None:
        self.assertIn("socks5h", app.TERMINAL_PROXY_SCHEMES)

    def test_build_start_process_command_uses_no_profile(self) -> None:
        command = app.build_start_process_command(
            ps_command="Write-Host 'hello'",
            run_as_admin=True,
        )

        self.assertIn("-Verb RunAs", command)
        self.assertIn("'-NoProfile'", command)
        self.assertIn("'-NoExit'", command)
        self.assertIn("'-EncodedCommand'", command)

    def test_build_start_process_command_prefers_windows_terminal(self) -> None:
        with mock.patch.object(app.shutil, "which", side_effect=lambda name: {
            "wt.exe": "C:\\Users\\me\\AppData\\Local\\Microsoft\\WindowsApps\\wt.exe",
            "pwsh.exe": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        }.get(name)):
            command = app.build_start_process_command(
                ps_command="Write-Host 'hello'",
                run_as_admin=False,
            )

        self.assertIn("Start-Process 'wt.exe'", command)
        self.assertIn("'new-tab'", command)
        self.assertIn("'--title'", command)
        self.assertIn("'Codex'", command)
        self.assertIn("'pwsh.exe'", command)
        self.assertIn("'-NoLogo'", command)
        self.assertIn("'-NoExit'", command)
        self.assertIn("'-EncodedCommand'", command)
        self.assertNotIn("Write-Host ''hello''", command)

    def test_build_start_process_command_falls_back_to_windows_powershell_without_pwsh(self) -> None:
        with mock.patch.object(app.shutil, "which", side_effect=lambda _name: None):
            command = app.build_start_process_command(
                ps_command="Write-Host 'hello'",
                run_as_admin=False,
            )

        self.assertIn("Start-Process 'powershell.exe'", command)
        self.assertIn("'-NoLogo'", command)
        self.assertIn("'-NoProfile'", command)
        self.assertIn("'-NoExit'", command)

    def test_launch_terminal_command_uses_windows_terminal_without_admin(self) -> None:
        with mock.patch.object(app.shutil, "which", side_effect=lambda name: {
            "wt.exe": "wt.exe",
            "pwsh.exe": "pwsh.exe",
        }.get(name)), \
                mock.patch.object(app.subprocess, "Popen") as popen:
            app.launch_terminal_command("Write-Host 'hello'", run_as_admin=False)

        popen.assert_called_once()
        args, kwargs = popen.call_args
        self.assertEqual(
            [
                "wt.exe",
                "new-tab",
                "--title",
                "Codex",
                "--",
                "pwsh.exe",
                "-NoLogo",
                "-NoProfile",
                "-NoExit",
                "-EncodedCommand",
                app._encode_powershell_command("Write-Host 'hello'"),
            ],
            args[0],
        )
        self.assertNotIn("creationflags", kwargs)

    def test_launch_terminal_command_falls_back_to_direct_pwsh_when_windows_terminal_fails(self) -> None:
        with mock.patch.object(app.shutil, "which", side_effect=lambda name: {
            "wt.exe": "wt.exe",
            "pwsh.exe": "pwsh.exe",
        }.get(name)), \
                mock.patch.object(app.subprocess, "Popen", side_effect=[OSError("wt failed"), mock.DEFAULT]) as popen:
            app.launch_terminal_command("Write-Host 'hello'", run_as_admin=False)

        self.assertEqual(2, popen.call_count)
        args, kwargs = popen.call_args
        self.assertEqual(
            ["pwsh.exe", "-NoLogo", "-NoProfile", "-NoExit", "-Command", "Write-Host 'hello'"],
            args[0],
        )
        self.assertEqual(getattr(app.subprocess, "CREATE_NEW_CONSOLE", 0), kwargs.get("creationflags"))

    def test_launch_terminal_command_uses_powershell_for_admin_elevation(self) -> None:
        with mock.patch.object(app.shutil, "which", side_effect=lambda name: {
            "wt.exe": "wt.exe",
            "pwsh.exe": "pwsh.exe",
        }.get(name)), \
                mock.patch.object(app.subprocess, "Popen") as popen:
            app.launch_terminal_command("Write-Host 'hello'", run_as_admin=True)

        popen.assert_called_once()
        args, _kwargs = popen.call_args
        self.assertEqual("powershell.exe", args[0][0])
        self.assertIn("-ExecutionPolicy", args[0])
        self.assertIn("Start-Process 'wt.exe' -Verb RunAs", args[0][-1])
        self.assertIn("'new-tab'", args[0][-1])
        self.assertIn("'pwsh.exe'", args[0][-1])
        self.assertIn("'-EncodedCommand'", args[0][-1])

    def test_build_proxy_environment_ps_prefix_clears_proxy_when_disabled(self) -> None:
        prefix = app.build_proxy_environment_ps_prefix(
            enabled=False,
            scheme="socks5h",
            host="127.0.0.1",
            port_text="7897",
        )

        self.assertIn("$env:HTTP_PROXY=$null", prefix)
        self.assertIn("$env:ALL_PROXY=$null", prefix)

    def test_build_proxy_environment_ps_prefix_supports_socks5h(self) -> None:
        prefix = app.build_proxy_environment_ps_prefix(
            enabled=True,
            scheme="socks5h",
            host="127.0.0.1",
            port_text="7897",
        )

        self.assertIn("socks5h://127.0.0.1:7897", prefix)

    def test_format_account_status_label_uses_active_slot_name(self) -> None:
        label = app.format_account_status_label(
            "account-a",
            {"email": "a@example.com", "account_id": "acct-a"},
        )

        self.assertEqual("Auth: Account A | a@example.com", label)

    def test_format_account_slot_summary_marks_unbound_slots(self) -> None:
        summary = app.format_account_slot_summary("account-b", {}, None)

        self.assertIn("Account B", summary)
        self.assertIn("Not bound yet.", summary)

    def test_format_account_slot_summary_prefers_dynamic_label(self) -> None:
        summary = app.format_account_slot_summary(
            "slot-3",
            {"label": "Travel", "email": "travel@example.com", "auth_mode": "chatgpt", "fingerprint": "abc"},
            None,
        )

        self.assertIn("Travel", summary)
        self.assertNotIn("slot-3", summary)

    def test_slot_supports_direct_login_only_for_unbound_slots(self) -> None:
        self.assertTrue(app.slot_supports_direct_login({}))
        self.assertTrue(app.slot_supports_direct_login({"fingerprint": ""}))
        self.assertFalse(app.slot_supports_direct_login({"fingerprint": "bound"}))

    def test_format_quota_summary_uses_backend_text(self) -> None:
        summary = app.format_account_quota_summary({"summary": "Weekly quota: 76% used", "state": "ok"})

        self.assertEqual("Weekly quota: 76% used", summary)

    def test_account_dialog_dimensions_fit_within_screen(self) -> None:
        width, height = app.account_dialog_dimensions(screen_width=1920, screen_height=1080)

        self.assertEqual((720, 820), (width, height))

    def test_account_dialog_dimensions_keep_small_screens_usable(self) -> None:
        width, height = app.account_dialog_dimensions(screen_width=640, screen_height=480)

        self.assertEqual((560, 400), (width, height))

    def test_merge_available_models_promotes_gpt_5_5_without_losing_cached_entries(self) -> None:
        models = app.merge_available_models(["gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex"])

        self.assertEqual(
            ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.2", "gpt-5"],
            models,
        )

    def test_build_codex_new_args_defaults_backend_override_to_gpt_5_5(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.model_var = mock.Mock()
        manager.model_var.get.return_value = "default"
        manager._token_pool_settings = mock.Mock(return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_TOKEN_POOL})
        manager._build_codex_override_args = mock.Mock(return_value=[])
        manager._build_backend_override_args = mock.Mock(return_value=[])

        app.SessionManagerApp._build_codex_new_args(manager)

        manager._build_backend_override_args.assert_called_once_with("gpt-5.5")

    def test_build_codex_override_args_applies_launch_defaults_when_global_defaults_enabled(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.use_global_defaults_var = mock.Mock()
        manager.use_global_defaults_var.get.return_value = True
        manager.model_var = mock.Mock()
        manager.model_var.get.return_value = "default"
        manager.approval_var = mock.Mock()
        manager.approval_var.get.return_value = "default"
        manager.sandbox_var = mock.Mock()
        manager.sandbox_var.get.return_value = "default"
        manager.search_var = mock.Mock()
        manager.search_var.get.return_value = True
        manager.reasoning_effort_var = mock.Mock()
        manager.reasoning_effort_var.get.return_value = "xhigh"
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        )

        args = app.SessionManagerApp._build_codex_override_args(manager)

        self.assertEqual(["-m", "gpt-5.5", "-a", "never", "-s", "danger-full-access"], args)

    def test_build_codex_override_args_ignores_desktop_model_when_openai_compatible_enabled(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.use_global_defaults_var = mock.Mock()
        manager.use_global_defaults_var.get.return_value = False
        manager.model_var = mock.Mock()
        manager.model_var.get.return_value = "gpt-5.5"
        manager.approval_var = mock.Mock()
        manager.approval_var.get.return_value = "default"
        manager.sandbox_var = mock.Mock()
        manager.sandbox_var.get.return_value = "default"
        manager.search_var = mock.Mock()
        manager.search_var.get.return_value = False
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE}
        )

        args = app.SessionManagerApp._build_codex_override_args(manager)

        self.assertEqual([], args)

    def test_build_codex_resume_args_prefers_saved_openai_model_over_session_model(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._build_codex_override_args = mock.Mock(return_value=[])
        manager._build_backend_override_args = mock.Mock(return_value=["BACKEND"])
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "openai_model": "mimo-v2.5-pro",
            }
        )

        item = app.SessionItem(
            session_id="session-1",
            ts=1,
            text="hello",
            note="",
            history_count=1,
            cwd="D:\\stock",
            model="gpt-5.5",
            approval_policy="never",
            sandbox_mode="danger-full-access",
            turn_id="",
            session_file="",
        )

        args = app.SessionManagerApp._build_codex_resume_args(manager, item)

        manager._build_backend_override_args.assert_called_once_with("mimo-v2.5-pro")
        self.assertIn("-m", args)
        self.assertIn("mimo-v2.5-pro", args)
        self.assertNotIn("gpt-5.5", args)
        self.assertEqual(["codex.cmd", "resume", "session-1", "-m", "mimo-v2.5-pro", "BACKEND"], args)

    def test_build_codex_new_args_prefers_saved_openai_model_over_desktop_picker(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.model_var = mock.Mock()
        manager.model_var.get.return_value = "gpt-5.5"
        manager._build_codex_override_args = mock.Mock(return_value=[])
        manager._build_backend_override_args = mock.Mock(return_value=["BACKEND"])
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "openai_model": "mimo-v2.5-pro",
            }
        )

        args = app.SessionManagerApp._build_codex_new_args(manager)

        manager._build_backend_override_args.assert_called_once_with("mimo-v2.5-pro")
        self.assertIn("-m", args)
        self.assertIn("mimo-v2.5-pro", args)
        self.assertNotIn("gpt-5.5", args)
        self.assertEqual(["codex.cmd", "-m", "mimo-v2.5-pro", "BACKEND"], args)

    def test_build_token_pool_provider_override_args_points_codex_to_local_proxy(self) -> None:
        args = app.build_token_pool_provider_override_args(
            model="gpt-5.4",
            proxy_port=8317,
            provider_name="built_in_token_pool",
            env_key_name="CODEX_TOKEN_POOL_API_KEY",
        )

        rendered = " ".join(args)
        self.assertIn('model_provider="built_in_token_pool"', rendered)
        self.assertIn('model_providers.built_in_token_pool.base_url="http://127.0.0.1:8317"', rendered)
        self.assertIn('model_providers.built_in_token_pool.env_key="CODEX_TOKEN_POOL_API_KEY"', rendered)
        self.assertIn('model_providers.built_in_token_pool.wire_api="responses"', rendered)
        self.assertIn('model_providers.built_in_token_pool.requires_openai_auth=false', rendered)
        self.assertIn('model_providers.built_in_token_pool.supports_websockets=false', rendered)

    def test_build_token_pool_environment_ps_prefix_sets_local_api_key(self) -> None:
        prefix = app.build_token_pool_environment_ps_prefix(
            env_key_name="CODEX_TOKEN_POOL_API_KEY",
            api_key_value="local-proxy-key",
        )

        self.assertIn("$env:CODEX_TOKEN_POOL_API_KEY='local-proxy-key'", prefix)

    def test_build_openai_compatible_ps_prefix_uses_local_proxy_api_key(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "proxy_api_key": "local-proxy-key",
                "openai_api_key": "test-upstream-key",
            }
        )

        prefix = app.SessionManagerApp._build_openai_compatible_ps_prefix(manager)

        self.assertIn("$env:CODEX_OPENAI_COMPATIBLE_API_KEY='test-upstream-key'", prefix)
        self.assertNotIn("local-proxy-key", prefix)

    def test_build_openai_compatible_provider_override_args_points_codex_to_custom_base_url(self) -> None:
        args = app.build_openai_compatible_provider_override_args(
            model="gpt-5.5",
            base_url="https://api.openai.com/v1",
            provider_name="openai_compatible",
            env_key_name="CODEX_OPENAI_COMPATIBLE_API_KEY",
        )

        rendered = " ".join(args)
        self.assertIn('model_provider="openai_compatible"', rendered)
        self.assertIn('model_providers.openai_compatible.base_url="https://api.openai.com/v1"', rendered)
        self.assertIn('model_providers.openai_compatible.env_key="CODEX_OPENAI_COMPATIBLE_API_KEY"', rendered)
        self.assertIn('model_providers.openai_compatible.wire_api="responses"', rendered)

    def test_build_backend_override_args_for_codex_auth_forces_builtin_openai_provider(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        )

        args = app.SessionManagerApp._build_backend_override_args(manager, "gpt-5.5")

        self.assertEqual(["-c", 'model_provider="openai"'], args)

    def test_build_terminal_ps_command_for_codex_auth_clears_stale_api_environment(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        )
        manager.use_proxy_var = mock.Mock(get=lambda: False)
        manager.proxy_scheme_var = mock.Mock(get=lambda: "socks5h")
        manager.proxy_host_var = mock.Mock(get=lambda: "127.0.0.1")
        manager.proxy_port_var = mock.Mock(get=lambda: "7897")

        command = app.SessionManagerApp._build_terminal_ps_command(
            manager,
            "D:\\tools",
            ["codex.cmd", "-c", 'model_provider="openai"'],
        )

        self.assertIn("codex.cmd", command)
        self.assertIn("$env:CODEX_API_KEY=$null", command)
        self.assertIn("$env:OPENAI_API_KEY=$null", command)
        self.assertIn("$env:CODEX_OPENAI_COMPATIBLE_API_KEY=$null", command)
        self.assertIn("$env:CODEX_TOKEN_POOL_API_KEY=$null", command)
        self.assertNotIn("api.unity2.ai", command)

    def test_build_terminal_ps_command_resolves_codex_cmd_for_terminal_launch(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        )
        manager.use_proxy_var = mock.Mock(get=lambda: False)
        manager.proxy_scheme_var = mock.Mock(get=lambda: "socks5h")
        manager.proxy_host_var = mock.Mock(get=lambda: "127.0.0.1")
        manager.proxy_port_var = mock.Mock(get=lambda: "7897")

        with mock.patch.object(app.shutil, "which", return_value="C:\\Users\\me\\AppData\\Roaming\\npm\\codex.cmd"):
            command = app.SessionManagerApp._build_terminal_ps_command(
                manager,
                "D:\\tools",
                ["codex.cmd", "resume", "session-1"],
            )

        self.assertIn("& 'C:\\Users\\me\\AppData\\Roaming\\npm\\codex.cmd' 'resume' 'session-1'", command)

    def test_load_backend_settings_preserves_openai_compatible_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"

            saved = app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=Path(temp_dir) / "tokens",
                proxy_port=8317,
                proxy_api_key="pool-api-key",
                openai_base_url="https://api.openai.com/v1",
                openai_api_key="sk-test",
                openai_model="gpt-5.5",
                openai_models=["gpt-5.5", "gpt-5.4"],
                openai_protocol="responses",
            )
            loaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual(app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE, saved["backend_mode"])
        self.assertEqual("https://api.openai.com/v1", loaded["openai_base_url"])
        self.assertEqual("sk-test", loaded["openai_api_key"])
        self.assertEqual("gpt-5.5", loaded["openai_model"])
        self.assertEqual(["gpt-5.5", "gpt-5.4"], loaded["openai_models"])
        self.assertEqual("responses", loaded["openai_protocol"])

    def test_save_openai_compatible_backend_settings_forces_openai_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            token_dir.mkdir()
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key="pool-api-key",
            )

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                return_value={
                    "openai_base_url": "https://api.openai.com/v1",
                    "openai_api_key": "sk-test",
                    "openai_model": "gpt-5.5",
                    "openai_models": ["gpt-5.5", "gpt-5.4"],
                    "openai_protocol": "chat_completions",
                },
            ) as resolve_backend:
                updated = app.save_openai_compatible_backend_settings(
                    settings_file=settings_file,
                    token_dir=token_dir,
                    proxy_port=8317,
                    proxy_api_key="pool-api-key",
                    base_url="https://api.openai.com/v1",
                    api_key="sk-test",
                    model="gpt-5.5",
                )
            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        resolve_backend.assert_called_once_with(
            "https://api.openai.com/v1",
            "sk-test",
            "gpt-5.5",
        )
        self.assertEqual(app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE, updated["backend_mode"])
        self.assertEqual(app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE, reloaded["backend_mode"])
        self.assertEqual("https://api.openai.com/v1", reloaded["openai_base_url"])
        self.assertEqual("sk-test", reloaded["openai_api_key"])
        self.assertEqual("gpt-5.5", reloaded["openai_model"])
        self.assertEqual(["gpt-5.5", "gpt-5.4"], reloaded["openai_models"])
        self.assertEqual("chat_completions", reloaded["openai_protocol"])

    def test_save_openai_compatible_backend_settings_updates_named_active_preset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            token_dir.mkdir()
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key="pool-api-key",
            )

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                return_value={
                    "openai_base_url": "https://provider-a.example.test/v1",
                    "openai_api_key": "sk-test",
                    "openai_model": "gpt-5.5",
                    "openai_models": ["gpt-5.5"],
                    "openai_protocol": "responses",
                },
            ):
                app.save_openai_compatible_backend_settings(
                    settings_file=settings_file,
                    token_dir=token_dir,
                    proxy_port=8317,
                    proxy_api_key="pool-api-key",
                    base_url="https://provider-a.example.test/v1",
                    api_key="sk-test",
                    model="gpt-5.5",
                    preset_id="wanx",
                    preset_name="WanX",
                )

            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual("wanx", reloaded["active_openai_preset_id"])
        self.assertEqual("https://provider-a.example.test/v1", reloaded["openai_base_url"])
        self.assertEqual("gpt-5.5", reloaded["openai_model"])
        preset = next(item for item in reloaded["openai_presets"] if item["id"] == "wanx")
        self.assertEqual("WanX", preset["name"])
        self.assertEqual("https://provider-a.example.test/v1", preset["openai_base_url"])
        self.assertEqual("sk-test", preset["openai_api_key"])
        self.assertEqual("gpt-5.5", preset["openai_model"])
        self.assertEqual(["gpt-5.5"], preset["openai_models"])
        self.assertEqual("responses", preset["openai_protocol"])
        self.assertEqual([], preset["openai_manual_extra_models"])
        self.assertEqual("direct", preset["proxy_preference"])
        self.assertEqual("", preset["upstream_proxy_url"])

    def test_openai_account_form_values_use_active_preset_when_top_level_is_detached(self) -> None:
        settings = {
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": "",
            "openai_model": "",
            "openai_models": ["gpt-5.4"],
            "openai_protocol": "responses",
            "proxy_preference": "direct",
            "active_openai_preset_id": "day-60",
            "openai_config_detached_from_preset": True,
            "openai_presets": [
                {
                    "id": "day-60",
                    "name": "day-60",
                    "openai_base_url": "https://provider-b.example.test/codex",
                    "openai_api_key": "sk-day",
                    "openai_model": "gpt-5.5",
                    "openai_models": ["gpt-5.5", "gpt-5.4"],
                    "openai_protocol": "responses",
                    "proxy_preference": "proxy",
                }
            ],
        }

        values = app.openai_account_form_values(settings)

        self.assertEqual("https://provider-b.example.test/codex", values["openai_base_url"])
        self.assertEqual("sk-day", values["openai_api_key"])
        self.assertEqual("gpt-5.5", values["openai_model"])
        self.assertEqual(["gpt-5.5", "gpt-5.4"], values["openai_models"])
        self.assertEqual("proxy", values["proxy_preference"])

    def test_openai_api_key_entry_is_plain_text(self) -> None:
        self.assertEqual("", app.OPENAI_API_KEY_ENTRY_SHOW)

    def test_save_openai_compatible_preset_settings_preserves_current_backend_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key="pool-api-key",
            )

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                return_value={
                    "openai_base_url": "https://provider-b.example.test/codex",
                    "openai_api_key": "sk-day",
                    "openai_model": "gpt-5.5",
                    "openai_models": ["gpt-5.5"],
                    "openai_protocol": "responses",
                },
            ):
                updated = app.save_openai_compatible_preset_settings(
                    settings_file=settings_file,
                    base_url="https://provider-b.example.test/codex",
                    api_key="sk-day",
                    model="gpt-5.5",
                    preset_name="day-60",
                    proxy_preference="direct",
                    protocol_override="responses",
                )

            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual(app.token_pool_settings.BACKEND_MODE_CODEX_AUTH, updated["backend_mode"])
        self.assertEqual(app.token_pool_settings.BACKEND_MODE_CODEX_AUTH, reloaded["backend_mode"])
        self.assertEqual("day-60", updated["active_openai_preset_id"])
        self.assertEqual("sk-day", reloaded["openai_api_key"])

    def test_save_openai_compatible_backend_settings_derives_preset_id_from_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                return_value={
                    "openai_base_url": "https://api.example.com/v1",
                    "openai_api_key": "sk-test",
                    "openai_model": "gpt-5.5",
                    "openai_models": ["gpt-5.5"],
                    "openai_protocol": "responses",
                },
            ):
                app.save_openai_compatible_backend_settings(
                    settings_file=settings_file,
                    token_dir=token_dir,
                    proxy_port=8317,
                    proxy_api_key="pool-api-key",
                    base_url="https://api.example.com/v1",
                    api_key="sk-test",
                    model="",
                    preset_id="",
                    preset_name="Local Grok",
                )

            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual("local-grok", reloaded["active_openai_preset_id"])
        self.assertIn(
            {"id": "local-grok", "name": "Local Grok"},
            [{"id": item["id"], "name": item["name"]} for item in reloaded["openai_presets"]],
        )

    def test_apply_openai_compatible_preset_settings_restarts_stale_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=Path(temp_dir) / "tokens",
                proxy_port=8317,
                proxy_api_key="pool-api-key",
                openai_base_url="https://first.example/v1",
                openai_api_key="sk-first",
                openai_model="first-model",
                openai_models=["first-model"],
                openai_protocol="responses",
            )
            app.token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id="wanx",
                name="WanX",
                openai_base_url="https://provider-a.example.test/v1",
                openai_api_key="sk-wanx",
                openai_model="wanx-model",
                openai_models=["wanx-model"],
                openai_protocol="responses",
                set_active=False,
            )
            manager = object.__new__(app.SessionManagerApp)
            manager._stop_token_pool_proxy = mock.Mock()
            manager._start_openai_compatible_proxy = mock.Mock()
            manager._load_available_models = mock.Mock(return_value=["wanx-model"])
            manager._render_models = mock.Mock()

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                return_value={
                    "openai_base_url": "https://provider-a.example.test/v1",
                    "openai_api_key": "sk-wanx",
                    "openai_model": "wanx-model",
                    "openai_models": ["wanx-model"],
                    "openai_protocol": "responses",
                },
            ) as resolve_backend:
                updated = app.SessionManagerApp._apply_openai_compatible_preset_settings(
                    manager,
                    "wanx",
                    settings_file=settings_file,
                )

        self.assertEqual("wanx", updated["active_openai_preset_id"])
        self.assertEqual("wanx-model", updated["openai_model"])
        self.assertEqual("responses", updated["openai_protocol"])
        resolve_backend.assert_called_once_with("https://provider-a.example.test/v1", "sk-wanx", "wanx-model", upstream_proxy_url="")
        manager._stop_token_pool_proxy.assert_called_once_with()
        manager._start_openai_compatible_proxy.assert_not_called()
        manager._render_models.assert_called_once_with()

    def test_apply_openai_compatible_preset_settings_skips_validation_from_preset_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=Path(temp_dir) / "tokens",
                proxy_port=8317,
                proxy_api_key="pool-api-key",
                openai_base_url="https://first.example/v1",
                openai_api_key="sk-first",
                openai_model="first-model",
                openai_models=["first-model"],
                openai_protocol="responses",
            )
            app.token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id="private-provider",
                name="Private Provider",
                openai_base_url="https://private.example/v1",
                openai_api_key="sk-private",
                openai_model="private-model",
                openai_models=["private-model", "private-alt"],
                openai_protocol="responses",
                skip_validation=True,
                set_active=False,
            )
            manager = object.__new__(app.SessionManagerApp)
            manager._stop_token_pool_proxy = mock.Mock()
            manager._start_openai_compatible_proxy = mock.Mock()
            manager._load_available_models = mock.Mock(return_value=["private-model"])
            manager._render_models = mock.Mock()

            with mock.patch.object(app.token_pool_settings, "resolve_openai_compatible_backend_config") as resolve_backend:
                updated = app.SessionManagerApp._apply_openai_compatible_preset_settings(
                    manager,
                    "private-provider",
                    settings_file=settings_file,
                )

        resolve_backend.assert_not_called()
        self.assertEqual("private-provider", updated["active_openai_preset_id"])
        self.assertEqual("private-model", updated["openai_model"])
        self.assertEqual("responses", updated["openai_protocol"])

    def test_delete_openai_compatible_preset_settings_falls_back_and_restarts_proxy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=Path(temp_dir) / "tokens",
                proxy_port=8317,
                proxy_api_key="pool-api-key",
                openai_base_url="https://first.example/v1",
                openai_api_key="sk-first",
                openai_model="first-model",
                openai_models=["first-model"],
                openai_protocol="responses",
            )
            app.token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id="wanx",
                name="WanX",
                openai_base_url="https://provider-a.example.test/v1",
                openai_api_key="sk-wanx",
                openai_model="wanx-model",
                openai_models=["wanx-model"],
                openai_protocol="responses",
                set_active=True,
            )
            manager = object.__new__(app.SessionManagerApp)
            manager._stop_token_pool_proxy = mock.Mock()
            manager._start_openai_compatible_proxy = mock.Mock()
            manager._load_available_models = mock.Mock(return_value=["first-model"])
            manager._render_models = mock.Mock()

            updated = app.SessionManagerApp._delete_openai_compatible_preset_settings(
                manager,
                "wanx",
                settings_file=settings_file,
            )

        self.assertEqual("default", updated["active_openai_preset_id"])
        self.assertEqual(["default"], [item["id"] for item in updated["openai_presets"]])
        manager._stop_token_pool_proxy.assert_called_once_with()
        manager._start_openai_compatible_proxy.assert_not_called()
        manager._render_models.assert_called_once_with()

    def test_save_openai_compatible_backend_settings_refuses_invalid_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            token_dir.mkdir()
            app.token_pool_settings.save_backend_settings(
                app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key="pool-api-key",
            )

            with mock.patch.object(
                app.token_pool_settings,
                "resolve_openai_compatible_backend_config",
                side_effect=RuntimeError("Protocol detection failed."),
            ):
                with self.assertRaisesRegex(RuntimeError, "Protocol detection failed"):
                    app.save_openai_compatible_backend_settings(
                        settings_file=settings_file,
                        token_dir=token_dir,
                        proxy_port=8317,
                        proxy_api_key="pool-api-key",
                        base_url="https://api.openai.com/v1",
                        api_key="sk-test",
                        model="gpt-5.5",
                    )

            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual(app.token_pool_settings.BACKEND_MODE_CODEX_AUTH, reloaded["backend_mode"])

    def test_apply_backend_mode_settings_migrates_openai_protocol_for_other_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            token_dir.mkdir()

            updated = app.apply_backend_mode_settings(
                backend_mode=app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key="pool-api-key",
                openai_base_url="https://token-plan-sgp.xiaomimimo.com/v1",
                openai_api_key="tp-test",
                openai_model="mimo-v2-omni",
                openai_models=["mimo-v2-omni", "mimo-v2-pro"],
                openai_protocol="chat_completions",
            )
            reloaded = app.token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual(app.token_pool_settings.BACKEND_MODE_CODEX_AUTH, updated["backend_mode"])
        self.assertEqual("chat_completions", reloaded["openai_protocol"])
        self.assertEqual("tp-test", reloaded["openai_api_key"])

    def test_apply_backend_mode_settings_uses_openai_save_flow_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "token_pool_settings.json"
            token_dir = Path(temp_dir) / "tokens"
            token_dir.mkdir()

            with mock.patch.object(
                app,
                "save_openai_compatible_backend_settings",
                return_value={
                    "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                    "openai_base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
                    "openai_api_key": "tp-test",
                    "openai_model": "mimo-v2-omni",
                    "openai_models": ["mimo-v2-omni", "mimo-v2-pro"],
                    "openai_protocol": "chat_completions",
                },
            ) as save_openai:
                updated = app.apply_backend_mode_settings(
                    backend_mode=app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                    settings_file=settings_file,
                    token_dir=token_dir,
                    proxy_port=8317,
                    proxy_api_key="pool-api-key",
                    openai_base_url="https://token-plan-sgp.xiaomimimo.com/v1",
                    openai_api_key="tp-test",
                    openai_model="mimo-v2-omni",
                    openai_models=["mimo-v2-omni"],
                    openai_protocol="",
                )

        self.assertEqual(app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE, updated["backend_mode"])
        save_openai.assert_called_once_with(
            settings_file=settings_file,
            token_dir=token_dir,
            proxy_port=8317,
            proxy_api_key="pool-api-key",
            base_url="https://token-plan-sgp.xiaomimimo.com/v1",
            api_key="tp-test",
            model="mimo-v2-omni",
        )

    def test_load_available_models_uses_exact_openai_compatible_models_when_backend_enabled(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.backend_settings = {
            "backend_mode": "openai_compatible",
            "openai_models": ["mimo-v2.5-pro", "mimo-v2-pro"],
        }
        manager._reload_backend_settings = mock.Mock(return_value=manager.backend_settings)

        with mock.patch.object(app, "MODELS_CACHE_FILE", Path("missing-models-cache.json")):
            models = app.SessionManagerApp._load_available_models(manager)

        self.assertEqual(["mimo-v2.5-pro", "mimo-v2-pro"], models)

    def test_load_available_models_includes_visible_cache_models_for_codex_auth(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.backend_settings = {"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        manager._reload_backend_settings = mock.Mock(return_value=manager.backend_settings)

        with tempfile.TemporaryDirectory() as temp_dir:
            models_path = Path(temp_dir) / "models_cache.json"
            models_path.write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-5.4-mini", "visibility": "list"},
                            {"slug": "hidden-model", "visibility": "hidden"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(app, "MODELS_CACHE_FILE", models_path):
                models = app.SessionManagerApp._load_available_models(manager)

        self.assertIn("gpt-5.4-mini", models)
        self.assertNotIn("hidden-model", models)

    def test_build_codex_new_args_openai_compatible_uses_selected_endpoint_model(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager.use_global_defaults_var = mock.Mock()
        manager.use_global_defaults_var.get.return_value = False
        manager.model_var = mock.Mock()
        manager.model_var.get.return_value = "mimo-v2-pro"
        manager.approval_var = mock.Mock()
        manager.approval_var.get.return_value = "default"
        manager.sandbox_var = mock.Mock()
        manager.sandbox_var.get.return_value = "default"
        manager.search_var = mock.Mock()
        manager.search_var.get.return_value = False
        manager.available_models = ["mimo-v2.5-pro", "mimo-v2-pro"]
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "proxy_port": 8317,
                "openai_model": "mimo-v2.5-pro",
            }
        )

        args = app.SessionManagerApp._build_codex_new_args(manager)

        self.assertEqual("mimo-v2-pro", args[args.index("-m") + 1])

    def test_token_pool_status_summary_ignores_proxy_from_other_backend_mode_for_codex_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = object.__new__(app.SessionManagerApp)
            manager._token_pool_settings = mock.Mock(
                return_value={
                    "backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                    "proxy_port": 8317,
                    "token_dir": str(Path(temp_dir) / "tokens"),
                }
            )
            manager._token_pool_health = mock.Mock(
                return_value={
                    "status": "ok",
                    "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                    "port": 8317,
                }
            )

            summary = app.SessionManagerApp._token_pool_status_summary(manager)

        self.assertIn("Mode: codex_auth", summary)
        self.assertIn("Proxy: stopped", summary)

    def test_openai_compatible_proxy_health_requires_matching_config_fingerprint(self) -> None:
        settings = {
            "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "proxy_port": 8317,
            "proxy_api_key": "local-proxy-key",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": "sk-test",
            "openai_protocol": "responses",
            "openai_models": ["gpt-5.5"],
        }
        matching_health = {
            "status": "ok",
            "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "port": 8317,
            "config_fingerprint": app.token_pool_settings.openai_compatible_proxy_config_fingerprint(
                local_api_key="local-proxy-key",
                upstream_base_url="https://api.openai.com/v1",
                upstream_api_key="sk-test",
                upstream_protocol="responses",
                model_ids=["gpt-5.5"],
            ),
        }

        self.assertTrue(app.openai_compatible_proxy_health_matches_settings(matching_health, settings))
        self.assertFalse(
            app.openai_compatible_proxy_health_matches_settings(
                {**matching_health, "config_fingerprint": "stale"},
                settings,
            )
        )

    def test_restart_token_pool_proxy_codex_auth_only_stops_existing_proxy(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={"backend_mode": app.token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        )
        manager._stop_token_pool_proxy = mock.Mock()
        manager._start_token_pool_proxy = mock.Mock()

        app.SessionManagerApp._restart_token_pool_proxy(manager)

        manager._stop_token_pool_proxy.assert_called_once_with()
        manager._start_token_pool_proxy.assert_not_called()

    def test_run_taskkill_tree_silently_discards_taskkill_console_output(self) -> None:
        completed = subprocess.CompletedProcess(["taskkill"], 0)
        with mock.patch.object(app.subprocess, "run", return_value=completed) as run:
            result = app.run_taskkill_tree_silently(123)

        self.assertTrue(result)
        run.assert_called_once_with(
            ["taskkill", "/PID", "123", "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )

    def test_build_backend_override_args_uses_local_adapter_url_for_openai_mode(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "proxy_port": 8456,
                "proxy_api_key": "local-proxy-key",
                "openai_base_url": "https://token-plan-sgp.example.com/v1",
                "openai_api_key": "test-upstream-key",
                "openai_model": "mimo-v2-pro",
                "openai_protocol": "chat_completions",
            }
        )

        args = app.SessionManagerApp._build_backend_override_args(manager, "mimo-v2-pro")

        rendered = " ".join(args)
        self.assertIn('model_provider="openai_compatible"', rendered)
        self.assertIn('model_providers.openai_compatible.base_url="http://127.0.0.1:8456"', rendered)

    def test_build_backend_override_args_uses_local_adapter_when_proxy_preference_is_proxy(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "proxy_port": 8456,
                "proxy_api_key": "local-proxy-key",
                "openai_base_url": "https://token-plan-sgp.example.com/v1",
                "openai_api_key": "test-upstream-key",
                "openai_model": "gpt-5.5",
                "openai_protocol": "responses",
                "proxy_preference": "proxy",
            }
        )

        args = app.SessionManagerApp._build_backend_override_args(manager, "gpt-5.5")

        rendered = " ".join(args)
        self.assertIn('model_providers.openai_compatible.base_url="http://127.0.0.1:8456"', rendered)

    def test_token_pool_status_summary_includes_current_token_quota_when_available(self) -> None:
        manager = object.__new__(app.SessionManagerApp)
        manager._token_pool_settings = mock.Mock(
            return_value={
                "backend_mode": app.token_pool_settings.BACKEND_MODE_TOKEN_POOL,
                "token_dir": "C:\\tokens",
                "proxy_port": 8317,
            }
        )
        manager._token_pool_health = mock.Mock(
            return_value={
                "status": "ok",
                "port": 8317,
                "current_token_file": "only.json",
            }
        )
        with mock.patch.object(app.token_pool_settings, "list_token_files", return_value=[Path("C:\\tokens\\only.json")]), \
             mock.patch.object(
                 app,
                 "read_token_pool_token_quota",
                 return_value={
                     "state": "ok",
                     "summary": "5h quota: 7% used\nWeekly quota: 17% used",
                     "token_file": "only.json",
                     "email": "beth@example.com",
                 },
             ):
            summary = app.SessionManagerApp._token_pool_status_summary(manager)

        self.assertIn("Current token: only.json", summary)
        self.assertIn("Current token email: beth@example.com", summary)
        self.assertIn("Current token quota: 5h quota: 7% used", summary)

    def test_build_token_pool_proxy_command_uses_app_script_in_source_mode(self) -> None:
        with mock.patch.object(app.shutil, "which", return_value=None):
            command = app.build_token_pool_proxy_command(
                executable="C:\\Python311\\python.exe",
                app_path="D:\\codex\\manger\\app.py",
                port=8317,
                api_key="local-proxy-key",
                token_dir="C:\\Users\\codexuser\\.cli-proxy-api",
                frozen=False,
            )

        self.assertEqual("C:\\Python311\\python.exe", command[0])
        self.assertEqual("D:\\codex\\manger\\app.py", command[1])
        self.assertIn("--token-pool-proxy", command)
        self.assertIn("--port", command)

    def test_build_token_pool_proxy_command_prefers_conda_env_when_available(self) -> None:
        with mock.patch.object(app.shutil, "which", return_value="C:\\Miniconda3\\condabin\\conda.bat"):
            command = app.build_token_pool_proxy_command(
                executable="C:\\Python311\\python.exe",
                app_path="D:\\codex\\manger\\app.py",
                port=8317,
                api_key="local-proxy-key",
                token_dir="C:\\Users\\codexuser\\.cli-proxy-api",
                frozen=False,
            )

        self.assertEqual("C:\\Miniconda3\\condabin\\conda.bat", command[0])
        self.assertEqual(["run", "--no-capture-output", "-n", "codex-accel", "python", "D:\\codex\\manger\\app.py"], command[1:7])
        self.assertIn("--token-pool-proxy", command)

    def test_build_token_pool_proxy_command_uses_executable_only_when_frozen(self) -> None:
        command = app.build_token_pool_proxy_command(
            executable="D:\\codex\\manger\\codex-session-manager.exe",
            app_path="D:\\codex\\manger\\app.py",
            port=8317,
            api_key="local-proxy-key",
            token_dir="C:\\Users\\codexuser\\.cli-proxy-api",
            frozen=True,
        )

        self.assertEqual("D:\\codex\\manger\\codex-session-manager.exe", command[0])
        self.assertNotIn("D:\\codex\\manger\\app.py", command)

    def test_build_token_pool_proxy_command_uses_py_launcher_when_python_is_windowsapps_shim(self) -> None:
        executable = "C:\\Users\\codexuser\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\python.exe"

        def fake_which(name: str) -> str | None:
            mapping = {
                "conda": None,
                "py": "C:\\Windows\\py.exe",
                "python": executable,
            }
            return mapping.get(name)

        with mock.patch.object(app.shutil, "which", side_effect=fake_which):
            command = app.build_token_pool_proxy_command(
                executable=executable,
                app_path="D:\\codex\\manger\\app.py",
                port=8317,
                api_key="local-proxy-key",
                token_dir="C:\\Users\\codexuser\\.cli-proxy-api",
                frozen=False,
            )

        self.assertEqual(["C:\\Windows\\py.exe", "-3", "D:\\codex\\manger\\app.py"], command[:3])
        self.assertIn("--token-pool-proxy", command)

    def test_build_custom_provider_proxy_command_uses_py_launcher_when_python_is_windowsapps_shim(self) -> None:
        executable = "C:\\Program Files\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64__qbz5n2kfra8p0\\python3.13.exe"

        def fake_which(name: str) -> str | None:
            mapping = {
                "conda": None,
                "py": "C:\\Windows\\py.exe",
                "python": "C:\\Users\\codexuser\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe",
            }
            return mapping.get(name)

        with mock.patch.object(app.shutil, "which", side_effect=fake_which):
            command = app.build_custom_provider_proxy_command(
                executable=executable,
                app_path="D:\\codex\\manger\\app.py",
                port=8317,
                api_key="local-proxy-key",
                upstream_base_url="https://token-plan-sgp.example.com/v1",
                upstream_api_key="test-upstream-key",
                upstream_protocol="chat_completions",
                upstream_proxy_url="http://127.0.0.1:7898",
                model_ids=["mimo-v2-pro"],
                frozen=False,
            )

        self.assertEqual(["C:\\Windows\\py.exe", "-3", "D:\\codex\\manger\\app.py"], command[:3])
        self.assertIn("--custom-provider-proxy", command)
        self.assertIn("--upstream-protocol", command)
        protocol_index = command.index("--upstream-protocol") + 1
        self.assertEqual("chat_completions", command[protocol_index])
        self.assertNotIn("responses", command[protocol_index : protocol_index + 1])
        self.assertIn("--upstream-proxy-url", command)
        proxy_index = command.index("--upstream-proxy-url") + 1
        self.assertEqual("http://127.0.0.1:7898", command[proxy_index])

    def test_run_codex_browser_login_uses_default_login_command(self) -> None:
        completed = subprocess.CompletedProcess(["codex.cmd", "login"], 0, stdout="ok")

        with mock.patch.object(app.subprocess, "run", return_value=completed) as run:
            result = app.run_codex_browser_login()

        self.assertIs(result, completed)
        run.assert_called_once_with(
            ["codex.cmd", "login"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )

    def test_start_codex_browser_login_process_uses_default_login_command(self) -> None:
        fake_process = mock.Mock()

        with mock.patch.object(app.subprocess, "Popen", return_value=fake_process) as popen:
            result = app.start_codex_browser_login_process()

        self.assertIs(result, fake_process)
        popen.assert_called_once_with(
            ["codex.cmd", "login"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

    def test_start_codex_browser_login_process_can_request_private_browser(self) -> None:
        fake_process = mock.Mock()

        with mock.patch.object(app.subprocess, "Popen", return_value=fake_process) as popen:
            result = app.start_codex_browser_login_process(private_browser=True)

        self.assertIs(result, fake_process)
        args, kwargs = popen.call_args
        self.assertEqual(["codex.cmd", "login", "--device-auth"], args[0])
        env = kwargs["env"]
        self.assertEqual("1", env["CODEX_LOGIN_PRIVATE_BROWSER"])
        launcher = Path(env["BROWSER"])
        self.assertTrue(launcher.exists())
        launcher_text = launcher.read_text(encoding="utf-8")
        self.assertIn("--user-data-dir=", launcher_text)
        self.assertRegex(launcher_text.lower(), r"inprivate|incognito")
        self.assertTrue(Path(env["CODEX_LOGIN_PRIVATE_PROFILE_DIR"]).exists())

    def test_login_progress_window_is_modeless_so_notes_remain_copyable(self) -> None:
        self.assertFalse(app.LOGIN_PROGRESS_IS_MODAL)

    def test_find_note_references_detects_urls_and_emails(self) -> None:
        text = "acct a.user+1@example.com open https://mailbox.aiturn.top/ or http://x.test?a=1"

        refs = app.find_note_references(text)

        email = "a.user+1@example.com"
        first_url = "https://mailbox.aiturn.top/"
        second_url = "http://x.test?a=1"

        self.assertEqual(
            [
                {"kind": "email", "value": email, "start": text.index(email), "end": text.index(email) + len(email)},
                {"kind": "url", "value": first_url, "start": text.index(first_url), "end": text.index(first_url) + len(first_url)},
                {"kind": "url", "value": second_url, "start": text.index(second_url), "end": text.index(second_url) + len(second_url)},
            ],
            refs,
        )

    def test_login_and_bind_account_slot_saves_new_current_auth(self) -> None:
        completed = subprocess.CompletedProcess(["codex.cmd", "login"], 0, stdout="ok")

        with mock.patch.object(app.auth_slots, "load_slot_registry", return_value=[{"slot_id": "slot-9"}]), \
             mock.patch.object(app.auth_slots, "current_auth_info", side_effect=[{"fingerprint": "old"}, {"fingerprint": "new"}]), \
             mock.patch.object(app, "run_codex_browser_login", return_value=completed) as run_login, \
             mock.patch.object(app.auth_slots, "save_current_auth_to_slot", return_value={"slot_id": "slot-9", "email": "new@example.com"}) as save:
            result = app.login_and_bind_account_slot("slot-9")

        self.assertEqual("slot-9", result["slot_id"])
        run_login.assert_called_once_with()
        save.assert_called_once_with("slot-9")

    def test_login_and_bind_account_slot_rejects_unchanged_auth(self) -> None:
        completed = subprocess.CompletedProcess(["codex.cmd", "login"], 0, stdout="ok")

        with mock.patch.object(app.auth_slots, "load_slot_registry", return_value=[{"slot_id": "slot-9"}]), \
             mock.patch.object(app.auth_slots, "current_auth_info", side_effect=[{"fingerprint": "same"}, {"fingerprint": "same"}]), \
             mock.patch.object(app, "run_codex_browser_login", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "did not produce a new login"):
                app.login_and_bind_account_slot("slot-9")

    def test_main_dispatches_token_pool_proxy_mode(self) -> None:
        with mock.patch.object(app, "sys") as mocked_sys, mock.patch.object(app.token_pool_proxy, "main", return_value=7) as proxy_main:
            mocked_sys.argv = ["app.py", "--token-pool-proxy", "--port", "8317", "--api-key", "local", "--token-dir", "C:\\tokens"]

            result = app.main()

        self.assertEqual(7, result)
        proxy_main.assert_called_once_with(["--port", "8317", "--api-key", "local", "--token-dir", "C:\\tokens"])

    def test_main_dispatches_custom_provider_proxy_mode(self) -> None:
        with mock.patch.object(app, "sys") as mocked_sys, \
             mock.patch.object(app.custom_provider_proxy, "main", return_value=9) as proxy_main:
            mocked_sys.argv = [
                "app.py",
                "--custom-provider-proxy",
                "--port",
                "8456",
                "--api-key",
                "local-proxy-key",
                "--upstream-base-url",
                "https://token-plan-sgp.example.com/v1",
                "--upstream-api-key",
                "test-upstream-key",
                "--upstream-protocol",
                "responses",
                "--model",
                "mimo-v2-pro",
            ]

            result = app.main()

        self.assertEqual(9, result)
        proxy_main.assert_called_once_with(
            [
                "--port",
                "8456",
                "--api-key",
                "local-proxy-key",
                "--upstream-base-url",
                "https://token-plan-sgp.example.com/v1",
                "--upstream-api-key",
                "test-upstream-key",
                "--upstream-protocol",
                "responses",
                "--model",
                "mimo-v2-pro",
            ]
        )



if __name__ == "__main__":
    unittest.main()


