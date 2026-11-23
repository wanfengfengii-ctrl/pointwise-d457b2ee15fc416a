import sqlite3

from receiving.admit import initialize_receiving

from .history import get_report as get_report
from .ledger import SignReceipt as SignReceipt
from .ledger import SignedReport as SignedReport
from .ledger import initialize_report_store
from .publish import sign as sign


def initialize_center(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        raise ValueError('center initialization requires an idle connection')
    conn.execute('PRAGMA foreign_keys = ON')
    initialize_receiving(conn)
    initialize_report_store(conn)
