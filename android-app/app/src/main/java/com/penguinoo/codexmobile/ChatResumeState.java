package com.penguinoo.codexmobile;

public final class ChatResumeState {
    private ChatResumeState() {
    }

    public static boolean shouldReloadSessionOnResume(boolean hasCurrentSession) {
        return hasCurrentSession;
    }

    public static boolean shouldKeepWatcherAttached(boolean hasRunningJob) {
        return hasRunningJob;
    }

    public static boolean shouldKeepSessionClaim(boolean hasRunningJob, boolean hasPendingSend) {
        return hasRunningJob || hasPendingSend;
    }
}
