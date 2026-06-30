from pathlib import Path
import unittest


class RunMobileLauncherTests(unittest.TestCase):
    def test_launcher_does_not_start_tailscale_ui_client(self) -> None:
        script = Path(__file__).resolve().parents[1] / "run-mobile.bat"
        text = script.read_text(encoding="utf-8").lower()

        self.assertNotIn("tailscale-ipn.exe", text)

    def test_launcher_does_not_start_machine_specific_cloudflared_config(self) -> None:
        script = Path(__file__).resolve().parents[1] / "run-mobile.bat"
        text = script.read_text(encoding="utf-8").lower()

        self.assertNotIn("cloudflared", text)
        self.assertNotIn(".yml", text)


if __name__ == "__main__":
    unittest.main()
