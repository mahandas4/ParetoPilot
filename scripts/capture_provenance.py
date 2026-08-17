#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def command(argv: list[str]) -> str | None:
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip() or None


def main() -> None:
    files = {}
    for path in sorted((ROOT / "benchmarks").rglob("*")):
        if path.is_file():
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    data = {
        "git_commit": command(["git", "rev-parse", "HEAD"]),
        "git_dirty": command(["git", "status", "--porcelain"]),
        "python": sys.version,
        "platform": platform.platform(),
        "vitis_hls_version": command(["vitis_hls", "-version"]),
        "vivado_version": command(["vivado", "-version"]),
        "benchmark_sha256": files,
    }
    destination = ROOT / "PROVENANCE.json"
    destination.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
