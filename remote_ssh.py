import subprocess
import shutil
from pathlib import Path


DEFAULT_RESTART_TIMEOUT_SECONDS = 30


def find_plink_executable() -> str | None:
    found = shutil.which("plink.exe") or shutil.which("plink")
    if found:
        return found
    for candidate in (
        Path(r"C:\Program Files\PuTTY\plink.exe"),
        Path(r"C:\Program Files (x86)\PuTTY\plink.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None

def build_restart_command(
    *,
    user: str,
    host: str,
    identity_file: str = "",
    password: str = "",
    host_key: str = "",
) -> list[str]:
    clean_user = user.strip()
    clean_host = host.strip()
    if not clean_user:
        raise ValueError("SSH user is required.")
    if not clean_host:
        raise ValueError("Tailscale host is required.")

    clean_password = password.strip()
    if clean_password:
        plink_executable = find_plink_executable()
        if not plink_executable:
            raise RuntimeError("Password mode requires plink.exe. Install PuTTY or add plink.exe to PATH.")
        return [
            plink_executable,
            "-ssh",
            "-batch",
            *(["-hostkey", host_key.strip()] if host_key.strip() else []),
            "-pw",
            clean_password,
            f"{clean_user}@{clean_host}",
            "shutdown /r /t 0",
        ]

    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    clean_identity = identity_file.strip()
    if clean_identity:
        command.extend(["-i", str(Path(clean_identity))])
    command.extend([f"{clean_user}@{clean_host}", "shutdown /r /t 0"])
    return command


def restart_computer(
    *,
    user: str,
    host: str,
    identity_file: str = "",
    password: str = "",
    host_key: str = "",
    timeout_seconds: int = DEFAULT_RESTART_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    command = build_restart_command(
        user=user,
        host=host,
        identity_file=identity_file,
        password=password,
        host_key=host_key,
    )
    return subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
