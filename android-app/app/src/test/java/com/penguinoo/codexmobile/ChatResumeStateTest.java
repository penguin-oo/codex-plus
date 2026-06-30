package com.penguinoo.codexmobile;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class ChatResumeStateTest {
    @Test
    public void shouldReloadSessionOnResume_whenSessionLoaded_returnsTrue() {
        assertTrue(ChatResumeState.shouldReloadSessionOnResume(true));
    }

    @Test
    public void shouldReloadSessionOnResume_whenSessionMissing_returnsFalse() {
        assertFalse(ChatResumeState.shouldReloadSessionOnResume(false));
    }

    @Test
    public void shouldKeepWatcherAttached_whenActivityBackgroundedAndJobRunning_returnsTrue() {
        assertTrue(ChatResumeState.shouldKeepWatcherAttached(true));
    }

    @Test
    public void shouldKeepWatcherAttached_whenNoJobRunning_returnsFalse() {
        assertFalse(ChatResumeState.shouldKeepWatcherAttached(false));
    }

    @Test
    public void shouldKeepSessionClaim_whenSendIsStillSubmitting_returnsTrue() {
        assertTrue(ChatResumeState.shouldKeepSessionClaim(false, true));
    }

    @Test
    public void shouldKeepSessionClaim_whenJobIsRunning_returnsTrue() {
        assertTrue(ChatResumeState.shouldKeepSessionClaim(true, false));
    }

    @Test
    public void shouldKeepSessionClaim_whenIdle_returnsFalse() {
        assertFalse(ChatResumeState.shouldKeepSessionClaim(false, false));
    }
}
