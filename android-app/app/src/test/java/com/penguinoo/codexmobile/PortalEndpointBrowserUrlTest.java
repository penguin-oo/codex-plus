package com.penguinoo.codexmobile;

import static org.junit.Assert.assertEquals;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;

@RunWith(RobolectricTestRunner.class)
public final class PortalEndpointBrowserUrlTest {
    @Test
    public void browserUrl_joinsOriginAndRelativePath() {
        PortalEndpoint endpoint = PortalEndpoint.parse("http://100.64.0.10:8765/?token=verify-token");

        assertEquals(
                "http://100.64.0.10:8765/files/share-1?token=verify-token",
                endpoint.browserUrl("/files/share-1?token=verify-token")
        );
    }
}