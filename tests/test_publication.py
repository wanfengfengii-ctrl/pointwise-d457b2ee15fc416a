import sqlite3
from fractions import Fraction

from review import get_report, initialize_center, sign

from tests import ALIGNED, IDENTITY, OPPOSITE, WorkbenchTestCase


class PublicationTests(WorkbenchTestCase):
    def report_ledger(self, center):
        reports = center.execute('SELECT report_id FROM reports ORDER BY report_id').fetchall()
        receipts = center.execute('SELECT receipt_id, report_id FROM sign_receipts ORDER BY receipt_id').fetchall()
        return reports, receipts

    def test_missing_band(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, [('low', 1, 0)])
        ids = (left.receipt_id, right.receipt_id)
        with self.assertRaisesRegex(ValueError, "band 'high' is missing"):
            sign(center, ids, {'high': 1})
        self.assertEqual(self.report_ledger(center), ([], []))

    def test_zero_weight_missing(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, [('low', 1, 0)])
        ids = (left.receipt_id, right.receipt_id)
        with self.assertRaisesRegex(ValueError, "band 'high' is missing"):
            sign(center, ids, {'low': 1, 'high': 0})
        self.assertEqual(self.report_ledger(center), ([], []))

    def test_wrong_pair(self):
        center = self.center()
        station = self.station('A')
        original = self.issue_measurement(station, 'A', OPPOSITE)
        corrected = self.issue_measurement(station, 'A', ALIGNED, previous=original.source.revision_id)
        first = self.receive(center, original)
        second = self.receive(center, corrected)
        station.close()
        for ids in ((first.receipt_id, 'missing'), (first.receipt_id, second.receipt_id),
                    (first.receipt_id, first.receipt_id), (first.receipt_id,)):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                sign(center, ids, {'low': 1})
        self.assertEqual(self.report_ledger(center), ([], []))

    def test_invalid_weights(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, ALIGNED)
        ids = (left.receipt_id, right.receipt_id)
        for weights in ({'low': '3/0'}, {'low': False}, {'low': 0.25}, {'low': -1, 'high': 2},
                        {'low': 0, 'high': 0}, {}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                sign(center, ids, weights)
        self.assertEqual(self.report_ledger(center), ([], []))

    def old_report_and_artifact(self, center):
        left_db = self.station('A')
        right_db = self.station('B')
        original = self.issue_measurement(left_db, 'A', OPPOSITE)
        right = self.issue_measurement(right_db, 'B', ALIGNED, IDENTITY)
        first_receipt = self.receive(center, original)
        right_receipt = self.receive(center, right)
        left_db.close()
        right_db.close()
        result = sign(center, (first_receipt.receipt_id, right_receipt.receipt_id), {'low': 1, 'high': 1})
        self.assert_outcome(result, 'exact', Fraction(4))
        return result, original, right_receipt

    def receive_correction(self, center, original):
        left_db = self.station('A')
        corrected = self.issue_measurement(left_db, 'A', ALIGNED, previous=original.source.revision_id)
        receipt = self.receive(center, corrected)
        left_db.close()
        return corrected, receipt

    def test_atomic_failure(self):
        center = self.center()
        old, original, right_receipt = self.old_report_and_artifact(center)
        _, corrected_receipt = self.receive_correction(center, original)
        before = self.report_ledger(center)
        center.execute('''
            CREATE TEMP TRIGGER fail_sign_receipt BEFORE INSERT ON sign_receipts
            WHEN EXISTS (SELECT 1 FROM reports WHERE report_id = NEW.report_id)
            BEGIN
                SELECT RAISE(ABORT, 'receipt write rejected');
            END
        ''')
        new_ids = (corrected_receipt.receipt_id, right_receipt.receipt_id)
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'receipt write rejected'):
            sign(center, new_ids, {'low': 1, 'high': 1})
        self.assertFalse(center.in_transaction)
        self.assertEqual(self.report_ledger(center), before)
        center.close()
        center = self.center()
        self.assertEqual(self.report_ledger(center), before)
        self.assertEqual(get_report(center, old.report_id), old)
        new_report = sign(center, new_ids, {'low': 1, 'high': 1})
        self.assert_outcome(new_report, 'undetermined', None)
        self.assertEqual(get_report(center, new_report.report_id), new_report)

    def test_history_original(self):
        center = self.center()
        old, original, right_receipt = self.old_report_and_artifact(center)
        corrected, corrected_receipt = self.receive_correction(center, original)
        new_ids = (right_receipt.receipt_id, corrected_receipt.receipt_id)
        new_report = sign(center, new_ids, {'high': 1, 'low': 1})
        self.assert_outcome(new_report, 'undetermined', None)
        self.assertNotEqual(new_report.report_id, old.report_id)
        self.assertEqual(new_report.request.receipt_ids, new_ids)
        self.assertEqual(new_report.parents[1].source, corrected.source)
        initialize_center(center)
        center.close()
        center = self.center()

        def allow_report_reads(action, table, column, database, trigger):
            if action == sqlite3.SQLITE_READ and table in {'received_artifacts', 'receipts'}:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        center.set_authorizer(allow_report_reads)
        old_readback = get_report(center, old.report_id)
        self.assertEqual(old_readback, old)
        self.assertEqual(old_readback.parents[0].source, original.source)
        self.assertEqual(old_readback.request.weights, (('low', Fraction(1)), ('high', Fraction(1))))
        self.assertEqual(get_report(center, new_report.report_id), new_report)
        self.assertIsNone(get_report(center, 'missing'))
