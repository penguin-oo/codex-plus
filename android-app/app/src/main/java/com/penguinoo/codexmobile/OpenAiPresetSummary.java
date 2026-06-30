package com.penguinoo.codexmobile;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class OpenAiPresetSummary {
    public final String id;
    public final String name;
    public final String baseUrl;
    public final String model;
    public final List<String> models;
    public final String protocol;
    public final String apiKey;
    public final String proxyPreference;
    public final boolean hasApiKey;

    public OpenAiPresetSummary(
            String id,
            String name,
            String baseUrl,
            String model,
            List<String> models,
            String protocol,
            String apiKey,
            String proxyPreference,
            boolean hasApiKey
    ) {
        this.id = id == null ? "" : id;
        this.name = name == null ? "" : name;
        this.baseUrl = baseUrl == null ? "" : baseUrl;
        this.model = model == null ? "" : model;
        this.models = models == null
                ? Collections.emptyList()
                : Collections.unmodifiableList(new ArrayList<>(models));
        this.protocol = protocol == null ? "" : protocol;
        this.apiKey = apiKey == null ? "" : apiKey;
        this.proxyPreference = "proxy".equals(proxyPreference) ? "proxy" : "direct";
        this.hasApiKey = hasApiKey;
    }

    public String displayName() {
        if (!name.trim().isEmpty()) {
            return name.trim();
        }
        return id.trim();
    }

    public String detailText(String currentPresetLabel) {
        StringBuilder builder = new StringBuilder();
        builder.append(currentPresetLabel == null || currentPresetLabel.trim().isEmpty()
                ? "Current preset"
                : currentPresetLabel.trim());
        builder.append(": ").append(displayName().isEmpty() ? "-" : displayName());
        builder.append("\nBase URL: ").append(baseUrl.trim().isEmpty() ? "-" : baseUrl.trim());
        builder.append("\nModel: ").append(model.trim().isEmpty() ? "-" : model.trim());
        builder.append("\nProtocol: ").append(protocol.trim().isEmpty() ? "unverified" : protocol.trim());
        builder.append("\nProxy: ").append(proxyPreference);
        builder.append("\nModels: ").append(models.size());
        builder.append("\nAPI key: ").append(apiKey.trim().isEmpty() ? (hasApiKey ? "saved" : "missing") : apiKey.trim());
        return builder.toString();
    }
}
