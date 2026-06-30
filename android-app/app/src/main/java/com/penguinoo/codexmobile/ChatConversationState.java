package com.penguinoo.codexmobile;

import java.util.ArrayList;
import java.util.List;

public final class ChatConversationState {
    private ChatConversationState() {
    }

    public static List<ChatMessage> compose(
            List<ChatMessage> persistedMessages,
            ChatMessage pendingUserMessage,
            String liveAssistantText
    ) {
        return compose(persistedMessages, pendingUserMessage, liveAssistantText, true);
    }

    public static List<ChatMessage> compose(
            List<ChatMessage> persistedMessages,
            ChatMessage pendingUserMessage,
            String liveAssistantText,
            boolean liveAssistantEphemeral
    ) {
        List<ChatMessage> pendingMessages = new ArrayList<>();
        if (pendingUserMessage != null) {
            pendingMessages.add(pendingUserMessage);
        }
        return compose(persistedMessages, pendingMessages, liveAssistantText, liveAssistantEphemeral);
    }

    public static List<ChatMessage> compose(
            List<ChatMessage> persistedMessages,
            List<ChatMessage> pendingUserMessages,
            String liveAssistantText
    ) {
        return compose(persistedMessages, pendingUserMessages, liveAssistantText, true);
    }

    public static List<ChatMessage> compose(
            List<ChatMessage> persistedMessages,
            List<ChatMessage> pendingUserMessages,
            String liveAssistantText,
            boolean liveAssistantEphemeral
    ) {
        List<ChatMessage> displayMessages = new ArrayList<>(persistedMessages);
        if (pendingUserMessages != null) {
            displayMessages.addAll(pendingUserMessages);
        }
        if (liveAssistantText != null && !liveAssistantText.isBlank()) {
            displayMessages.add(new ChatMessage("assistant", liveAssistantText, 0L, liveAssistantEphemeral));
        }
        return displayMessages;
    }
}
