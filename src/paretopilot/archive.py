from __future__ import annotations

from dataclasses import dataclass, field

from .models import CandidateRecord, TaskSpec, ToolKind


def dominates(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return len(left) == len(right) and all(a <= b for a, b in zip(left, right)) and any(
        a < b for a, b in zip(left, right)
    )


def _front(points: list[tuple[float, ...]]) -> list[tuple[float, ...]]:
    unique = list(dict.fromkeys(points))
    return [point for point in unique if not any(dominates(other, point) for other in unique if other != point)]


def hypervolume(points: list[tuple[float, ...]], reference: tuple[float, ...]) -> float:
    """Exact minimisation hypervolume for two or three objectives."""
    clean = [p for p in _front(points) if len(p) == len(reference) and all(x < r for x, r in zip(p, reference))]
    if not clean:
        return 0.0
    if len(reference) == 2:
        ordered = sorted(clean, key=lambda p: (p[0], p[1]))
        area, best_y = 0.0, reference[1]
        for x, y in ordered:
            if y < best_y:
                area += (reference[0] - x) * (best_y - y)
                best_y = y
        return area
    if len(reference) == 3:
        xs = sorted({p[0] for p in clean} | {reference[0]})
        volume = 0.0
        for lo, hi in zip(xs, xs[1:]):
            active = [(p[1], p[2]) for p in clean if p[0] <= lo]
            volume += (hi - lo) * hypervolume(active, reference[1:])
        return volume
    raise ValueError("Hypervolume supports two or three objectives")


@dataclass
class ParetoArchive:
    task: TaskSpec
    front_2d: list[CandidateRecord] = field(default_factory=list)
    front_3d: list[CandidateRecord] = field(default_factory=list)
    measured_baseline: dict[str, float] = field(default_factory=dict)

    def _vector(self, record: CandidateRecord) -> tuple[float, ...] | None:
        result = record.ppa_result
        if not result or not result.metrics:
            return None
        return result.metrics.objective_vector(self.task, self.measured_baseline)

    def add(self, record: CandidateRecord) -> bool:
        result = record.ppa_result
        if not result or not result.passed or not result.metrics:
            return False
        if not self.measured_baseline and result.metrics.latency_cycles is not None:
            self.measured_baseline["latency_cycles"] = float(result.metrics.latency_cycles)
        if result.metrics.power_w is not None and "power_w" not in self.measured_baseline:
            self.measured_baseline["power_w"] = result.metrics.power_w
        vector = self._vector(record)
        if vector is None:
            return False
        target = self.front_3d if len(vector) == 3 else self.front_2d
        old_ids = {item.candidate.id for item in target}
        combined = target + [record]
        kept: list[CandidateRecord] = []
        for candidate in combined:
            candidate_vector = self._vector(candidate)
            if candidate_vector is None or len(candidate_vector) != len(vector):
                continue
            if not any(
                other is not candidate
                and (other_vector := self._vector(other)) is not None
                and dominates(other_vector, candidate_vector)
                for other in combined
            ):
                kept.append(candidate)
        target[:] = list({item.candidate.id: item for item in kept}.values())
        return record.candidate.id in {item.candidate.id for item in target} and record.candidate.id not in old_ids

    def hypervolume(self) -> float:
        if self.front_3d:
            records = self.front_3d
            reference = self.task.hv_reference
        else:
            records = self.front_2d
            reference = self.task.hv_reference[:2]
        points: list[tuple[float, ...]] = []
        for record in records:
            vector = self._vector(record)
            if vector:
                points.append(vector)
        return hypervolume(points, reference) if points else 0.0

    def all_records(self) -> list[CandidateRecord]:
        return self.front_3d + [r for r in self.front_2d if r.candidate.id not in {x.candidate.id for x in self.front_3d}]

    def incumbent(self) -> CandidateRecord | None:
        # Never compare a point with missing power numerically against a 3-D point.
        records = self.front_3d if self.front_3d else self.front_2d
        if not records:
            return None
        def key(record: CandidateRecord) -> tuple[float, float, float]:
            vector = self._vector(record) or (float("inf"), float("inf"))
            return (vector[0], vector[1], vector[2] if len(vector) == 3 else float("inf"))
        return min(records, key=key)
