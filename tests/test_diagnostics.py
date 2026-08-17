import pytest

from paretopilot.diagnostics import classify_failure
from paretopilot.models import FailureClass


@pytest.mark.parametrize(("log", "expected"), [
    ("ERROR: undeclared identifier", FailureClass.COMPILE),
    ("maximum error exceeds tolerance", FailureClass.NUMERICAL),
    ("dataflow deadlock: no progress", FailureClass.DEADLOCK),
    ("AXI TLAST protocol mismatch", FailureClass.INTERFACE),
    ("max_dsp=12 exceeds 4", FailureClass.RESOURCE),
    ("max_clock_ns=5.2 exceeds 3.0", FailureClass.TIMING),
])
def test_typed_diagnosis(log, expected):
    assert classify_failure(log, 1) is expected
