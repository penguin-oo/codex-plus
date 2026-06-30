package com.penguinoo.codexmobile;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class BackendStatusPayload {
    public final String backendMode;
    public final String tokenDir;
    public final int proxyPort;
    public final boolean proxyRunning;
    public final String proxySummary;
    public final int tokenCount;
    public final String openaiBaseUrl;
    public final String openaiModel;
    public final int openaiModelCount;
    public final String openaiApiKey;
    public final boolean hasOpenAiApiKey;
    public final List<String> openaiModels;
    public final List<OpenAiPresetSummary> openaiPresets;
    public final String activeOpenAiPresetId;
    public final String proxyPreference;
    public final String lastError;
    public final String currentTokenFile;
    public final String currentTokenEmail;
    public final String currentTokenPlanType;
    public final String currentTokenQuotaSummary;

    public BackendStatusPayload(
            String backendMode,
            String tokenDir,
            int proxyPort,
            boolean proxyRunning,
            String proxySummary,
            int tokenCount,
            String openaiBaseUrl,
            String openaiModel,
            int openaiModelCount,
            boolean hasOpenAiApiKey,
            List<String> openaiModels,
            String lastError,
            String currentTokenFile,
            String currentTokenEmail,
            String currentTokenPlanType,
            String currentTokenQuotaSummary
    ) {
        this(
                backendMode,
                tokenDir,
                proxyPort,
                proxyRunning,
                proxySummary,
                tokenCount,
                openaiBaseUrl,
                openaiModel,
                openaiModelCount,
                "",
                hasOpenAiApiKey,
                openaiModels,
                Collections.emptyList(),
                "",
                "direct",
                lastError,
                currentTokenFile,
                currentTokenEmail,
                currentTokenPlanType,
                currentTokenQuotaSummary
        );
    }

    public BackendStatusPayload(
            String backendMode,
            String tokenDir,
            int proxyPort,
            boolean proxyRunning,
            String proxySummary,
            int tokenCount,
            String openaiBaseUrl,
            String openaiModel,
            int openaiModelCount,
            String openaiApiKey,
            boolean hasOpenAiApiKey,
            List<String> openaiModels,
            List<OpenAiPresetSummary> openaiPresets,
            String activeOpenAiPresetId,
            String proxyPreference,
            String lastError,
            String currentTokenFile,
            String currentTokenEmail,
            String currentTokenPlanType,
            String currentTokenQuotaSummary
    ) {
        this.backendMode = backendMode;
        this.tokenDir = tokenDir;
        this.proxyPort = proxyPort;
        this.proxyRunning = proxyRunning;
        this.proxySummary = proxySummary;
        this.tokenCount = tokenCount;
        this.openaiBaseUrl = openaiBaseUrl;
        this.openaiModel = openaiModel;
        this.openaiModelCount = openaiModelCount;
        this.openaiApiKey = openaiApiKey == null ? "" : openaiApiKey;
        this.hasOpenAiApiKey = hasOpenAiApiKey;
        this.openaiModels = openaiModels == null
                ? Collections.emptyList()
                : Collections.unmodifiableList(new ArrayList<>(openaiModels));
        this.openaiPresets = openaiPresets == null
                ? Collections.emptyList()
                : Collections.unmodifiableList(new ArrayList<>(openaiPresets));
        this.activeOpenAiPresetId = activeOpenAiPresetId == null ? "" : activeOpenAiPresetId;
        this.proxyPreference = "proxy".equals(proxyPreference) ? "proxy" : "direct";
        this.lastError = lastError;
        this.currentTokenFile = currentTokenFile;
        this.currentTokenEmail = currentTokenEmail;
        this.currentTokenPlanType = currentTokenPlanType;
        this.currentTokenQuotaSummary = currentTokenQuotaSummary;
    }

    public boolean isTokenPoolMode() {
        return "built_in_token_pool".equalsIgnoreCase(backendMode);
    }

    public boolean isOpenAiCompatibleMode() {
        return "openai_compatible".equalsIgnoreCase(backendMode);
    }

    public boolean isCodexAuthMode() {
        return "codex_auth".equalsIgnoreCase(backendMode) || backendMode == null || backendMode.trim().isEmpty();
    }
}
