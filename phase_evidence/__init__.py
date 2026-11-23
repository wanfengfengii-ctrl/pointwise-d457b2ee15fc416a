import sqlite3

from calibration.snapshots import initialize_analysis_store
from measurements.revisions import initialize_revision_store

from .issue import IssuedArtifact as IssuedArtifact
from .issue import get_issued_artifact as get_issued_artifact
from .issue import initialize_issuance_store
from .issue import issue as issue


def initialize_station(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        raise ValueError('station initialization requires an idle connection')
    conn.execute('PRAGMA foreign_keys = ON')
    initialize_revision_store(conn)
    initialize_analysis_store(conn)
    initialize_issuance_store(conn)
