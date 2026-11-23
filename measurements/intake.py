import sqlite3

from .bands import require_name
from .lineage import require_predecessor
from .readings import parse_readings
from .revisions import save_revision


def record(
    conn: sqlite3.Connection,
    station: str,
    run: str,
    rows: object,
    previous_revision_id: str | None = None,
) -> str:
    station = require_name(station, 'station')
    run = require_name(run, 'run')
    catalog, readings = parse_readings(rows)
    conn.execute('BEGIN IMMEDIATE')
    with conn:
        require_predecessor(conn, station, run, previous_revision_id)
        revision = save_revision(conn, station, run, previous_revision_id, catalog, readings)
    return revision.revision_id
