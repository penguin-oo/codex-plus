import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_mobile_launcher_passes_absolute_script_path(self) -> None:
        launcher = (REPO_ROOT / "run-mobile.bat").read_text(encoding="utf-8")

        self.assertIn('python "%~dp0mobile_portal.py"', launcher)
        self.assertIn('py -3 "%~dp0mobile_portal.py"', launcher)

    def test_desktop_launcher_passes_absolute_script_path(self) -> None:
        launcher = (REPO_ROOT / "run.bat").read_text(encoding="utf-8")

        self.assertIn('py -3 "%~dp0app.py"', launcher)
        self.assertIn('python "%~dp0app.py"', launcher)


if __name__ == "__main__":
    unittest.main()
