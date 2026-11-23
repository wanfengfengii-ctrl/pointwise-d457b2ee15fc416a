import json
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from measurements.readings import parse_rational
from phase_evidence.identity import SourceBinding

from .energy import EnergyOutcome
from .request import ReportParent, ReviewRequest, ValidatedRequest


@dataclass(frozen=True)
class SignReceipt:
    receipt_id: str
    report_id: str


@dataclass(frozen=True)
class SignedReport:
    report_id: str
    request: ReviewRequest
    parents: tuple[ReportParent, ReportParent]
    outcome: EnergyOutcome
    receipt: SignReceipt


def initialize_report_store(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY NOT NULL,
            request_snapshot TEXT NOT NULL,
            parents_snapshot TEXT NOT NULL,
            status TEXT NOT NULL,
            energy TEXT,
            CHECK ((status = 'exact' AND energy IS NOT NULL)
                OR (status = 'undetermined' AND energy IS NULL))
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sign_receipts (
            receipt_id TEXT PRIMARY KEY NOT NULL,
            report_id TEXT NOT NULL UNIQUE REFERENCES reports(report_id)
        )
    ''')


def commit_report(
    conn: sqlite3.Connection, validated: ValidatedRequest, outcome: EnergyOutcome
) -> SignedReport:
    report_id = uuid4().hex
    receipt = SignReceipt(uuid4().hex, report_id)
    request = validated.request
    parents = validated.parents
    request_payload = json.dumps({
        'receipt_ids': request.receipt_ids,
        'weights': [(band, str(weight)) for band, weight in request.weights],
    })
    parents_payload = json.dumps([
        {'artifact_id': parent.artifact_id, 'source': parent.source.as_dict()}
        for parent in parents
    ])
    energy = None if outcome.energy is None else str(outcome.energy)
    conn.execute('BEGIN IMMEDIATE')
    with conn:
        conn.execute('''
            INSERT INTO reports (report_id, request_snapshot, parents_snapshot, status, energy)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, request_payload, parents_payload, outcome.status, energy))
        conn.execute('INSERT INTO sign_receipts (receipt_id, report_id) VALUES (?, ?)',
                     (receipt.receipt_id, report_id))
    return SignedReport(report_id, request, parents, outcome, receipt)


def load_signed_record(conn: sqlite3.Connection, report_id: str) -> SignedReport | None:
    row = conn.execute('''
        SELECT reports.report_id, request_snapshot, parents_snapshot, status, energy, receipt_id
        FROM reports JOIN sign_receipts USING (report_id)
        WHERE reports.report_id = ?
    ''', (report_id,)).fetchone()
    if row is None:
        return None
    stored_id, request_snapshot, parents_snapshot, status, energy, receipt_id = row
    request_data = json.loads(request_snapshot)
    left_id, right_id = request_data['receipt_ids']
    request = ReviewRequest((left_id, right_id), tuple(
        (band, parse_rational(weight)) for band, weight in request_data['weights']
    ))
    left, right = (
        ReportParent(data['artifact_id'], SourceBinding(**data['source']))
        for data in json.loads(parents_snapshot)
    )
    outcome = EnergyOutcome(status, None if energy is None else parse_rational(energy))
    return SignedReport(stored_id, request, (left, right), outcome, SignReceipt(receipt_id, stored_id))
