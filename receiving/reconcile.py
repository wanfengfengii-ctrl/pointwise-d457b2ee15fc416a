import sqlite3
from dataclasses import dataclass

from measurements.bands import require_name

from .lookup import ReceivedItem, lookup_received


@dataclass(frozen=True)
class ReceivedPair:
    left: ReceivedItem
    right: ReceivedItem


def collect_pair(conn: sqlite3.Connection, receipt_ids: tuple[str, str] | list[str]) -> ReceivedPair:
    if not isinstance(receipt_ids, (list, tuple)) or len(receipt_ids) != 2:
        raise ValueError('review requires exactly two ordered receipt ids')
    left_id, right_id = (require_name(receipt_id, 'receipt id') for receipt_id in receipt_ids)
    left = lookup_received(conn, left_id)
    right = lookup_received(conn, right_id)
    if left is None:
        raise ValueError(f'unknown receipt {left_id!r}')
    if right is None:
        raise ValueError(f'unknown receipt {right_id!r}')
    if left.source.station == right.source.station:
        raise ValueError('review requires artifacts from different stations')
    return ReceivedPair(left, right)
