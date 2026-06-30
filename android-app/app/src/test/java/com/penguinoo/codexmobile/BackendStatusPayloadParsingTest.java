package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

public final class BackendStatusPayloadParsingTest {
    @Test
    public void parseBackendStatus_readsTokenPoolFields() throws Exception {
        JSONObject json = new JSONObject()
                .put("backend_mode", "built_in_token_pool")
                .put("token_dir", "C:\\Users\\codexuser\\.cli-proxy-api")
                .put("proxy_port", 8317)
                .put("proxy_running", true)
                .put("proxy_summary", "http://127.0.0.1:8317")
                .put("token_count", 4)
                .put("current_token_quota", new JSONObject()
                        .put("state", "ok")
                        .put("summary", "5h quota: 7% used")
                        .put("token_file", "only.json")
                        .put("email", "beth@example.com")
                        .put("plan_type", "plus"))
                .put("last_error", "");

        BackendStatusPayload payload = PortalApiClient.parseBackendStatus(json);

        assertEquals("built_in_token_pool", payload.backendMode);
        assertEquals(8317, payload.proxyPort);
        assertEquals(4, payload.tokenCount);
        assertTrue(payload.proxyRunning);
        assertTrue(payload.isTokenPoolMode());
        assertEquals("only.json", payload.currentTokenFile);
        assertEquals("beth@example.com", payload.currentTokenEmail);
        assertEquals("5h quota: 7% used", payload.currentTokenQuotaSummary);
    }

    @Test
    public void parseBackendStatus_readsOpenAiCompatibleFields() throws Exception {
        JSONObject json = new JSONObject()
                .put("backend_mode", "openai_compatible")
                .put("token_dir", "")
                .put("proxy_port", 0)
                .put("proxy_running", false)
                .put("proxy_summary", "stopped")
                .put("token_count", 0)
                .put("openai_base_url", "https://api.openai.com/v1")
                .put("openai_model", "gpt-5.5")
                .put("openai_model_count", 2)
                .put("openai_api_key", "sk-top")
                .put("has_openai_api_key", true)
                .put("active_openai_preset_id", "day-60")
                .put("proxy_preference", "proxy")
                .put("openai_models", new JSONArray().put("gpt-5.5").put("gpt-4.1"))
                .put("openai_presets", new JSONArray().put(new JSONObject()
                        .put("id", "day-60")
                        .put("name", "Day 60")
                        .put("openai_base_url", "https://newapi.openedapi.com/v1")
                        .put("openai_model", "gpt-5.5")
                        .put("openai_models", new JSONArray().put("gpt-5.5"))
                        .put("openai_protocol", "responses")
                        .put("openai_api_key", "sk-test")
                        .put("has_openai_api_key", true)
                        .put("proxy_preference", "direct")))
                .put("last_error", "");

        BackendStatusPayload payload = PortalApiClient.parseBackendStatus(json);

        assertEquals("openai_compatible", payload.backendMode);
        assertEquals("https://api.openai.com/v1", payload.openaiBaseUrl);
        assertEquals("gpt-5.5", payload.openaiModel);
        assertEquals(2, payload.openaiModelCount);
        assertEquals("sk-top", payload.openaiApiKey);
        assertTrue(payload.hasOpenAiApiKey);
        assertEquals(Arrays.asList("gpt-5.5", "gpt-4.1"), payload.openaiModels);
        assertEquals("day-60", payload.activeOpenAiPresetId);
        assertEquals("proxy", payload.proxyPreference);
        assertEquals(1, payload.openaiPresets.size());
        assertEquals("Day 60", payload.openaiPresets.get(0).displayName());
        assertEquals("https://newapi.openedapi.com/v1", payload.openaiPresets.get(0).baseUrl);
        assertEquals("sk-test", payload.openaiPresets.get(0).apiKey);
        assertEquals("direct", payload.openaiPresets.get(0).proxyPreference);
        assertTrue(payload.openaiPresets.get(0).hasApiKey);
        assertTrue(payload.isOpenAiCompatibleMode());
    }

    @Test
    public void buildBackendSettingsBody_includesOpenAiFields() throws Exception {
        JSONObject body = PortalApiClient.buildBackendSettingsBody(
                "openai_compatible",
                "C:\\tokens",
                8317,
                "https://api.openai.com/v1",
                "sk-test",
                "gpt-5.5",
                "day-60",
                "Day 60",
                "proxy"
        );

        assertEquals("openai_compatible", body.getString("backend_mode"));
        assertEquals("C:\\tokens", body.getString("token_dir"));
        assertEquals(8317, body.getInt("proxy_port"));
        assertEquals("https://api.openai.com/v1", body.getString("openai_base_url"));
        assertEquals("sk-test", body.getString("openai_api_key"));
        assertEquals("gpt-5.5", body.getString("openai_model"));
        assertEquals("day-60", body.getString("preset_id"));
        assertEquals("Day 60", body.getString("preset_name"));
        assertEquals("proxy", body.getString("proxy_preference"));
    }

    @Test
    public void buildApplyBackendPresetBody_targetsSelectedPreset() throws Exception {
        JSONObject body = PortalApiClient.buildApplyBackendPresetBody("day-60");

        assertEquals("apply", body.getString("preset_action"));
        assertEquals("day-60", body.getString("preset_id"));
    }
}
