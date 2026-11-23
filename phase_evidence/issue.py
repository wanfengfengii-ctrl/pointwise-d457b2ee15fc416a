import sqlite3
from dataclasses import dataclass

from calibration.snapshots import get_fixed_analysis
from measurements.bands import require_name

from .export import ExchangeEnvelope, pack_exchange, unpack_exchange
from .identity import SourceBinding, artifact_identity
from .response import build_evidence, encode_evidence


@dataclass(frozen=True)
class IssuedArtifact:
    artifact_id: str
    source: SourceBinding
    exchange: str


def initialize_issuance_store(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS issued_artifacts (
            artifact_id TEXT PRIMARY KEY NOT NULL,
            analysis_id TEXT NOT NULL REFERENCES fixed_analyses(analysis_id),
            exchange TEXT NOT NULL
        )
    ''')


def issue(conn: sqlite3.Connection, analysis_id: str) -> IssuedArtifact:
    require_name(analysis_id, 'analysis id')
    analysis = get_fixed_analysis(conn, analysis_id)
    if analysis is None:
        raise ValueError(f'unknown fixed analysis {analysis_id!r}')
    source = SourceBinding(analysis.station, analysis.revision_id, analysis.analysis_id)
    body = encode_evidence(build_evidence(analysis))
    artifact_id = artifact_identity(source, body)
    exchange = pack_exchange(ExchangeEnvelope(artifact_id, source, body))
    conn.execute('BEGIN IMMEDIATE')
    with conn:
        conn.execute('''
            INSERT INTO issued_artifacts (artifact_id, analysis_id, exchange) VALUES (?, ?, ?)
            ON CONFLICT (artifact_id) DO NOTHING
        ''', (artifact_id, analysis_id, exchange))
        result = get_issued_artifact(conn, artifact_id)
    if result is None:
        raise sqlite3.IntegrityError('issued artifact is missing from the station ledger')
    return result


def get_issued_artifact(conn: sqlite3.Connection, artifact_id: str) -> IssuedArtifact | None:
    row = conn.execute('SELECT exchange FROM issued_artifacts WHERE artifact_id = ?', (artifact_id,)).fetchone()
    if row is None:
        return None
    exchange = row[0]
    envelope = unpack_exchange(exchange)
    return IssuedArtifact(envelope.artifact_id, envelope.source, exchange)
