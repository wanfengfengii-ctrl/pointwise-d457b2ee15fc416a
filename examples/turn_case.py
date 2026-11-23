import sqlite3
from contextlib import closing, contextmanager

from calibration import ReferenceRecord, freeze
from measurements import record
from phase_evidence import initialize_station, issue
from receiving import accept
from review import get_report, initialize_center, sign

RUN = "pump-turn"
READINGS = (("low", 1, 0),)
WEIGHTS = {"low": 1}
POSITIVE_REAL = (1, 0)
NEGATIVE_REAL = (-1, 0)
POSITIVE_IMAG = (0, 1)
WORK_ORDERS = (
    ("right", (POSITIVE_REAL,), 2),
    ("left", (NEGATIVE_REAL,), 2),
    ("quarter", (POSITIVE_REAL, POSITIVE_IMAG), 2),
    ("opposite-at-limit", (POSITIVE_REAL, NEGATIVE_REAL), 2),
    ("opposite-two-arcs", (POSITIVE_REAL, NEGATIVE_REAL), 3),
    ("opposite-empty", (POSITIVE_REAL, NEGATIVE_REAL), 1),
    ("opposite-full", (POSITIVE_REAL, NEGATIVE_REAL), 4),
)


def prepare_analysis(db, station, *, anchored=False, previous_revision_id=None):
    revision_id = record(db, station, RUN, READINGS, previous_revision_id)
    reference = ReferenceRecord(revision_id, POSITIVE_REAL) if anchored else None
    return freeze(db, revision_id, reference)


@contextmanager
def reject_commit(db):
    denied = []

    def authorize(action, operation, unused, schema, trigger):
        if action == sqlite3.SQLITE_TRANSACTION and operation == "COMMIT":
            denied.append(operation)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    db.set_authorizer(authorize)
    try:
        yield denied
    finally:
        db.set_authorizer(None)


def check_seed():
    with closing(sqlite3.connect(":memory:", cached_statements=0)) as center:
        initialize_center(center)
        with closing(sqlite3.connect(":memory:")) as left, closing(sqlite3.connect(":memory:")) as right:
            initialize_station(left)
            initialize_station(right)
            a = issue(left, prepare_analysis(left, "A").analysis_id)
            b = issue(right, prepare_analysis(right, "B", anchored=True).analysis_id)
            receipts = tuple(accept(center, item.exchange, item.artifact_id) for item in (a, b))
            assert accept(center, a.exchange, a.artifact_id) == receipts[0]
        ids = tuple(receipt.receipt_id for receipt in receipts)
        original = sign(center, ids, WEIGHTS)
        assert original.outcome.status == "undetermined" and original.outcome.energy is None
        assert get_report(center, original.report_id) == original
        before = tuple(center.iterdump())
        with reject_commit(center) as denied:
            try:
                sign(center, ids, WEIGHTS)
            except sqlite3.DatabaseError:
                assert denied
            else:
                raise AssertionError("the fixture did not interrupt the report commit")
        assert not center.in_transaction
        assert tuple(center.iterdump()) == before
        retry = sign(center, ids, WEIGHTS)
        assert retry.report_id != original.report_id
        assert get_report(center, retry.report_id) == retry
        print("V1 low-band review:", original.outcome.status, "energy:", original.outcome.energy)
        print("Commit rejected, previous report preserved and retry stored:", retry.outcome.status)


if __name__ == "__main__":
    check_seed()
