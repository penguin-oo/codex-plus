import json
import unittest
import tempfile
from pathlib import Path
from unittest import mock

import token_pool_settings


class OpenAICompatibleConfigTests(unittest.TestCase):
    def test_direct_get_forces_empty_proxy_handler(self) -> None:
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=None)
        response.status = 200
        response.read.return_value = b'{}'
        opener = mock.Mock()
        opener.open.return_value = response

        with mock.patch.object(token_pool_settings.url_request, 'ProxyHandler', side_effect=lambda proxies: ('proxy', proxies)), \
             mock.patch.object(token_pool_settings.url_request, 'build_opener', return_value=opener) as build_opener:
            status, body = token_pool_settings._direct_get(
                'https://example.invalid/models',
                {'Accept': 'application/json'},
                1.0,
            )

        self.assertEqual(200, status)
        self.assertEqual('{}', body)
        build_opener.assert_called_once_with(('proxy', {}))

    def test_detect_openai_compatible_protocol_prefers_responses_when_available(self) -> None:
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                return 200, '{"id":"resp_test","output":[{"type":"message"}]}'
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://token-plan-sgp.xiaomimimo.com/v1',
                'sk-test',
                'mimo-v2.5-pro',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_RESPONSES, protocol)
        self.assertEqual('https://token-plan-sgp.xiaomimimo.com/v1', resolved)
        self.assertEqual(
            ['https://token-plan-sgp.xiaomimimo.com/v1/responses'],
            calls,
        )

    def test_detect_openai_compatible_protocol_falls_back_to_chat_completions(self) -> None:
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                return 404, '{"error":"not found"}'
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://token-plan-sgp.xiaomimimo.com/v1',
                'sk-test',
                'mimo-v2.5-pro',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS, protocol)
        self.assertEqual('https://token-plan-sgp.xiaomimimo.com/v1', resolved)
        self.assertEqual(
            [
                'https://token-plan-sgp.xiaomimimo.com/v1/responses',
                'https://token-plan-sgp.xiaomimimo.com/v1/chat/completions',
            ],
            calls,
        )

    def test_detect_openai_compatible_protocol_falls_back_when_responses_disconnects(self) -> None:
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                raise RuntimeError('Failed to connect to the configured endpoint.')
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://gptcode.top/v1',
                'sk-test',
                'gpt-5.4',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS, protocol)
        self.assertEqual('https://gptcode.top/v1', resolved)
        self.assertEqual(
            [
                'https://gptcode.top/v1/responses',
                'https://gptcode.top/v1/chat/completions',
            ],
            calls,
        )

    def test_detect_openai_compatible_protocol_falls_back_when_responses_output_is_empty(self) -> None:
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                return 200, '{"id":"resp_test","output":[]}'
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://example.invalid/v1',
                'sk-test',
                'gpt-5.4',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS, protocol)
        self.assertEqual(
            [
                'https://example.invalid/v1/responses',
                'https://example.invalid/v1/responses',
                'https://example.invalid/v1/chat/completions',
            ],
            calls,
        )

    def test_detect_openai_compatible_protocol_accepts_streaming_responses_after_empty_non_stream(self) -> None:
        calls: list[tuple[str, bool]] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            payload_dict = json.loads(payload)
            stream = bool(payload_dict.get('stream'))
            calls.append((url, stream))
            if url.endswith('/responses') and not stream:
                return 200, '{"id":"resp_test","output":[],"status":"completed"}'
            if url.endswith('/responses') and stream:
                return 200, (
                    'event: response.output_text.delta\n'
                    'data: {"type":"response.output_text.delta","delta":"pong"}\n\n'
                    'event: response.completed\n'
                    'data: {"type":"response.completed","response":{"status":"completed"}}\n\n'
                )
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://provider-c.example.test/v1',
                'sk-test',
                'gpt-5.5',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_RESPONSES, protocol)
        self.assertEqual('https://provider-c.example.test/v1', resolved)
        self.assertEqual(
            [
                ('https://provider-c.example.test/v1/responses', False),
                ('https://provider-c.example.test/v1/responses', True),
            ],
            calls,
        )

    def test_detect_openai_compatible_protocol_falls_back_on_stream_required_error(self) -> None:
        """Proxies that reject non-stream /responses with HTTP 400 should
        still be detected as supporting the Responses API when a stream
        probe succeeds, or fall back to /chat/completions otherwise."""
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                payload_dict = json.loads(payload)
                if payload_dict.get('stream'):
                    return 200, 'data: {"id":"resp_test","output":[{"type":"message"}]}\n\ndata: [DONE]\n\n'
                return 400, '{"error":{"message":"must be stream request","type":"new_api_error","code":"invalid_responses_request"}}'
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://provider-d.example.test/v1',
                'sk-test',
                'gpt-5.5',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_RESPONSES, protocol)
        self.assertEqual('https://provider-d.example.test/v1', resolved)

    def test_detect_openai_compatible_protocol_returns_responses_when_stream_probe_fails_but_proxy_confirmed(self) -> None:
        """When the proxy returns HTTP 400 'must be stream request' for the
        non-stream probe, it has confirmed it speaks the Responses API.
        Even if the stream probe also fails, we should return 'responses'
        rather than falling back to /chat/completions."""
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                return 400, '{"error":{"message":"must be stream request","type":"new_api_error"}}'
            if url.endswith('/chat/completions'):
                return 200, '{"id":"chatcmpl_test","choices":[{"message":{"content":"pong"}}]}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://provider-d.example.test/v1',
                'sk-test',
                'gpt-5.5',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_RESPONSES, protocol)
        self.assertEqual('https://provider-d.example.test/v1', resolved)

    def test_detect_openai_compatible_protocol_accepts_codex_restricted_responses(self) -> None:
        calls: list[str] = []

        def fake_post(url: str, headers: dict[str, str], payload: bytes, timeout: float) -> tuple[int, str]:
            calls.append(url)
            if url.endswith('/responses'):
                return 403, '{"error":{"message":"请使用最新版的codex客户端或codex cli调用","code":"codex_access_restricted"}}'
            if url.endswith('/chat/completions'):
                return 404, '{"error":"not found"}'
            return 404, '{}'

        with mock.patch.object(
            token_pool_settings,
            '_http_post_json',
            side_effect=fake_post,
        ), mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ):
            protocol, resolved = token_pool_settings.detect_openai_compatible_protocol(
                'https://provider-b.example.test/codex',
                'sk-test',
                'gpt-5.5',
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_RESPONSES, protocol)
        self.assertEqual('https://provider-b.example.test/codex', resolved)
        self.assertEqual(['https://provider-b.example.test/codex/responses'], calls)

    def test_save_backend_settings_preserves_chat_completions_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = token_pool_settings.save_backend_settings(
                token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=Path(temp_dir) / 'token_pool_settings.json',
                token_dir=Path(temp_dir) / 'tokens',
                proxy_port=8317,
                proxy_api_key='pool-api-key',
                openai_base_url='https://api.openai.com/v1',
                openai_api_key='sk-test',
                openai_model='gpt-5.5',
                openai_models=['gpt-5.5'],
                openai_protocol=token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS,
            )

        self.assertEqual(token_pool_settings.OPENAI_PROTOCOL_CHAT_COMPLETIONS, payload['openai_protocol'])

    def test_load_backend_settings_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            settings_file.write_text(
                '\ufeff{'
                '"backend_mode":"openai_compatible",'
                '"token_dir":"C:/tokens",'
                '"proxy_port":8317,'
                '"proxy_api_key":"local-proxy-key",'
                '"openai_base_url":"https://s2a.example/v1",'
                '"openai_api_key":"sk-test",'
                '"openai_model":"gpt-5.5",'
                '"openai_models":["gpt-5.5"],'
                '"openai_protocol":"responses"'
                '}',
                encoding='utf-8',
            )

            payload = token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual(token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE, payload['backend_mode'])
        self.assertEqual('https://s2a.example/v1', payload['openai_base_url'])
        self.assertEqual('gpt-5.5', payload['openai_model'])

    def test_load_backend_settings_migrates_top_level_openai_config_to_default_preset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            settings_file.write_text(
                json.dumps(
                    {
                        'backend_mode': 'openai_compatible',
                        'token_dir': 'C:/tokens',
                        'proxy_port': 8317,
                        'proxy_api_key': 'local-proxy-key',
                        'openai_base_url': 'https://s2a.example/v1',
                        'openai_api_key': 'sk-test',
                        'openai_model': 'kimi-k2',
                        'openai_models': ['kimi-k2', 'deepseek-v3'],
                        'openai_protocol': 'responses',
                    }
                ),
                encoding='utf-8',
            )

            payload = token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual('default', payload['active_openai_preset_id'])
        self.assertEqual(1, len(payload['openai_presets']))
        preset = payload['openai_presets'][0]
        self.assertEqual('default', preset['id'])
        self.assertEqual('Default', preset['name'])
        self.assertEqual('https://s2a.example/v1', preset['openai_base_url'])
        self.assertEqual('sk-test', preset['openai_api_key'])
        self.assertEqual('kimi-k2', preset['openai_model'])
        self.assertEqual(['kimi-k2', 'deepseek-v3'], preset['openai_models'])

    def test_save_and_apply_openai_preset_mirrors_active_top_level_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            token_dir = Path(temp_dir) / 'tokens'
            token_pool_settings.save_backend_settings(
                token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key='local-proxy-key',
                openai_base_url='https://first.example/v1',
                openai_api_key='sk-first',
                openai_model='first-model',
                openai_models=['first-model'],
                openai_protocol='responses',
            )

            token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='wanx',
                name='WanX',
                openai_base_url='https://provider-a.example.test/v1',
                openai_api_key='sk-wanx',
                openai_model='gpt-5.5',
                openai_models=['gpt-5.5', 'gpt-5.4'],
                openai_protocol='responses',
                upstream_proxy_url='http://127.0.0.1:7898',
                set_active=False,
            )
            applied = token_pool_settings.apply_openai_preset('wanx', settings_file=settings_file)
            reloaded = token_pool_settings.load_backend_settings(settings_file)

        self.assertEqual('wanx', applied['active_openai_preset_id'])
        self.assertEqual('wanx', reloaded['active_openai_preset_id'])
        self.assertEqual('https://provider-a.example.test/v1', reloaded['openai_base_url'])
        self.assertEqual('sk-wanx', reloaded['openai_api_key'])
        self.assertEqual('gpt-5.5', reloaded['openai_model'])
        self.assertEqual(['gpt-5.5', 'gpt-5.4'], reloaded['openai_models'])
        self.assertEqual('http://127.0.0.1:7898', reloaded['upstream_proxy_url'])
        self.assertEqual(['default', 'wanx'], [item['id'] for item in reloaded['openai_presets']])
        preset = next(item for item in reloaded['openai_presets'] if item['id'] == 'wanx')
        self.assertEqual('http://127.0.0.1:7898', preset['upstream_proxy_url'])

    def test_save_backend_settings_preserves_existing_openai_presets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            token_dir = Path(temp_dir) / 'tokens'
            token_pool_settings.save_backend_settings(
                token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key='local-proxy-key',
                openai_base_url='https://first.example/v1',
                openai_api_key='sk-first',
                openai_model='first-model',
                openai_models=['first-model'],
                openai_protocol='responses',
            )
            token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='wanx',
                name='WanX',
                openai_base_url='https://provider-a.example.test/v1',
                openai_api_key='sk-wanx',
                openai_model='wanx-model',
                openai_models=['wanx-model'],
                openai_protocol='responses',
                set_active=True,
            )

            token_pool_settings.save_backend_settings(
                token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=token_dir,
                proxy_port=8317,
                proxy_api_key='local-proxy-key',
                openai_base_url='https://new.example/v1',
                openai_api_key='sk-new',
                openai_model='new-model',
                openai_models=['new-model'],
                openai_protocol='chat_completions',
            )
            reloaded = token_pool_settings.load_backend_settings(settings_file)

        preset = next(item for item in reloaded['openai_presets'] if item['id'] == 'wanx')
        self.assertEqual('https://provider-a.example.test/v1', preset['openai_base_url'])
        self.assertEqual('sk-wanx', preset['openai_api_key'])
        self.assertEqual('wanx-model', preset['openai_model'])
        self.assertEqual('https://new.example/v1', reloaded['openai_base_url'])
        self.assertEqual('new-model', reloaded['openai_model'])

    def test_save_openai_preset_overwrites_existing_id_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='provider',
                name='Provider',
                openai_base_url='https://old.example/v1',
                openai_api_key='sk-old',
                openai_model='old-model',
                openai_models=['old-model'],
                openai_protocol='responses',
                set_active=True,
            )

            updated = token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='provider',
                name='Provider',
                openai_base_url='https://new.example/v1',
                openai_api_key='sk-new',
                openai_model='new-model',
                openai_models=['new-model'],
                openai_protocol='chat_completions',
                set_active=True,
            )

        self.assertEqual('provider', updated['active_openai_preset_id'])
        presets = {item['id']: item for item in updated['openai_presets']}
        self.assertNotIn('provider-2', presets)
        self.assertEqual('https://new.example/v1', presets['provider']['openai_base_url'])
        self.assertEqual('new-model', presets['provider']['openai_model'])

    def test_save_openai_preset_defaults_to_direct_without_auto_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'

            with mock.patch.object(token_pool_settings, 'detect_proxy_preference') as detect_proxy:
                updated = token_pool_settings.save_openai_preset(
                    settings_file=settings_file,
                    preset_id='provider',
                    name='Provider',
                    openai_base_url='https://new.example/v1',
                    openai_api_key='sk-new',
                    openai_model='new-model',
                    openai_models=['new-model'],
                    openai_protocol='chat_completions',
                    set_active=True,
                )

        detect_proxy.assert_not_called()
        self.assertEqual('direct', updated['proxy_preference'])
        self.assertEqual('direct', updated['openai_presets'][0]['proxy_preference'])

    def test_save_openai_preset_preserves_private_behavior_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'

            updated = token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='private-provider',
                name='Private Provider',
                openai_base_url='https://private.example/v1',
                openai_api_key='sk-test',
                openai_model='private-model',
                openai_models=['private-model'],
                openai_protocol='responses',
                skip_validation=True,
                installation_id='install-test',
                claude_env={'DISABLE_INSTALLATION_CHECKS': '1'},
                disable_image_generation=True,
            )

            reloaded = token_pool_settings.load_backend_settings(settings_file)

        preset = next(item for item in updated['openai_presets'] if item['id'] == 'private-provider')
        reloaded_preset = next(item for item in reloaded['openai_presets'] if item['id'] == 'private-provider')
        self.assertTrue(preset['skip_validation'])
        self.assertEqual('install-test', preset['installation_id'])
        self.assertEqual({'DISABLE_INSTALLATION_CHECKS': '1'}, preset['claude_env'])
        self.assertTrue(preset['disable_image_generation'])
        self.assertEqual(preset['installation_id'], reloaded_preset['installation_id'])

    def test_delete_active_openai_preset_falls_back_to_remaining_preset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / 'token_pool_settings.json'
            token_pool_settings.save_backend_settings(
                token_pool_settings.BACKEND_MODE_OPENAI_COMPATIBLE,
                settings_file=settings_file,
                token_dir=Path(temp_dir) / 'tokens',
                proxy_port=8317,
                proxy_api_key='local-proxy-key',
                openai_base_url='https://default.example/v1',
                openai_api_key='sk-default',
                openai_model='default-model',
                openai_models=['default-model'],
                openai_protocol='responses',
            )
            token_pool_settings.save_openai_preset(
                settings_file=settings_file,
                preset_id='wanx',
                name='WanX',
                openai_base_url='https://provider-a.example.test/v1',
                openai_api_key='sk-wanx',
                openai_model='wanx-model',
                openai_models=['wanx-model'],
                openai_protocol='responses',
                set_active=True,
            )

            updated = token_pool_settings.delete_openai_preset('wanx', settings_file=settings_file)

        self.assertEqual('default', updated['active_openai_preset_id'])
        self.assertEqual(['default'], [item['id'] for item in updated['openai_presets']])
        self.assertEqual('https://default.example/v1', updated['openai_base_url'])
        self.assertEqual('default-model', updated['openai_model'])

    def test_resolve_openai_compatible_backend_config_falls_back_to_returned_model(self) -> None:
        with mock.patch.object(
            token_pool_settings,
            'normalize_openai_base_url',
            side_effect=lambda url, *a, **kw: url.strip().rstrip('/'),
        ), mock.patch.object(
            token_pool_settings,
            'fetch_openai_compatible_models',
            return_value=['mimo-v2.5-pro', 'mimo-v2.0-pro'],
        ) as fetch_models, mock.patch.object(
            token_pool_settings,
            'detect_openai_compatible_protocol',
            return_value=('responses', 'https://token-plan-sgp.xiaomimimo.com/v1'),
        ) as detect_protocol:
            resolved = token_pool_settings.resolve_openai_compatible_backend_config(
                'https://token-plan-sgp.xiaomimimo.com/v1',
                'sk-test',
                'gpt-5.5',
            )

        fetch_models.assert_called_once_with(
            'https://token-plan-sgp.xiaomimimo.com/v1',
            'sk-test',
            timeout_seconds=8.0,
        )
        detect_protocol.assert_called_once_with(
            'https://token-plan-sgp.xiaomimimo.com/v1',
            'sk-test',
            'mimo-v2.5-pro',
            timeout_seconds=5.0,
            _skip_normalize=True,
        )
        self.assertEqual('mimo-v2.5-pro', resolved['openai_model'])
        self.assertEqual(['mimo-v2.5-pro', 'mimo-v2.0-pro'], resolved['openai_models'])

    def test_resolve_openai_compatible_backend_config_uses_explicit_upstream_proxy(self) -> None:
        calls: list[tuple[str, str, str]] = []

        def fake_get(
            url: str,
            headers: dict[str, str],
            timeout: float,
            explicit_proxy: str = '',
        ) -> tuple[int, str]:
            calls.append(('GET', url, explicit_proxy))
            return 200, '{"data":[{"id":"gpt-5.5"}]}'

        def fake_post(
            url: str,
            headers: dict[str, str],
            payload: bytes,
            timeout: float,
            explicit_proxy: str = '',
        ) -> tuple[int, str]:
            calls.append(('POST', url, explicit_proxy))
            return 200, '{"id":"resp_test","output":[{"type":"message"}]}'

        with mock.patch.object(token_pool_settings, '_http_get', side_effect=fake_get), \
             mock.patch.object(token_pool_settings, '_http_post_json', side_effect=fake_post):
            resolved = token_pool_settings.resolve_openai_compatible_backend_config(
                'https://api.example',
                'sk-test',
                'gpt-5.5',
                upstream_proxy_url='http://127.0.0.1:7898',
            )

        self.assertEqual('https://api.example', resolved['openai_base_url'])
        self.assertEqual('gpt-5.5', resolved['openai_model'])
        self.assertTrue(calls)
        self.assertTrue(all(call[2] == 'http://127.0.0.1:7898' for call in calls))

