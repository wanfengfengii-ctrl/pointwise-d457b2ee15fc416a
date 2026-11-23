import sqlite3
from collections.abc import Mapping

from .energy import determine_energy
from .ledger import SignedReport, commit_report
from .request import validate_request


def sign(
    conn: sqlite3.Connection, receipt_ids: tuple[str, str] | list[str], weights: Mapping[str, object]
) -> SignedReport:
    validated = validate_request(conn, receipt_ids, weights)
    outcome = determine_energy(validated)
    return commit_report(conn, validated, outcome)
