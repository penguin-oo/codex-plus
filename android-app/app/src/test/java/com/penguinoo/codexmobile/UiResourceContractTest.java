package com.penguinoo.codexmobile;

import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.junit.Test;

public final class UiResourceContractTest {
    @Test
    public void colors_useNeutralOperationalDarkPalette() throws IOException {
        String colors = readResource("values/colors.xml");

        assertTrue(colors.contains("#0B0D10"));
        assertTrue(colors.contains("#44C2A8"));
    }

    @Test
    public void cardAndPanelRadiiStayCompact() throws IOException {
        String card = readResource("drawable/bg_card.xml");
        String panel = readResource("drawable/bg_panel.xml");

        assertTrue(card.contains("android:radius=\"10dp\""));
        assertTrue(panel.contains("android:radius=\"12dp\""));
    }

    @Test
    public void appBrandingUsesCodexPlusNameAndFlatLauncherMark() throws IOException {
        String strings = readResource("values/strings.xml");
        String icon = readResource("drawable/ic_launcher.xml");

        assertTrue(strings.contains("<string name=\"app_name\">Codex+</string>"));
        assertTrue(icon.contains("#0B0D10"));
        assertTrue(icon.contains("#44C2A8"));
        assertTrue(icon.contains("#EEF2F6"));
        assertTrue(icon.contains("M70,26h10v10h10v10h-10v10h-10v-10h-10v-10h10z"));
    }

    private static String readResource(String relativePath) throws IOException {
        Path path = Paths.get("src", "main", "res").resolve(relativePath);
        if (!Files.exists(path)) {
            path = Paths.get("app", "src", "main", "res").resolve(relativePath);
        }
        return new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
    }
}
