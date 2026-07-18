package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;

import org.junit.Test;

public final class ChatWatchStateTest {
    @Test
    public void interruptedJobUsesStableMessageAndKeepsPartialText() {
        PortalJob job = new PortalJob(
                "job-1",
                "failed",
                "session-1",
                "partial reply",
                "",
                "partial reply",
                1,
                "mobile",
                "Mobile"
        );

        assertEquals(
                "Reply interrupted. The response may be incomplete.",
                ChatWatchState.displayError(job)
        );
        assertEquals("partial reply", ChatStreamingState.resolveLiveText(job));
    }

    @Test
    public void completedJobPrefersFinalMessageOverStreamedCommentary() {
        PortalJob job = new PortalJob(
                "job-1",
                "completed",
                "session-1",
                "final answer",
                "",
                "working update",
                1,
                "mobile",
                "Mobile"
        );

        assertEquals("final answer", ChatStreamingState.resolveLiveText(job));
    }

    @Test
    public void completedJobRefreshRetriesUntilFinalMessageAppearsOrLimitIsReached() {
        PortalJob job = new PortalJob(
                "job-1",
                "completed",
                "session-1",
                "final answer",
                "",
                "working update",
                1,
                "mobile",
                "Mobile"
        );

        assertTrue(ChatWatchState.shouldRetryFinalRefresh(
                job,
                Arrays.asList(new ChatMessage("assistant", "working update", 110L, false)),
                0
        ));
        assertFalse(ChatWatchState.shouldRetryFinalRefresh(
                job,
                Arrays.asList(new ChatMessage("assistant", "final answer", 120L, false)),
                0
        ));
        assertFalse(ChatWatchState.shouldRetryFinalRefresh(
                job,
                Arrays.asList(new ChatMessage("assistant", "working update", 110L, false)),
                ChatWatchState.FINAL_REFRESH_MAX_ATTEMPTS
        ));
    }

    @Test
    public void failedJobRefreshesSessionAndDoesNotDuplicatePersistedReply() {
        PortalJob job = new PortalJob(
                "job-1",
                "failed",
                "session-1",
                "recovered answer",
                "",
                "recovered answer",
                1,
                "mobile",
                "Mobile"
        );

        assertTrue(ChatWatchState.shouldRefreshTerminalSession(job));
        assertFalse(ChatWatchState.shouldAppendTerminalText(
                job,
                Arrays.asList(
                        new ChatMessage("user", "question", 110L, false),
                        new ChatMessage("assistant", "recovered answer", 120L, false)
                )
        ));
        assertTrue(ChatWatchState.shouldAppendTerminalText(
                job,
                Arrays.asList(new ChatMessage("user", "question", 110L, false))
        ));
    }

    @Test
    public void cleanRefreshReplacesInterruptedBannerWhenMobileStillOwnsSession() {
        assertEquals(
                "Mobile is controlling this session.",
                ChatWatchState.bannerAfterCleanRefresh(
                        true,
                        "Reply interrupted. The response may be incomplete."
                )
        );
    }

    @Test
    public void cleanReadOnlyRefreshClearsPreviousInterruptedBanner() {
        assertEquals(
                "",
                ChatWatchState.bannerAfterCleanRefresh(
                        false,
                        "Reply interrupted. The response may be incomplete."
                )
        );
    }
}
