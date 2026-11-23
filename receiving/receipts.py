import sqlite3
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    artifact_id: str


def initialize_receipts(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id TEXT PRIMARY KEY NOT NULL,
            artifact_id TEXT NOT NULL UNIQUE REFERENCES received_artifacts(artifact_id)
        )
    ''')


def save_receipt(conn: sqlite3.Connection, artifact_id: str) -> Receipt:
    receipt = Receipt(uuid4().hex, artifact_id)
    conn.execute('INSERT INTO receipts (receipt_id, artifact_id) VALUES (?, ?)',
                 (receipt.receipt_id, receipt.artifact_id))
    return receipt


def find_receipt_by_artifact(conn: sqlite3.Connection, artifact_id: str) -> Receipt | None:
    row = conn.execute('SELECT receipt_id, artifact_id FROM receipts WHERE artifact_id = ?',
                       (artifact_id,)).fetchone()
    return None if row is None else Receipt(*row)


def get_receipt(conn: sqlite3.Connection, receipt_id: str) -> Receipt | None:
    row = conn.execute('SELECT receipt_id, artifact_id FROM receipts WHERE receipt_id = ?',
                       (receipt_id,)).fetchone()
    return None if row is None else Receipt(*row)
