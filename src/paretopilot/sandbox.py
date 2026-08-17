from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class CommandSandbox(Protocol):
    host_binary_required: bool

    def run(self, argv: list[str], cwd: Path, timeout_s: int, env: dict[str, str]) -> ProcessResult: ...


class LocalSandbox:
    """Fresh working directories only; this is not a security boundary."""

    host_binary_required = True

    def run(self, argv: list[str], cwd: Path, timeout_s: int, env: dict[str, str]) -> ProcessResult:
        process = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout_s,
            env={**os.environ, **env}, check=False,
        )
        return ProcessResult(process.returncode, process.stdout, process.stderr)


class ContainerSandbox:
    """Restricted Docker/Podman runner for untrusted generated code."""

    host_binary_required = False

    def __init__(self, image: str, engine: str = "docker", memory: str = "8g", cpus: float = 4.0):
        self.image, self.engine, self.memory, self.cpus = image, engine, memory, cpus

    def run(self, argv: list[str], cwd: Path, timeout_s: int, env: dict[str, str]) -> ProcessResult:
        host_root = str(cwd.resolve())
        mapped = [part.replace(host_root, "/work") for part in argv]
        command = [
            self.engine, "run", "--rm", "--network=none", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=512",
            f"--memory={self.memory}", f"--cpus={self.cpus}",
            "--read-only", "--tmpfs=/tmp:rw,noexec,nosuid,size=2g",
            "-v", f"{host_root}:/work:rw", "-w", "/work",
        ]
        for key, value in env.items():
            command.extend(["-e", f"{key}={value}"])
        command.extend([self.image, *mapped])
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s, check=False)
        return ProcessResult(process.returncode, process.stdout, process.stderr)
