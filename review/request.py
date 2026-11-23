import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from measurements.bands import require_name
from measurements.readings import parse_rational
from phase_evidence.identity import SourceBinding
from receiving.reconcile import ReceivedPair, collect_pair


@dataclass(frozen=True)
class ReviewRequest:
    receipt_ids: tuple[str, str]
    weights: tuple[tuple[str, Fraction], ...]


@dataclass(frozen=True)
class ReportParent:
    artifact_id: str
    source: SourceBinding


@dataclass(frozen=True)
class ValidatedRequest:
    request: ReviewRequest
    pair: ReceivedPair

    @property
    def parents(self) -> tuple[ReportParent, ReportParent]:
        return (
            ReportParent(self.pair.left.receipt.artifact_id, self.pair.left.source),
            ReportParent(self.pair.right.receipt.artifact_id, self.pair.right.source),
        )


def _validate_weights(weights: Mapping[str, object]) -> tuple[tuple[str, Fraction], ...]:
    if not isinstance(weights, Mapping):
        raise ValueError('weights must map bands to rational values')
    parsed = []
    for key, value in weights.items():
        band = require_name(key, 'weight band')
        weight = parse_rational(value)
        if weight < 0:
            raise ValueError(f'negative weight for band {band!r}')
        parsed.append((band, weight))
    if not any(weight > 0 for _, weight in parsed):
        raise ValueError('at least one weight must be positive')
    return tuple(parsed)


def validate_request(
    conn: sqlite3.Connection, receipt_ids: tuple[str, str] | list[str], weights: Mapping[str, object]
) -> ValidatedRequest:
    parsed_weights = _validate_weights(weights)
    pair = collect_pair(conn, receipt_ids)
    left_bands = {band for band, _ in pair.left.evidence.responses}
    right_bands = {band for band, _ in pair.right.evidence.responses}
    for band, _ in parsed_weights:
        if band not in left_bands or band not in right_bands:
            raise ValueError(f'request band {band!r} is missing from at least one artifact')
    request = ReviewRequest((pair.left.receipt.receipt_id, pair.right.receipt.receipt_id), parsed_weights)
    return ValidatedRequest(request, pair)
