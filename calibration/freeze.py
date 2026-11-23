import sqlite3

from measurements.bands import require_name
from measurements.revisions import get_revision

from .inspection import inspect_revision
from .references import ReferenceRecord, qualify_reference
from .snapshots import FixedAnalysis, save_fixed_analysis


def freeze(
    conn: sqlite3.Connection, revision_id: str, reference: ReferenceRecord | None = None
) -> FixedAnalysis:
    require_name(revision_id, 'revision id')
    revision = get_revision(conn, revision_id)
    if revision is None:
        raise ValueError(f'unknown revision {revision_id!r}')
    qualification, correction = qualify_reference(revision, reference)
    inspection = inspect_revision(revision, qualification, correction)
    stored_reference = reference
    if correction is not None:
        stored_reference = ReferenceRecord(revision_id, (correction.real, correction.imag))
    conn.execute('BEGIN IMMEDIATE')
    with conn:
        analysis = save_fixed_analysis(conn, revision, stored_reference, inspection)
    return analysis
