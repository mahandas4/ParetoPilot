from __future__ import annotations

import re

from .models import FailureClass


_RULES: tuple[tuple[FailureClass, tuple[str, ...]], ...] = (
    (FailureClass.DEADLOCK, (r"deadlock", r"stalled stream", r"stream.*hang", r"read while empty", r"no progress")),
    (FailureClass.NUMERICAL, (r"tolerance", r"\bnan\b", r"\binf(?:inity)?\b", r"precision", r"maximum error")),
    (FailureClass.INTERFACE, (r"interface", r"port .* mismatch", r"\baxi\b", r"\btlast\b", r"protocol")),
    (FailureClass.FUNCTIONAL, (r"mismatch", r"assert(?:ion)?.*fail", r"wrong answer", r"held-out test", r"csim.*fail", r"co-simulation.*fail")),
    (FailureClass.RESOURCE, (r"resource.*exceed", r"utili[sz]ation.*over", r"cannot allocate", r"dsp.*limit", r"max_(?:lut|ff|dsp|bram|uram)=")),
    (FailureClass.TIMING, (r"timing.*fail", r"negative slack", r"target clock.*not met", r"max_clock_ns=")),
    (FailureClass.COMPILE, (r"compilation.*fail", r"syntax error", r"undeclared", r"no matching function", r"expected .* before", r"undefined reference")),
    (FailureClass.TOOL, (r"license", r"tool.*crash", r"internal error", r"timeout", r"not found")),
)


def classify_failure(log: str, returncode: int) -> FailureClass:
    if returncode == 0:
        return FailureClass.NONE
    normalized = log.lower()
    for label, patterns in _RULES:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return label
    return FailureClass.UNKNOWN


def compact_log(log: str, max_chars: int = 8000) -> str:
    if len(log) <= max_chars:
        return log
    half = max_chars // 2
    return log[:half] + "\n... <middle omitted> ...\n" + log[-half:]
