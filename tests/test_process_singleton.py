import unittest
from pathlib import Path

import process_singleton


class ProcessSingletonTests(unittest.TestCase):
    def test_should_cleanup_old_project_app_process(self) -> None:
        self.assertTrue(
            process_singleton.should_cleanup_process(
                process_id=101,
                command_line=r"C:\Python314\python.exe D:\repo\app.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids={303},
            )
        )

    def test_should_not_cleanup_current_or_protected_processes(self) -> None:
        self.assertFalse(
            process_singleton.should_cleanup_process(
                process_id=202,
                command_line=r"C:\Python314\python.exe D:\repo\app.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids={303},
            )
        )
        self.assertFalse(
            process_singleton.should_cleanup_process(
                process_id=303,
                command_line=r"C:\Python314\python.exe D:\repo\mobile_portal.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids={303},
            )
        )

    def test_should_not_cleanup_different_project_or_unrelated_python(self) -> None:
        self.assertFalse(
            process_singleton.should_cleanup_process(
                process_id=101,
                command_line=r"C:\Python314\python.exe D:\other\app.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids=set(),
            )
        )
        self.assertFalse(
            process_singleton.should_cleanup_process(
                process_id=101,
                command_line=r"C:\Python314\python.exe -m pip install requests",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids=set(),
            )
        )

    def test_mobile_marker_only_cleans_mobile_portal(self) -> None:
        self.assertTrue(
            process_singleton.should_cleanup_process(
                process_id=101,
                command_line=r"C:\Python314\python.exe D:\repo\mobile_portal.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids=set(),
                markers=("mobile_portal.py",),
            )
        )
        self.assertFalse(
            process_singleton.should_cleanup_process(
                process_id=101,
                command_line=r"C:\Python314\python.exe D:\repo\app.py",
                app_dir=Path(r"D:\repo"),
                current_pid=202,
                protected_pids=set(),
                markers=("mobile_portal.py",),
            )
        )


if __name__ == "__main__":
    unittest.main()
