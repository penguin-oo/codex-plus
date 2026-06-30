import subprocess
import unittest
from unittest import mock

import remote_ssh


class RemoteSshTests(unittest.TestCase):
    def test_build_restart_command_uses_batch_mode_and_shutdown(self) -> None:
        command = remote_ssh.build_restart_command(
            user="codexuser",
            host="100.64.0.10",
            identity_file=r"C:\Users\codexuser\.ssh\id_ed25519_remote",
        )

        self.assertEqual("ssh", command[0])
        self.assertIn("BatchMode=yes", command)
        self.assertIn(r"C:\Users\codexuser\.ssh\id_ed25519_remote", command)
        self.assertIn("codexuser@100.64.0.10", command)
        self.assertEqual("shutdown /r /t 0", command[-1])

    def test_build_restart_command_omits_identity_when_blank(self) -> None:
        command = remote_ssh.build_restart_command(
            user="codexuser",
            host="desktop-example.tailnet-name.ts.net",
            identity_file="",
        )

        self.assertNotIn("-i", command)
        self.assertIn("codexuser@desktop-example.tailnet-name.ts.net", command)

    def test_build_restart_command_uses_plink_when_password_is_provided(self) -> None:
        with mock.patch.object(remote_ssh, "find_plink_executable", return_value=r"C:\PuTTY\plink.exe"):
            command = remote_ssh.build_restart_command(
                user="codexuser",
                host="100.64.0.10",
                password="example-password",
            )

        self.assertEqual(r"C:\PuTTY\plink.exe", command[0])
        self.assertIn("-batch", command)
        self.assertNotIn("-hostkey", command)
        self.assertIn("-pw", command)
        self.assertIn("example-password", command)
        self.assertIn("codexuser@100.64.0.10", command)
        self.assertEqual("shutdown /r /t 0", command[-1])

    def test_build_restart_command_includes_plink_host_key_when_provided(self) -> None:
        with mock.patch.object(remote_ssh, "find_plink_executable", return_value=r"C:\PuTTY\plink.exe"):
            command = remote_ssh.build_restart_command(
                user="codexuser",
                host="100.64.0.10",
                password="example-password",
                host_key="SHA256:abc",
            )

        self.assertIn("-hostkey", command)
        self.assertIn("SHA256:abc", command)

    def test_build_restart_command_rejects_missing_target(self) -> None:
        with self.assertRaises(ValueError):
            remote_ssh.build_restart_command(user="", host="100.64.0.1", identity_file="")
        with self.assertRaises(ValueError):
            remote_ssh.build_restart_command(user="codexuser", host="", identity_file="")

    def test_build_restart_command_reports_missing_plink_for_password_mode(self) -> None:
        with mock.patch.object(remote_ssh, "find_plink_executable", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "plink.exe"):
                remote_ssh.build_restart_command(user="codexuser", host="100.64.0.10", password="example-password")

    def test_restart_computer_runs_built_command(self) -> None:
        completed = subprocess.CompletedProcess(["ssh"], 0, stdout="ok")

        with mock.patch.object(remote_ssh.subprocess, "run", return_value=completed) as run:
            result = remote_ssh.restart_computer(
                user="codexuser",
                host="100.64.0.10",
                identity_file="",
                password="",
                timeout_seconds=12,
            )

        self.assertIs(result, completed)
        run.assert_called_once()
        self.assertEqual(12, run.call_args.kwargs["timeout"])
        self.assertEqual(subprocess.PIPE, run.call_args.kwargs["stdout"])
        self.assertEqual(subprocess.STDOUT, run.call_args.kwargs["stderr"])


if __name__ == "__main__":
    unittest.main()