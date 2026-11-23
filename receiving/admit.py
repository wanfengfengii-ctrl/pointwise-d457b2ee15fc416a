import sqlite3

from .manifest import initialize_manifest, store_received_artifact, verify_delivery
from .receipts import Receipt, find_receipt_by_artifact, initialize_receipts, save_receipt


def initialize_receiving(conn: sqlite3.Connection) -> None:
    initialize_manifest(conn)
    initialize_receipts(conn)


def accept(conn: sqlite3.Connection, exchange: str, declared_artifact_id: str) -> Receipt:
    delivery = verify_delivery(exchange, declared_artifact_id)
    artifact_id = delivery.envelope.artifact_id
    conn.execute('BEGIN IMMEDIATE')
    with conn:
        receipt = find_receipt_by_artifact(conn, artifact_id)
        if receipt is None:
            store_received_artifact(conn, delivery)
            receipt = save_receipt(conn, artifact_id)
    return receipt
