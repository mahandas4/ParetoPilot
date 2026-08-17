from paretopilot.experiment import wilson_interval


def test_wilson_interval_contains_observed_rate():
    low, high = wilson_interval(8, 10)
    assert low < 0.8 < high
    assert 0 <= low <= high <= 1
