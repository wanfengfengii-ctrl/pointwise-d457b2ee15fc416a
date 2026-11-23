import sqlite3

from .ledger import SignedReport, load_signed_record


def get_report(conn: sqlite3.Connection, report_id: str) -> SignedReport | None:
    return load_signed_record(conn, report_id)
