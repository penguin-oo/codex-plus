import unittest
from pathlib import Path
from unittest import mock

import app
import mobile_portal
import token_pool_settings


class ProxyRoutingTests(unittest.TestCase):
    def test_responses_network_proxy_does_not_require_local_adapter(self) -> None:
        settings = {
            "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            "proxy_preference": "proxy",
        }

        self.assertFalse(app._is_proxy_needed_for_openai_compatible(settings))
        self.assertFalse(mobile_portal.openai_compatible_requires_local_proxy(settings))

    def test_chat_completions_requires_local_adapter(self) -> None:
        settings = {
            "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS,
            "proxy_preference": "direct",
        }

        self.assertTrue(app._is_proxy_needed_for_openai_compatible(settings))
        self.assertTrue(mobile_portal.openai_compatible_requires_local_proxy(settings))

    def test_responses_proxy_preference_keeps_upstream_base_url(self) -> None:
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            "openai_base_url": "https://provider.example/v1",
            "proxy_preference": "proxy",
            "proxy_port": 8317,
        }

        with mock.patch.object(
            token_pool_settings,
            "load_backend_settings",
            return_value=settings,
        ):
            args = mobile_portal.build_backend_override_args(Path("unused.json"))

        self.assertIn(
            'model_providers.openai_compatible.base_url="https://provider.example/v1"',
            args,
        )
        self.assertNotIn(
            'model_providers.openai_compatible.base_url="http://127.0.0.1:8317"',
            args,
        )

    def test_responses_proxy_preference_still_enables_network_proxy_env(self) -> None:
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            "openai_api_key": "test-key",
            "proxy_preference": "proxy",
        }
        proxy_settings = {
            "proxy_enabled": True,
            "proxy_scheme": "socks5h",
            "proxy_host": "127.0.0.1",
            "proxy_port": 7897,
        }

        with (
            mock.patch.object(token_pool_settings, "load_backend_settings", return_value=settings),
            mock.patch.object(mobile_portal, "load_proxy_settings", return_value=proxy_settings),
        ):
            env = mobile_portal.build_codex_subprocess_env(
                base_env={},
                settings_file=Path("proxy.json"),
                backend_settings_file=Path("backend.json"),
            )

        self.assertEqual("socks5h://127.0.0.1:7897", env["HTTPS_PROXY"])
        self.assertEqual("test-key", env[mobile_portal.OPENAI_COMPAT_ENV_KEY_NAME])

    def test_network_proxy_falls_back_to_active_preset_when_top_level_is_detached(self) -> None:
        settings = {
            "backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
            "openai_protocol": token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            "openai_api_key": "test-key",
            "active_openai_preset_id": "preset-1",
            "openai_config_detached_from_preset": True,
            "openai_presets": [
                {
                    "id": "preset-1",
                    "proxy_preference": "proxy",
                }
            ],
        }
        proxy_settings = {
            "proxy_enabled": True,
            "proxy_scheme": "socks5h",
            "proxy_host": "127.0.0.1",
            "proxy_port": 7897,
        }

        with (
            mock.patch.object(token_pool_settings, "load_backend_settings", return_value=settings),
            mock.patch.object(mobile_portal, "load_proxy_settings", return_value=proxy_settings),
        ):
            env = mobile_portal.build_codex_subprocess_env(
                base_env={},
                settings_file=Path("proxy.json"),
                backend_settings_file=Path("backend.json"),
            )

        self.assertEqual("socks5h://127.0.0.1:7897", env["HTTPS_PROXY"])

    def test_apply_mode_passes_selected_protocol_to_openai_backend_save(self) -> None:
        with (
            mock.patch.object(token_pool_settings, "load_backend_settings", return_value={}),
            mock.patch.object(
                app,
                "save_openai_compatible_backend_settings",
                return_value={"backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE},
            ) as save_backend,
        ):
            app.apply_backend_mode_settings(
                backend_mode=token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=Path("unused.json"),
                token_dir=Path("tokens"),
                proxy_port=8317,
                proxy_api_key="proxy-key",
                openai_base_url="https://provider.example/v1",
                openai_api_key="api-key",
                openai_model="gpt-test",
                openai_protocol=token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS,
            )

        self.assertEqual(
            token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS,
            save_backend.call_args.kwargs["protocol_override"],
        )

    def test_apply_mode_keeps_active_skip_validation_preset_path(self) -> None:
        existing = {
            "active_openai_preset_id": "skip-provider",
            "openai_config_detached_from_preset": True,
            "openai_presets": [
                {
                    "id": "skip-provider",
                    "name": "Skip Provider",
                    "skip_validation": True,
                    "proxy_preference": "direct",
                }
            ],
        }

        with (
            mock.patch.object(token_pool_settings, "load_backend_settings", return_value=existing),
            mock.patch.object(
                app,
                "save_openai_compatible_backend_settings",
                return_value={"backend_mode": token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE},
            ) as save_backend,
        ):
            app.apply_backend_mode_settings(
                backend_mode=token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=Path("unused.json"),
                token_dir=Path("tokens"),
                proxy_port=8317,
                proxy_api_key="proxy-key",
                openai_base_url="https://provider.example/v1",
                openai_api_key="api-key",
                openai_model="gpt-test",
                openai_protocol=token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS,
            )

        self.assertEqual("skip-provider", save_backend.call_args.kwargs["preset_id"])
        self.assertEqual("Skip Provider", save_backend.call_args.kwargs["preset_name"])


if __name__ == "__main__":
    unittest.main()
