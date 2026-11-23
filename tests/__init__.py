import sqlite3
import tempfile
import unittest
from pathlib import Path

from calibration import ReferenceRecord, freeze
from measurements import record
from phase_evidence import initialize_station, issue
from receiving import accept
from review import initialize_center


OPPOSITE = (('low', 1, 0), ('high', -1, 0))
ALIGNED = (('low', 1, 0), ('high', 1, 0))
IDENTITY = (1, 0)
RUN = 'pump-17'


class WorkbenchTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)

    def _open_database(self, name, initialize):
        conn = sqlite3.connect(self.folder / (name + '.sqlite3'))
        self.addCleanup(conn.close)
        initialize(conn)
        return conn

    def station(self, station):
        return self._open_database('station-' + station, initialize_station)

    def center(self):
        return self._open_database('center', initialize_center)

    def issue_measurement(self, conn, station, rows, factor=None, previous=None):
        revision_id = record(conn, station, RUN, rows, previous)
        reference = None if factor is None else ReferenceRecord(revision_id, factor)
        analysis = freeze(conn, revision_id, reference)
        return issue(conn, analysis.analysis_id)

    def receive(self, center, artifact):
        return accept(center, artifact.exchange, artifact.artifact_id)

    def offline_pair(self, center, left_rows, right_rows, left_factor=None, right_factor=IDENTITY):
        left_db = self.station('A')
        right_db = self.station('B')
        left = self.issue_measurement(left_db, 'A', left_rows, left_factor)
        right = self.issue_measurement(right_db, 'B', right_rows, right_factor)
        left_receipt = self.receive(center, left)
        right_receipt = self.receive(center, right)
        left_db.close()
        right_db.close()
        return left_receipt, right_receipt

    def assert_outcome(self, report, status, energy, message=None):
        self.assertEqual((report.outcome.status, report.outcome.energy), (status, energy), message)
        self.assertEqual(report.receipt.report_id, report.report_id)
