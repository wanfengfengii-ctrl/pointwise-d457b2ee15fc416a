import sqlite3
from dataclasses import dataclass

from phase_evidence.export import ExchangeEnvelope, unpack_exchange
from phase_evidence.identity import artifact_identity
from phase_evidence.response import PhaseEvidence, decode_evidence, encode_evidence


@dataclass(frozen=True)
class VerifiedDelivery:
    exchange: str
    envelope: ExchangeEnvelope
    evidence: PhaseEvidence


def verify_delivery(exchange: str, declared_artifact_id: str) -> VerifiedDelivery:
    envelope = unpack_exchange(exchange)
    if envelope.artifact_id != declared_artifact_id:
        raise ValueError('declared identity does not match exchange identity')
    evidence = decode_evidence(envelope.body)
    recomputed = artifact_identity(envelope.source, encode_evidence(evidence))
    if recomputed != envelope.artifact_id:
        raise ValueError('exchange identity does not match its source and evidence')
    return VerifiedDelivery(exchange, envelope, evidence)


def initialize_manifest(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS received_artifacts (
            artifact_id TEXT PRIMARY KEY NOT NULL,
            exchange TEXT NOT NULL
        )
    ''')


def store_received_artifact(conn: sqlite3.Connection, delivery: VerifiedDelivery) -> None:
    conn.execute('INSERT INTO received_artifacts (artifact_id, exchange) VALUES (?, ?)',
                 (delivery.envelope.artifact_id, delivery.exchange))


def load_received_artifact(conn: sqlite3.Connection, artifact_id: str) -> VerifiedDelivery | None:
    row = conn.execute('SELECT exchange FROM received_artifacts WHERE artifact_id = ?', (artifact_id,)).fetchone()
    if row is None:
        return None
    return verify_delivery(row[0], artifact_id)
