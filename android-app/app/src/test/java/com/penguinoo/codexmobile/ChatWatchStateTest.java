package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;

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
}
