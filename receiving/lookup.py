import sqlite3
from dataclasses import dataclass

from phase_evidence.identity import SourceBinding
from phase_evidence.response import PhaseEvidence

from .manifest import VerifiedDelivery, load_received_artifact
from .receipts import Receipt, get_receipt


@dataclass(frozen=True)
class ReceivedItem:
    receipt: Receipt
    delivery: VerifiedDelivery

    @property
    def source(self) -> SourceBinding:
        return self.delivery.envelope.source

    @property
    def evidence(self) -> PhaseEvidence:
        return self.delivery.evidence


def lookup_received(conn: sqlite3.Connection, receipt_id: str) -> ReceivedItem | None:
    receipt = get_receipt(conn, receipt_id)
    if receipt is None:
        return None
    delivery = load_received_artifact(conn, receipt.artifact_id)
    if delivery is None:
        raise sqlite3.IntegrityError('receipt has no corresponding received artifact')
    return ReceivedItem(receipt, delivery)
