import json
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from .bands import BandCatalog
from .readings import QuadratureReading, parse_readings


@dataclass(frozen=True)
class Revision:
    revision_id: str
    station: str
    run: str
    previous_revision_id: str | None
    catalog: BandCatalog
    readings: tuple[QuadratureReading, ...]


def initialize_revision_store(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS revisions (
            revision_id TEXT PRIMARY KEY NOT NULL,
            station TEXT NOT NULL,
            run TEXT NOT NULL,
            previous_revision_id TEXT REFERENCES revisions(revision_id),
            readings TEXT NOT NULL
        )
    ''')


def save_revision(
    conn: sqlite3.Connection,
    station: str,
    run: str,
    previous_revision_id: str | None,
    catalog: BandCatalog,
    readings: tuple[QuadratureReading, ...],
) -> Revision:
    revision = Revision(uuid4().hex, station, run, previous_revision_id, catalog, readings)
    payload = [
        [reading.band, str(reading.in_phase), str(reading.quadrature)]
        for reading in readings
    ]
    conn.execute('''
        INSERT INTO revisions (revision_id, station, run, previous_revision_id, readings)
        VALUES (?, ?, ?, ?, ?)
    ''', (revision.revision_id, station, run, previous_revision_id, json.dumps(payload)))
    return revision


def get_revision(conn: sqlite3.Connection, revision_id: str) -> Revision | None:
    row = conn.execute('''
        SELECT revision_id, station, run, previous_revision_id, readings
        FROM revisions WHERE revision_id = ?
    ''', (revision_id,)).fetchone()
    if row is None:
        return None
    stored_id, station, run, previous_revision_id, payload = row
    catalog, readings = parse_readings(json.loads(payload))
    return Revision(stored_id, station, run, previous_revision_id, catalog, readings)
