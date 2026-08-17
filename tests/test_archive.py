from paretopilot.archive import ParetoArchive, dominates, hypervolume
from paretopilot.models import Candidate, CandidateRecord, EvaluationResult, PPAMetrics, ToolKind


def record(code, latency, lut, task):
    item = CandidateRecord(Candidate(code, None, "test", 0))
    item.evaluations[ToolKind.CSYNTH] = EvaluationResult(
        ToolKind.CSYNTH, True, 0, "", PPAMetrics(latency_cycles=latency, lut=lut)
    )
    return item


def test_hypervolume_and_dominance():
    assert dominates((1.0, 2.0), (1.0, 3.0))
    assert hypervolume([(1.0, 4.0), (3.0, 2.0)], (5.0, 5.0)) == 8.0


def test_archive_retains_tradeoffs(task):
    archive = ParetoArchive(task)
    a = record("a", 100, 100, task)
    b = record("b", 50, 200, task)
    c = record("c", 120, 300, task)
    assert archive.add(a)
    assert archive.add(b)
    assert not archive.add(c)
    assert {r.candidate.code for r in archive.front_2d} == {"a", "b"}
