import json
import unittest
from unittest import mock

import custom_provider_proxy
import token_pool_settings


class CustomProviderProxyTranslationTests(unittest.TestCase):
    def test_build_health_payload_reports_openai_compatible_backend_mode(self) -> None:
        proxy = custom_provider_proxy.CustomProviderProxyApp(
            local_api_key="local-proxy-key",
            proxy_port=8317,
            upstream_base_url="https://api.openai.com/v1",
            upstream_api_key="sk-test",
            upstream_protocol="chat_completions",
            model_ids=["mimo-v2.5-pro"],
            upstream_proxy_url="http://127.0.0.1:7898",
        )

        payload = proxy.build_health_payload()

        self.assertEqual("ok", payload["status"])
        self.assertEqual("openai_compatible", payload["backend_mode"])
        self.assertEqual(8317, payload["port"])
        self.assertEqual(
            token_pool_settings.openai_compatible_proxy_config_fingerprint(
                local_api_key="local-proxy-key",
                upstream_base_url="https://api.openai.com/v1",
                upstream_api_key="sk-test",
                upstream_protocol="chat_completions",
                model_ids=["mimo-v2.5-pro"],
                upstream_proxy_url="http://127.0.0.1:7898",
            ),
            payload["config_fingerprint"],
        )

    def test_handler_accepts_models_route_with_query_string(self) -> None:
        proxy = custom_provider_proxy.CustomProviderProxyApp(
            local_api_key="local-proxy-key",
            proxy_port=8317,
            upstream_base_url="https://api.openai.com/v1",
            upstream_api_key="sk-test",
            upstream_protocol="chat_completions",
            model_ids=["gpt-5.5"],
        )
        handler = custom_provider_proxy.CustomProviderProxyHandler.__new__(
            custom_provider_proxy.CustomProviderProxyHandler
        )
        handler.path = "/models?client_version=0.140.0"
        handler.headers = {"Authorization": "Bearer local-proxy-key"}
        handler.server = type("Server", (), {"proxy_app": proxy})()

        with mock.patch.object(handler, "_write_response") as write_response:
            handler.do_GET()

        response = write_response.call_args.args[0]
        self.assertEqual(200, response.status_code)
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual("gpt-5.5", payload["data"][0]["id"])
        self.assertEqual("gpt-5.5", payload["models"][0]["slug"])
        self.assertEqual("medium", payload["models"][0]["default_reasoning_level"])
        self.assertTrue(payload["models"][0]["supported_reasoning_levels"])

    def test_translate_responses_request_to_chat_completions_includes_instructions_and_text(self) -> None:
        payload = {
            "model": "mimo-v2-pro",
            "instructions": "You are strict.",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Hello"}],
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "name": "lookup_weather",
                    "description": "Lookup weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                }
            ],
            "max_output_tokens": 32,
        }

        translated = custom_provider_proxy.translate_responses_request_to_chat_completions(payload)

        self.assertEqual("mimo-v2-pro", translated["model"])
        self.assertEqual("developer", translated["messages"][0]["role"])
        self.assertEqual("You are strict.", translated["messages"][0]["content"])
        self.assertEqual("user", translated["messages"][1]["role"])
        self.assertEqual("Hello", translated["messages"][1]["content"][0]["text"])
        self.assertEqual("text", translated["messages"][1]["content"][0]["type"])
        self.assertEqual("lookup_weather", translated["tools"][0]["function"]["name"])
        self.assertEqual(32, translated["max_tokens"])
        self.assertFalse(translated["stream"])

    def test_translate_responses_request_to_chat_completions_maps_image_inputs(self) -> None:
        payload = {
            "model": "mimo-v2-pro",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Describe this image"},
                        {"type": "input_image", "image_url": "data:image/png;base64,abc", "detail": "high"},
                    ],
                }
            ],
        }

        translated = custom_provider_proxy.translate_responses_request_to_chat_completions(payload)

        self.assertEqual("Describe this image", translated["messages"][0]["content"][0]["text"])
        self.assertEqual("image_url", translated["messages"][0]["content"][1]["type"])
        self.assertEqual("data:image/png;base64,abc", translated["messages"][0]["content"][1]["image_url"]["url"])
        self.assertEqual("high", translated["messages"][0]["content"][1]["image_url"]["detail"])

    def test_translate_responses_request_to_chat_completions_downgrades_orphan_tool_output_items(self) -> None:
        payload = {
            "model": "mimo-v2-pro",
            "input": [
                {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": '{"ok":true}',
                }
            ],
        }

        translated = custom_provider_proxy.translate_responses_request_to_chat_completions(payload)

        self.assertEqual("user", translated["messages"][0]["role"])
        self.assertIn("call_123", translated["messages"][0]["content"])
        self.assertIn('{"ok":true}', translated["messages"][0]["content"])

    def test_translate_responses_request_to_chat_completions_pairs_function_call_outputs(self) -> None:
        payload = {
            "model": "mimo-v2-pro",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Use the tool."}],
                },
                {
                    "type": "function_call",
                    "call_id": "call_123",
                    "name": "lookup_weather",
                    "arguments": '{"city":"Shanghai"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": '{"ok":true}',
                },
            ],
        }

        translated = custom_provider_proxy.translate_responses_request_to_chat_completions(payload)

        self.assertEqual("assistant", translated["messages"][1]["role"])
        self.assertEqual(
            [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "lookup_weather",
                        "arguments": '{"city":"Shanghai"}',
                    },
                }
            ],
            translated["messages"][1]["tool_calls"],
        )
        self.assertEqual("tool", translated["messages"][2]["role"])
        self.assertEqual("call_123", translated["messages"][2]["tool_call_id"])
        self.assertEqual('{"ok":true}', translated["messages"][2]["content"])

    def test_translate_chat_completion_to_responses_output_maps_text_and_tool_calls(self) -> None:
        completion = {
            "id": "chatcmpl_123",
            "model": "mimo-v2-pro",
            "created": 1710000000,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": "Need tool data first.",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "lookup_weather",
                                    "arguments": '{"city":"Shanghai"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        response_payload = custom_provider_proxy.translate_chat_completion_to_responses_output(completion)

        self.assertEqual("response", response_payload["object"])
        self.assertEqual("mimo-v2-pro", response_payload["model"])
        self.assertEqual("message", response_payload["output"][0]["type"])
        self.assertEqual("Need tool data first.", response_payload["output"][0]["content"][0]["text"])
        self.assertEqual("function_call", response_payload["output"][1]["type"])
        self.assertEqual("lookup_weather", response_payload["output"][1]["name"])
        self.assertEqual('{"city":"Shanghai"}', response_payload["output"][1]["arguments"])
        self.assertEqual(10, response_payload["usage"]["input_tokens"])
        self.assertEqual(5, response_payload["usage"]["output_tokens"])
        self.assertEqual(15, response_payload["usage"]["total_tokens"])
        self.assertEqual(0, response_payload["usage"]["input_tokens_details"]["cached_tokens"])
        self.assertEqual(0, response_payload["usage"]["output_tokens_details"]["reasoning_tokens"])

    def test_chat_completion_error_response_maps_200_business_error_to_502(self) -> None:
        completion = {"code": 0, "msg": "route closed", "data": None}

        response = custom_provider_proxy.chat_completion_error_response(completion)

        self.assertIsNotNone(response)
        self.assertEqual(502, response.status_code)
        self.assertIn("route closed", response.body.decode("utf-8"))

    def test_build_responses_sse_from_chat_completion_emits_text_and_completion_events(self) -> None:
        completion = {
            "id": "chatcmpl_123",
            "model": "mimo-v2-pro",
            "created": 1710000000,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "Hello world",
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        }

        chunks = list(custom_provider_proxy.build_responses_sse_from_chat_completion(completion))
        joined = b"".join(chunks).decode("utf-8")

        self.assertIn("response.output_text.delta", joined)
        self.assertIn("Hello world", joined)
        self.assertIn("response.completed", joined)
        self.assertIn('"input_tokens": 10', joined)
        self.assertIn('"output_tokens": 2', joined)
        self.assertIn('"total_tokens": 12', joined)

    def test_normalize_chat_completion_usage_maps_prompt_and_completion_tokens(self) -> None:
        usage = custom_provider_proxy.normalize_chat_completion_usage(
            {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
                "prompt_tokens_details": {"cached_tokens": 3},
                "completion_tokens_details": {"reasoning_tokens": 2},
            }
        )

        self.assertEqual(
            {
                "input_tokens": 11,
                "input_tokens_details": {"cached_tokens": 3},
                "output_tokens": 7,
                "output_tokens_details": {"reasoning_tokens": 2},
                "total_tokens": 18,
            },
            usage,
        )

    def test_responses_protocol_streams_upstream_sse_without_buffering(self) -> None:
        proxy = custom_provider_proxy.CustomProviderProxyApp(
            local_api_key="local-proxy-key",
            proxy_port=8317,
            upstream_base_url="https://api.openai.com/v1",
            upstream_api_key="sk-test",
            upstream_protocol=token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            model_ids=["mimo-v2.5-pro"],
        )
        stream_response = custom_provider_proxy.StreamingForwardResponse(
            status_code=200,
            headers={"content-type": "text/event-stream"},
            chunk_iterator=iter([b"event: response.completed\n\n"]),
            raw_response=object(),
        )

        with mock.patch.object(proxy, "_forward_responses_request", return_value=stream_response) as forward:
            response = proxy.forward_request(
                "Bearer local-proxy-key",
                json.dumps({"model": "mimo-v2.5-pro", "input": "ping", "stream": True}).encode("utf-8"),
                path="/responses",
            )

        self.assertIs(response, stream_response)
        forward.assert_called_once()
        self.assertEqual("/responses", forward.call_args.args[0])

    def test_responses_protocol_maps_compact_route_to_responses_upstream(self) -> None:
        proxy = custom_provider_proxy.CustomProviderProxyApp(
            local_api_key="local-proxy-key",
            proxy_port=8317,
            upstream_base_url="https://api.openai.com/v1",
            upstream_api_key="sk-test",
            upstream_protocol=token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            model_ids=["mimo-v2.5-pro"],
        )
        ok_response = custom_provider_proxy.ForwardResponse(
            status_code=200,
            body=b'{"id":"resp_test","status":"completed"}',
            headers={"content-type": "application/json"},
        )

        with mock.patch.object(proxy, "_forward_responses_request", return_value=ok_response) as forward:
            response = proxy.forward_request(
                "Bearer local-proxy-key",
                json.dumps({"model": "mimo-v2.5-pro", "input": "compact"}).encode("utf-8"),
                path="/responses/compact",
            )

        self.assertIs(response, ok_response)
        forward.assert_called_once()
        self.assertEqual("/responses", forward.call_args.args[0])

    def test_responses_protocol_falls_back_to_chat_completions_when_output_is_empty(self) -> None:
        proxy = custom_provider_proxy.CustomProviderProxyApp(
            local_api_key="local-proxy-key",
            proxy_port=8317,
            upstream_base_url="https://example.invalid/v1",
            upstream_api_key="sk-test",
            upstream_protocol=token_pool_settings.OPENAI_PROTOCOL_RESPONSES,
            model_ids=["gpt-5.4"],
        )
        empty_response = custom_provider_proxy.ForwardResponse(
            status_code=200,
            body=b'{"id":"resp_empty","output":[]}',
            headers={"content-type": "application/json"},
        )
        chat_body = json.dumps(
            {
                "id": "chatcmpl_123",
                "model": "gpt-5.4",
                "choices": [{"message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")

        with mock.patch.object(proxy, "_forward_responses_request", return_value=empty_response) as forward_responses, \
             mock.patch.object(proxy, "_forward_json_request", return_value=(200, chat_body, {"content-type": "application/json"})) as forward_chat:
            response = proxy.forward_request(
                "Bearer local-proxy-key",
                json.dumps({"model": "gpt-5.4", "input": "ping", "stream": False}).encode("utf-8"),
                path="/responses",
            )

        self.assertIsInstance(response, custom_provider_proxy.ForwardResponse)
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual("pong", payload["output"][0]["content"][0]["text"])
        forward_responses.assert_called_once()
        forward_chat.assert_called_once()
        self.assertEqual("/chat/completions", forward_chat.call_args.args[0])

    def test_build_upstream_headers_preserves_codex_client_headers_without_overriding_user_agent(self) -> None:
        headers = custom_provider_proxy.build_upstream_headers(
            upstream_api_key="test-upstream",
            accept="application/json",
            client_headers={
                "Authorization": "Bearer local-proxy-key",
                "Host": "127.0.0.1:8317",
                "Content-Length": "123",
                "User-Agent": "codex_exec/0.137.0",
                "originator": "codex_exec",
                "x-codex-window-id": "window-1",
                "x-client-request-id": "request-1",
                "session-id": "session-1",
                "thread-id": "thread-1",
            },
        )

        self.assertEqual("Bearer test-upstream", headers["Authorization"])
        self.assertEqual(custom_provider_proxy.DEFAULT_UPSTREAM_USER_AGENT, headers["User-Agent"])
        self.assertEqual("codex_exec", headers["originator"])
        self.assertEqual("window-1", headers["x-codex-window-id"])
        self.assertEqual("request-1", headers["x-client-request-id"])
        self.assertEqual("session-1", headers["session-id"])
        self.assertEqual("thread-1", headers["thread-id"])
        self.assertNotIn("Host", headers)
        self.assertNotIn("Content-Length", headers)

    def test_proxy_aware_urlopen_forces_direct_opener_before_proxy_fallback(self) -> None:
        request = custom_provider_proxy.url_request.Request("https://example.invalid/responses")
        response = mock.Mock()
        response.headers = {"content-type": "application/json"}
        direct_opener = mock.Mock()
        direct_opener.open.return_value = response

        with mock.patch.object(custom_provider_proxy, "_detect_system_proxy", return_value="http://127.0.0.1:7897"), \
             mock.patch.object(custom_provider_proxy.url_request, "ProxyHandler", side_effect=lambda proxies: ("proxy", proxies)), \
             mock.patch.object(custom_provider_proxy.url_request, "build_opener", return_value=direct_opener) as build_opener:
            result = custom_provider_proxy._proxy_aware_urlopen(request, timeout=1)

        self.assertIs(response, result)
        build_opener.assert_called_once_with(("proxy", {}))
        direct_opener.open.assert_called_once_with(request, timeout=1)

    def test_proxy_aware_urlopen_uses_explicit_upstream_proxy_without_direct_attempt(self) -> None:
        request = custom_provider_proxy.url_request.Request("https://example.invalid/responses")
        response = mock.Mock()
        proxy_opener = mock.Mock()
        proxy_opener.open.return_value = response

        with mock.patch.object(custom_provider_proxy, "_detect_system_proxy", return_value=None), \
             mock.patch.object(custom_provider_proxy.url_request, "ProxyHandler", side_effect=lambda proxies: ("proxy", proxies)), \
             mock.patch.object(custom_provider_proxy.url_request, "build_opener", return_value=proxy_opener) as build_opener:
            result = custom_provider_proxy._proxy_aware_urlopen(
                request,
                timeout=1,
                explicit_proxy="http://127.0.0.1:7898",
            )

        self.assertIs(response, result)
        build_opener.assert_called_once_with(("proxy", {"http": "http://127.0.0.1:7898", "https": "http://127.0.0.1:7898"}))
        proxy_opener.open.assert_called_once_with(request, timeout=1)

    def test_main_accepts_chat_completions_upstream_protocol(self) -> None:
        with mock.patch.object(custom_provider_proxy, "run_server", return_value=0) as run_server:
            result = custom_provider_proxy.main(
                [
                    "--api-key",
                    "local-proxy-key",
                    "--port",
                    "8317",
                    "--upstream-base-url",
                    "https://gptcode.top/v1",
                    "--upstream-api-key",
                    "test-upstream",
                    "--upstream-protocol",
                    "chat_completions",
                    "--upstream-proxy-url",
                    "http://127.0.0.1:7898",
                    "--model",
                    "gpt-5.4",
                ]
            )

        self.assertEqual(0, result)
        run_server.assert_called_once_with(
            api_key="local-proxy-key",
            port=8317,
            upstream_base_url="https://gptcode.top/v1",
            upstream_api_key="test-upstream",
            upstream_protocol="chat_completions",
            upstream_proxy_url="http://127.0.0.1:7898",
            model_ids=["gpt-5.4"],
        )


if __name__ == "__main__":
    unittest.main()

