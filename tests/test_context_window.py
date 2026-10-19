import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app
import custom_provider_proxy
import mobile_portal
import token_pool_proxy
import token_pool_settings
import window_runtime


class FakeVar:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value


def make_manager() -> app.SessionManagerApp:
    manager = object.__new__(app.SessionManagerApp)
    manager.use_global_defaults_var = FakeVar(False)
    manager.model_var = FakeVar("gpt-5.6-sol")
    manager.approval_var = FakeVar("never")
    manager.sandbox_var = FakeVar("danger-full-access")
    manager.reasoning_effort_var = FakeVar("high")
    manager.search_var = FakeVar(False)
    return manager


class ContextWindowTests(unittest.TestCase):
    def test_gpt6_model_is_the_shared_default(self) -> None:
        self.assertEqual("gpt-6.1-sol", app.DEFAULT_PRIMARY_MODEL)
        self.assertEqual("gpt-6.1-sol", app.DEFAULT_LAUNCH_MODEL)
        self.assertEqual("gpt-6.1-sol", mobile_portal.DEFAULT_PRIMARY_MODEL)

    def test_gpt61_sol_is_in_every_default_model_catalog(self) -> None:
        self.assertIn("gpt-6.1-sol", app.FALLBACK_MODEL_OPTIONS)
        self.assertIn("gpt-6.1-sol", mobile_portal.FALLBACK_MODEL_OPTIONS)
        self.assertIn("gpt-6.1-sol", custom_provider_proxy.DEFAULT_MODEL_IDS)
        self.assertIn("gpt-6.1-sol", token_pool_proxy.DEFAULT_MODEL_IDS)
        self.assertIn("gpt-6.1-sol", app.merge_available_models([]))
        self.assertIn("gpt-6.1-sol", mobile_portal.default_model_options([]))

    def test_gpt6_sol_and_luna_are_available_in_desktop_and_mobile_choices(self) -> None:
        for model_id in ("gpt-6-sol", "gpt-6-luna"):
            self.assertIn(model_id, app.FALLBACK_MODEL_OPTIONS)
            self.assertIn(model_id, mobile_portal.FALLBACK_MODEL_OPTIONS)
            self.assertIn(model_id, app.merge_available_models([]))
            self.assertIn(model_id, mobile_portal.default_model_options([]))

    def test_codex_auth_catalog_adds_gpt6_sol_and_luna_from_updated_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            catalog_file = Path(temp_dir) / "codex-auth-model-catalog.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-6-astra", "display_name": "GPT-6-Astra", "visibility": "list"},
                            {"slug": "gpt-5.6-sol", "display_name": "GPT-5.6-Sol", "visibility": "list"},
                            {"slug": "gpt-5.6-luna", "display_name": "GPT-5.6-Luna", "visibility": "list"},
                            {"slug": "gpt-reserve", "display_name": "GPT-Reserve", "visibility": "hide"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = token_pool_settings.ensure_codex_auth_model_catalog(
                models_cache_file=cache_file,
                catalog_file=catalog_file,
            )

            self.assertEqual(catalog_file, result)
            payload = json.loads(catalog_file.read_text(encoding="utf-8"))
            by_slug = {item["slug"]: item for item in payload["models"]}
            for model_id in ("gpt-6-sol", "gpt-6-luna"):
                self.assertIn(model_id, by_slug)
                self.assertEqual("list", by_slug[model_id]["visibility"])
                self.assertEqual(512_000, by_slug[model_id]["context_window"])
                self.assertIn(
                    "none",
                    {item["effort"] for item in by_slug[model_id]["supported_reasoning_levels"]},
                )

    def test_proxy_default_model_catalog_includes_gpt6_family(self) -> None:
        for model_id in ("gpt-6.1-sol", "gpt-6-astra", "gpt-6-sol", "gpt-6-luna"):
            self.assertIn(model_id, custom_provider_proxy.DEFAULT_MODEL_IDS)
            self.assertIn(model_id, token_pool_proxy.DEFAULT_MODEL_IDS)

    def test_codex_auth_catalog_adds_gpt61_sol_with_supported_reasoning_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            catalog_file = Path(temp_dir) / "codex-auth-model-catalog.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-5.6-sol", "display_name": "GPT-5.6-Sol", "visibility": "list"},
                            {"slug": "gpt-reserve", "display_name": "GPT-Reserve", "visibility": "hide"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            token_pool_settings.ensure_codex_auth_model_catalog(
                models_cache_file=cache_file,
                catalog_file=catalog_file,
            )
            models = json.loads(catalog_file.read_text(encoding="utf-8"))["models"]
            model = next(item for item in models if item["slug"] == "gpt-6.1-sol")
            self.assertEqual("GPT-6.1-Sol", model["display_name"])
            self.assertEqual(512_000, model["context_window"])
            self.assertEqual(
                ["low", "medium", "high", "xhigh", "max"],
                [item["effort"] for item in model["supported_reasoning_levels"]],
            )

    def test_gpt_reserve_is_only_in_codex_auth_model_catalog(self) -> None:
        self.assertIn("gpt-reserve", app.merge_available_models([], include_codex_reserve=True))
        self.assertNotIn("gpt-reserve", app.merge_available_models([]))
        self.assertIn("gpt-reserve", mobile_portal.merge_available_models([], include_codex_reserve=True))
        self.assertNotIn("gpt-reserve", mobile_portal.merge_available_models([]))

    def test_desktop_codex_auth_launch_passes_gpt_reserve_to_cli(self) -> None:
        manager = make_manager()
        manager.model_var = FakeVar("gpt-reserve")
        settings = {"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        with mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"):
            args = manager._build_codex_new_args(settings)
        self.assertIn(["-m", "gpt-reserve"], [args[index:index + 2] for index in range(len(args) - 1)])

    def test_mobile_codex_auth_launch_passes_gpt_reserve_to_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "backend.json"
            token_pool_settings.save_backend_settings(
                backend_mode=token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
            )
            args = mobile_portal.build_new_chat_args(
                Path(temp_dir) / "output.json",
                "hello",
                "gpt-reserve",
                "default",
                "default",
                "default",
                settings_file,
            )
        self.assertIn(["-m", "gpt-reserve"], [args[index:index + 2] for index in range(len(args) - 1)])

    def test_auth_resume_does_not_reuse_active_openai_preset_model(self) -> None:
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH,
            "active_openai_preset_id": "anyrouter",
            "openai_model": "gpt-6-astra",
            "openai_presets": [
                {
                    "id": "anyrouter",
                    "openai_model": "gpt-6-astra",
                    "openai_models": ["gpt-6-astra", "claude-fable-5-1"],
                }
            ],
        }
        with mock.patch.object(
            token_pool_settings,
            "configured_codex_auth_model",
            return_value="gpt-5.6-luna",
        ):
            resolved = mobile_portal.resolve_launch_model_for_backend(
                "gpt-6-astra",
                settings,
            )
        self.assertEqual("gpt-5.6-luna", resolved)

    def test_desktop_auth_global_default_uses_configured_account_model(self) -> None:
        manager = make_manager()
        manager.use_global_defaults_var = FakeVar(True)
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH,
        }
        with (
            mock.patch.object(
                token_pool_settings,
                "configured_codex_auth_model",
                return_value="gpt-5.6-luna",
            ),
            mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"),
        ):
            args = manager._build_codex_new_args(settings)
        self.assertIn(["-m", "gpt-5.6-luna"], [args[index:index + 2] for index in range(len(args) - 1)])

    def test_desktop_and_mobile_resume_pass_gpt_reserve_to_cli(self) -> None:
        manager = make_manager()
        manager.model_var = FakeVar("gpt-reserve")
        item = app.SessionItem(
            session_id="reserve-session",
            ts=0,
            text="",
            note="",
            history_count=1,
            cwd="D:\\workspace",
            model="gpt-reserve",
            approval_policy="never",
            sandbox_mode="danger-full-access",
            turn_id="",
            session_file="",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "backend.json"
            token_pool_settings.save_backend_settings(
                backend_mode=token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                settings_file=settings_file,
            )
            with mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"):
                desktop_args = manager._build_codex_resume_args(
                    item,
                    {"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH},
                )
            mobile_args = mobile_portal.build_resume_args(
                Path(temp_dir) / "output.json",
                "reserve-session",
                "continue",
                "gpt-reserve",
                "default",
                "default",
                "default",
                backend_settings_file=settings_file,
            )
        self.assertIn(["-m", "gpt-reserve"], [desktop_args[index:index + 2] for index in range(len(desktop_args) - 1)])
        self.assertIn(["-m", "gpt-reserve"], [mobile_args[index:index + 2] for index in range(len(mobile_args) - 1)])

    def test_context_override_is_512k_tokens_with_460k_compaction(self) -> None:
        self.assertEqual(
            [
                "-c",
                "model_context_window=512000",
                "-c",
                "model_auto_compact_token_limit=460000",
            ],
            token_pool_settings.build_codex_context_override_args(),
        )

    def test_desktop_new_and_resume_args_include_context_override_for_every_backend(self) -> None:
        manager = make_manager()
        item = app.SessionItem(
            session_id="session-test",
            ts=0,
            text="",
            note="",
            history_count=1,
            cwd="D:\\workspace",
            model="gpt-5.6-sol",
            approval_policy="never",
            sandbox_mode="danger-full-access",
            turn_id="",
            session_file="",
        )
        settings_by_mode = {
            token_pool_settings.BACKEND_MODE_CODEX_AUTH: {
                "backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH,
            },
            token_pool_settings.BACKEND_MODE_TOKEN_POOL: {
                "backend_mode": token_pool_settings.BACKEND_MODE_TOKEN_POOL,
                "proxy_port": 8317,
            },
            token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE: {
                "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "openai_base_url": "https://provider.example/v1",
                "openai_api_key": "key",
                "openai_model": "gpt-5.6-sol",
                "openai_models": ["gpt-5.6-sol"],
                "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
                "proxy_preference": "direct",
            },
        }

        for settings in settings_by_mode.values():
            if settings["backend_mode"] == token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE:
                with (
                    mock.patch.object(manager, "_ensure_openai_compatible_launch_model_metadata"),
                    mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"),
                ):
                    new_args = manager._build_codex_new_args(settings)
                    resume_args = manager._build_codex_resume_args(item, settings)
            else:
                with mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"):
                    new_args = manager._build_codex_new_args(settings)
                    resume_args = manager._build_codex_resume_args(item, settings)
            self.assertIn("model_context_window=512000", new_args)
            self.assertIn("model_auto_compact_token_limit=460000", new_args)
            self.assertIn("model_context_window=512000", resume_args)
            self.assertIn("model_auto_compact_token_limit=460000", resume_args)

    def test_mobile_new_and_resume_args_include_context_override_for_every_backend(self) -> None:
        settings_by_mode = [
            {"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH},
            {
                "backend_mode": token_pool_settings.BACKEND_MODE_TOKEN_POOL,
                "proxy_port": 8317,
            },
            {
                "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                "openai_base_url": "https://provider.example/v1",
                "openai_api_key": "key",
                "openai_model": "gpt-5.6-sol",
                "openai_models": ["gpt-5.6-sol"],
                "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
                "proxy_preference": "direct",
            },
        ]

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(token_pool_settings, "load_backend_settings") as load_settings,
            mock.patch.object(mobile_portal, "ensure_openai_compatible_launch_model_metadata"),
            mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"),
        ):
            output_file = Path(temp_dir) / "output.json"
            for settings in settings_by_mode:
                load_settings.return_value = settings
                new_args = mobile_portal.build_new_chat_args(
                    output_file,
                    "hello",
                    "gpt-5.6-sol",
                    "default",
                    "default",
                    "default",
                )
                resume_args = mobile_portal.build_resume_args(
                    output_file,
                    "session-test",
                    "hello",
                    "gpt-5.6-sol",
                    "default",
                    "default",
                    "default",
                )
                self.assertIn("model_context_window=512000", new_args)
                self.assertIn("model_auto_compact_token_limit=460000", new_args)
                self.assertIn("model_context_window=512000", resume_args)
                self.assertIn("model_auto_compact_token_limit=460000", resume_args)

    def test_custom_provider_advertises_512k_token_context(self) -> None:
        model = custom_provider_proxy.build_models_payload(["custom-model"])["models"][0]
        self.assertEqual(512_000, model["context_window"])
        self.assertEqual(512_000, model["max_context_window"])

    def test_token_pool_advertises_codex_context_metadata(self) -> None:
        payload = token_pool_proxy.build_models_payload(("gpt-5.6-sol",))
        self.assertIn("models", payload)
        model = payload["models"][0]
        self.assertEqual("gpt-5.6-sol", model["slug"])
        self.assertEqual(512_000, model["context_window"])
        self.assertEqual(512_000, model["max_context_window"])

    def test_context_metadata_normalizes_every_cached_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "gpt-5.6-sol",
                                "context_window": 272000,
                                "max_context_window": 872000,
                            },
                            {
                                "slug": "gpt-reserve",
                                "context_window": 128000,
                                "max_context_window": 128000,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                token_pool_settings.ensure_codex_model_context_metadata(
                    ["gpt-5.6-sol"],
                    models_cache_file=cache_file,
                )
            )
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            for model in payload["models"]:
                self.assertEqual(512_000, model["context_window"])
                self.assertEqual(512_000, model["max_context_window"])

    def test_codex_auth_reserve_model_is_visible_to_interactive_model_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-6-astra", "visibility": "list"},
                            {"slug": "gpt-reserve", "visibility": "hide"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                token_pool_settings.ensure_codex_auth_reserve_model_visible(
                    models_cache_file=cache_file,
                )
            )
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            reserve = next(model for model in payload["models"] if model["slug"] == "gpt-reserve")
            self.assertEqual("list", reserve["visibility"])

            self.assertFalse(
                token_pool_settings.ensure_codex_auth_reserve_model_visible(
                    models_cache_file=cache_file,
                )
            )

    def test_codex_auth_static_catalog_keeps_reserve_visible_after_cache_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            catalog_file = Path(temp_dir) / "codex-auth-model-catalog.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "gpt-6-astra", "visibility": "list"},
                            {"slug": "gpt-reserve", "visibility": "hide"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = token_pool_settings.ensure_codex_auth_model_catalog(
                models_cache_file=cache_file,
                catalog_file=catalog_file,
            )

            self.assertEqual(catalog_file, result)
            payload = json.loads(catalog_file.read_text(encoding="utf-8"))
            self.assertEqual(2, len(payload["models"]))
            reserve = next(model for model in payload["models"] if model["slug"] == "gpt-reserve")
            self.assertEqual("list", reserve["visibility"])

    def test_reserve_visibility_helper_does_not_add_model_to_generic_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            original = {"models": [{"slug": "gpt-6-astra", "visibility": "list"}]}
            cache_file.write_text(json.dumps(original), encoding="utf-8")

            self.assertFalse(
                token_pool_settings.ensure_codex_auth_reserve_model_visible(
                    models_cache_file=cache_file,
                )
            )
            self.assertEqual(original, json.loads(cache_file.read_text(encoding="utf-8")))

    def test_auth_launches_pass_static_model_catalog_to_cli(self) -> None:
        manager = make_manager()
        manager.model_var = FakeVar("gpt-reserve")
        settings = {"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH}
        catalog_file = Path("C:/Users/windows/.codex/codex_auth_model_catalog.json")

        with (
            mock.patch.object(token_pool_settings, "ensure_codex_auth_model_catalog", return_value=catalog_file),
            mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata"),
        ):
            desktop_args = manager._build_codex_new_args(settings)

            with tempfile.TemporaryDirectory() as temp_dir:
                settings_file = Path(temp_dir) / "backend.json"
                token_pool_settings.save_backend_settings(
                    backend_mode=token_pool_settings.BACKEND_MODE_CODEX_AUTH,
                    settings_file=settings_file,
                )
                mobile_args = mobile_portal.build_new_chat_args(
                    Path(temp_dir) / "output.json",
                    "hello",
                    "gpt-reserve",
                    "default",
                    "default",
                    "default",
                    settings_file,
                )

        expected = ['-c', 'model_catalog_json="C:/Users/windows/.codex/codex_auth_model_catalog.json"']
        self.assertIn(expected, [desktop_args[index:index + 2] for index in range(len(desktop_args) - 1)])
        self.assertIn(expected, [mobile_args[index:index + 2] for index in range(len(mobile_args) - 1)])

    def test_mobile_codex_auth_loader_exposes_reserve_in_shared_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "backend.json"
            cache_file = Path(temp_dir) / "models_cache.json"
            settings_file.write_text(
                json.dumps({"backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH}),
                encoding="utf-8",
            )
            cache_file.write_text(
                json.dumps({"models": [{"slug": "gpt-reserve", "visibility": "hide"}]}),
                encoding="utf-8",
            )

            with (
                mock.patch.object(mobile_portal, "BACKEND_SETTINGS_FILE", settings_file),
                mock.patch.object(mobile_portal, "MODELS_CACHE_FILE", cache_file),
            ):
                models = mobile_portal.CodexDataStore().load_available_models()

            self.assertIn("gpt-reserve", models)
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            reserve = next(model for model in payload["models"] if model["slug"] == "gpt-reserve")
            self.assertEqual("list", reserve["visibility"])

    def test_openai_compatible_cache_metadata_is_upgraded_to_512k(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "gpt-5.5",
                                "context_window": 272000,
                                "max_context_window": 272000,
                                "input_modalities": ["text"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                token_pool_settings.ensure_openai_compatible_model_metadata(
                    ["custom-model"],
                    models_cache_file=cache_file,
                )
            )
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            custom = next(model for model in payload["models"] if model["slug"] == "custom-model")
            self.assertEqual(512_000, custom["context_window"])
            self.assertEqual(512_000, custom["max_context_window"])

    def test_existing_model_cache_metadata_is_upgraded_for_any_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "gpt-5.6-sol",
                                "context_window": 272000,
                                "max_context_window": 872000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                token_pool_settings.ensure_codex_model_context_metadata(
                    ["gpt-5.6-sol"],
                    models_cache_file=cache_file,
                )
            )
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            model = payload["models"][0]
            self.assertEqual(512_000, model["context_window"])
            self.assertEqual(512_000, model["max_context_window"])

    def test_unchanged_model_cache_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            original = {
                "client_version": "0.148.0",
                "etag": None,
                "fetched_at": "2026-09-05T00:00:00Z",
                "models": [
                    {
                        "slug": "gpt-6-astra",
                        "context_window": 512_000,
                        "max_context_window": 512_000,
                    }
                ],
            }
            cache_file.write_text(
                json.dumps(original, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            before = cache_file.read_bytes()

            with mock.patch.object(
                token_pool_settings,
                "_current_codex_client_version",
                return_value="0.148.0",
            ):
                self.assertFalse(
                    token_pool_settings.ensure_codex_model_context_metadata(
                        ["gpt-6-astra"],
                        models_cache_file=cache_file,
                    )
                )

            self.assertEqual(before, cache_file.read_bytes())

    def test_model_cache_is_written_in_codex_cache_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "models_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "client_version": "0.148.0",
                        "models": [
                            {
                                "slug": "gpt-5.6-sol",
                                "context_window": 272000,
                                "max_context_window": 872000,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                token_pool_settings.ensure_codex_model_context_metadata(
                    ["gpt-5.6-sol"],
                    models_cache_file=cache_file,
                )
            )
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            self.assertRegex(payload["fetched_at"], r"^20\d\d-")
            self.assertIsNone(payload["etag"])

    def test_models_only_resolver_prefers_shared_gpt6_default_when_available(self) -> None:
        with (
            mock.patch.object(
                token_pool_settings,
                "normalize_openai_base_url",
                return_value="https://provider.example/v1",
            ),
            mock.patch.object(
                token_pool_settings,
                "fetch_openai_compatible_models",
                return_value=["claude-sonnet", "gpt-6-astra"],
            ),
        ):
            resolved = token_pool_settings.resolve_openai_compatible_models_only_config(
                "https://provider.example/v1",
                "api-key",
                "missing-model",
            )

        self.assertEqual("gpt-6-astra", resolved["openai_model"])

    def test_unsupported_api_preset_does_not_accept_global_gpt6_default(self) -> None:
        manager = make_manager()
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "openai_model": "gpt-5.5",
            "openai_models": ["gpt-5.5"],
        }

        self.assertEqual(
            "gpt-5.5",
            manager._resolve_openai_compatible_launch_model(
                app.DEFAULT_PRIMARY_MODEL,
                settings=settings,
            ),
        )
        self.assertEqual(
            "gpt-5.5",
            mobile_portal.resolve_launch_model_for_backend(
                app.DEFAULT_PRIMARY_MODEL,
                settings,
            ),
        )

    def test_desktop_runtime_refreshes_active_account_model_cache(self) -> None:
        manager = make_manager()
        manager.model_var = FakeVar("default")
        runtime = window_runtime.WindowRuntime(
            launch_id="launch-test",
            runtime_root=Path("D:/codex-runtime"),
            runtime_dir=Path("D:/codex-runtime/launch-test"),
            codex_home=Path("C:/Users/windows/.codex/account_slots/slot-2"),
            sqlite_home=Path("C:/Users/windows/.codex"),
            isolated=True,
            session_id="",
        )
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_CODEX_AUTH,
        }

        with (
            mock.patch.object(app.auth_slots, "detect_active_slot", return_value="slot-2"),
            mock.patch.object(app.window_runtime, "prepare_account_runtime", return_value=runtime),
            mock.patch.object(token_pool_settings, "ensure_codex_model_context_metadata") as ensure,
            mock.patch.object(token_pool_settings, "ensure_codex_auth_reserve_model_visible") as expose_reserve,
            mock.patch.object(
                token_pool_settings,
                "configured_codex_auth_model",
                return_value="gpt-5.6-luna",
            ),
        ):
            manager._prepare_window_runtime(settings, session_id="")

        expose_reserve.assert_called_once_with(
            models_cache_file=runtime.codex_home / "models_cache.json",
        )
        ensure.assert_called_once_with(
            ["gpt-5.6-luna"],
            models_cache_file=runtime.codex_home / "models_cache.json",
        )


if __name__ == "__main__":
    unittest.main()
