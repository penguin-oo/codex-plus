package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class AccountCenterPresentationTest {
    @Test
    public void currentAccountSummary_includesIdentityModeSlotAndQuota() {
        AccountSlotsPayload payload = new AccountSlotsPayload(
                "slot-2",
                "b@example.com",
                "acct-b",
                "chatgpt",
                "Weekly quota: 76% used",
                "ok",
                false,
                new BackendStatusPayload("codex_auth", "", 0, false, "", 0, "", "", 0, false, java.util.Collections.emptyList(), "", "", "", "", ""),
                java.util.Collections.emptyList()
        );

        String summary = AccountCenterPresentation.currentAccountSummary(
                payload,
                "Not bound yet",
                "Quota unavailable",
                "Backup"
        );

        assertEquals(
                "b@example.com\nMode: chatgpt\nActive slot: Backup\nWeekly quota: 76% used",
                summary
        );
    }

    @Test
    public void slotSummary_marksUnboundSlotsClearly() {
        AccountSlotSummary slot = new AccountSlotSummary(
                "slot-3",
                "Travel",
                "",
                "",
                "",
                false,
                false
        );

        String summary = AccountCenterPresentation.slotSummary(
                slot,
                "Not bound yet",
                "Active now",
                "Ready to switch",
                "Bind the current login here first"
        );

        assertEquals("Not bound yet\nBind the current login here first", summary);
        assertFalse(AccountCenterPresentation.canSwitch(slot));
    }

    @Test
    public void slotSummary_marksActiveBoundSlotsClearly() {
        AccountSlotSummary slot = new AccountSlotSummary(
                "slot-2",
                "Backup",
                "b@example.com",
                "acct-b",
                "chatgpt",
                true,
                true
        );

        String summary = AccountCenterPresentation.slotSummary(
                slot,
                "Not bound yet",
                "Active now",
                "Ready to switch",
                "Bind the current login here first"
        );

        assertEquals("b@example.com\nMode: chatgpt\nActive now", summary);
        assertTrue(AccountCenterPresentation.canSwitch(slot));
    }

    @Test
    public void backendSummary_highlightsOpenAiConfiguration() {
        BackendStatusPayload backend = new BackendStatusPayload(
                "openai_compatible",
                "",
                0,
                false,
                "stopped",
                0,
                "https://api.openai.com/v1",
                "gpt-5.5",
                2,
                true,
                java.util.Arrays.asList("gpt-5.5", "gpt-4.1"),
                "",
                "",
                "",
                "",
                ""
        );

        String summary = AccountCenterPresentation.backendSummary(
                backend,
                "running",
                "stopped"
        );

        assertEquals(
                "Mode: openai_compatible\n" +
                        "Proxy: stopped\n" +
                        "Token files: 0\n" +
                        "Base URL: https://api.openai.com/v1\n" +
                        "Model: gpt-5.5\n" +
                        "Discovered models: 2\n" +
                        "API key: configured",
                summary
        );
    }

    @Test
    public void backendSummary_includesCurrentTokenQuotaForTokenPool() {
        BackendStatusPayload backend = new BackendStatusPayload(
                "built_in_token_pool",
                "C:\\tokens",
                8317,
                true,
                "http://127.0.0.1:8317",
                1,
                "",
                "",
                0,
                false,
                java.util.Collections.emptyList(),
                "",
                "only.json",
                "beth@example.com",
                "plus",
                "5h quota: 7% used\nWeekly quota: 17% used"
        );

        String summary = AccountCenterPresentation.backendSummary(
                backend,
                "running",
                "stopped"
        );

        assertEquals(
                "Mode: built_in_token_pool\n" +
                        "Proxy: http://127.0.0.1:8317\n" +
                        "Token files: 1\n" +
                        "Current token: only.json\n" +
                        "Current token email: beth@example.com\n" +
                        "Current token plan: plus\n" +
                        "Current token quota: 5h quota: 7% used\nWeekly quota: 17% used",
                summary
        );
    }
}
