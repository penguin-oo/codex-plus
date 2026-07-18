package com.penguinoo.codexmobile;

import java.util.List;

public final class ChatWatchState {
    private static final int INVALIDATE_AFTER_FAILURES = 5;
    private static final String INTERRUPTION_MESSAGE = "Reply interrupted. The response may be incomplete.";
    public static final int FINAL_REFRESH_MAX_ATTEMPTS = 4;

    private ChatWatchState() {
    }

    public static int nextFailureCount(boolean succeeded, int currentFailures) {
        if (succeeded) {
            return 0;
        }
        return Math.max(0, currentFailures) + 1;
    }

    public static boolean shouldInvalidateWatch(int failureCount) {
        return failureCount >= INVALIDATE_AFTER_FAILURES;
    }

    public static boolean shouldApplyLiveUpdate(String watchingJobId, int currentGeneration, int callbackGeneration, PortalJob job) {
        if (job == null || !job.isRunning()) {
            return false;
        }
        if (watchingJobId == null || watchingJobId.isEmpty()) {
            return false;
        }
        if (callbackGeneration != currentGeneration) {
            return false;
        }
        return watchingJobId.equals(job.jobId);
    }

    public static String displayError(PortalJob job) {
        if (job != null && job.error != null && !job.error.trim().isEmpty()) {
            return job.error.trim();
        }
        return INTERRUPTION_MESSAGE;
    }

    public static boolean shouldRefreshTerminalSession(PortalJob job) {
        return job != null && !job.isRunning();
    }

    public static boolean shouldAppendTerminalText(PortalJob job, List<ChatMessage> messages) {
        if (normalizedText(ChatStreamingState.resolveLiveText(job)).isEmpty()) {
            return false;
        }
        if (messages == null) {
            return true;
        }
        for (int index = messages.size() - 1; index >= 0; index--) {
            ChatMessage message = messages.get(index);
            if (message == null || message.isEphemeral) {
                continue;
            }
            if (message.isUser()) {
                return true;
            }
            return false;
        }
        return true;
    }

    public static String bannerAfterCleanRefresh(boolean hasLease, String previousBanner) {
        if (hasLease) {
            return "Mobile is controlling this session.";
        }
        String banner = previousBanner == null ? "" : previousBanner;
        if (INTERRUPTION_MESSAGE.equals(banner.trim())) {
            return "";
        }
        return banner;
    }

    public static boolean shouldRetryFinalRefresh(PortalJob job, List<ChatMessage> messages, int attempt) {
        if (job == null || !job.isCompleted() || attempt >= FINAL_REFRESH_MAX_ATTEMPTS) {
            return false;
        }
        String finalText = normalizedText(job.lastMessage);
        if (finalText.isEmpty()) {
            return false;
        }
        if (messages != null) {
            for (int index = messages.size() - 1; index >= 0; index--) {
                ChatMessage message = messages.get(index);
                if (message == null || message.isEphemeral || message.isUser()) {
                    continue;
                }
                return !finalText.equals(normalizedText(message.text));
            }
        }
        return true;
    }

    private static String normalizedText(String text) {
        if (text == null) {
            return "";
        }
        return text.trim().replaceAll("\\s+", " ");
    }
}
