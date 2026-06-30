package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;

import java.util.Arrays;

import org.junit.Test;

public final class OpenAiPresetSummaryTest {
    @Test
    public void detailText_showsPresetApiConfiguration() {
        OpenAiPresetSummary preset = new OpenAiPresetSummary(
                "day-60",
                "Day 60",
                "https://api.example.com/v1",
                "gpt-5.5",
                Arrays.asList("gpt-5.5", "gpt-5.4"),
                "responses",
                "sk-test",
                "proxy",
                true
        );

        assertEquals(
                "Current preset: Day 60\n" +
                        "Base URL: https://api.example.com/v1\n" +
                        "Model: gpt-5.5\n" +
                        "Protocol: responses\n" +
                        "Proxy: proxy\n" +
                        "Models: 2\n" +
                        "API key: sk-test",
                preset.detailText("Current preset")
        );
    }
}
