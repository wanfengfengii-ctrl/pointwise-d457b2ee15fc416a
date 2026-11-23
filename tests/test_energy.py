from dataclasses import replace
from fractions import Fraction

from phase_evidence.export import pack_exchange, unpack_exchange
from receiving import accept, lookup_received
from review import get_report, sign

from tests import ALIGNED, IDENTITY, OPPOSITE, WorkbenchTestCase


class EnergyTests(WorkbenchTestCase):
    def test_order_and_identity(self):
        center = self.center()
        left_db = self.station('A')
        right_db = self.station('B')
        left = self.issue_measurement(left_db, 'A', [('low', 1, 0), ('high', 0, 1)], IDENTITY)
        right = self.issue_measurement(right_db, 'B', [('low', 1, 0), ('high', 0, -1)], IDENTITY)
        envelope = unpack_exchange(right.exchange)
        reversed_body = dict(envelope.body)
        reversed_body['bands'] = list(reversed(reversed_body['bands']))
        reversed_text = pack_exchange(replace(envelope, body=reversed_body))
        self.assertNotEqual(reversed_text, right.exchange)
        left_receipt = self.receive(center, left)
        right_receipt = accept(center, reversed_text, right.artifact_id)
        self.assertEqual(self.receive(center, right), right_receipt)
        left_db.close()
        right_db.close()
        self.assertEqual(lookup_received(center, right_receipt.receipt_id).delivery.exchange, reversed_text)
        weights = {'high': 1, 'low': 1}
        forward_ids = (left_receipt.receipt_id, right_receipt.receipt_id)
        reversed_ids = tuple(reversed(forward_ids))
        for ids, artifacts in ((forward_ids, (left, right)), (reversed_ids, (right, left))):
            with self.subTest(ids=ids):
                report = sign(center, ids, weights)
                self.assert_outcome(report, 'exact', Fraction(4))
                self.assertEqual(report.request.receipt_ids, ids)
                self.assertEqual(report.request.weights, (('high', Fraction(1)), ('low', Fraction(1))))
                self.assertEqual(tuple(parent.artifact_id for parent in report.parents),
                                 tuple(artifact.artifact_id for artifact in artifacts))
                self.assertEqual(tuple(parent.source for parent in report.parents),
                                 tuple(artifact.source for artifact in artifacts))
                self.assertEqual(get_report(center, report.report_id), report)

    def test_exact_fraction(self):
        center = self.center()
        rows = [('low', '1/2', 0)]
        left, right = self.offline_pair(center, rows, rows, IDENTITY)
        report = sign(center, (left.receipt_id, right.receipt_id), {'low': '1/3'})
        self.assert_outcome(report, 'exact', Fraction(1, 3))
        self.assertIsInstance(report.outcome.energy, Fraction)
        self.assertEqual(get_report(center, report.report_id), report)

    def test_determined_zero(self):
        center = self.center()
        left, right = self.offline_pair(center, ALIGNED, [('low', -1, 0), ('high', -1, 0)], IDENTITY)
        report = sign(center, (left.receipt_id, right.receipt_id), {'low': 1, 'high': 1})
        self.assert_outcome(report, 'exact', Fraction(0))
        self.assertIsInstance(report.outcome.energy, Fraction)
        self.assertEqual(get_report(center, report.report_id), report)

    def test_offline_total_and_single_band(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, ALIGNED)
        ids = (left.receipt_id, right.receipt_id)
        report = sign(center, ids, {'low': 1, 'high': 1})
        self.assert_outcome(report, 'exact', Fraction(4), 'V6_OFFLINE_TOTAL')
        self.assert_outcome(sign(center, ids, {'low': 1}), 'undetermined', None)
        self.assertEqual(get_report(center, report.report_id), report)

    def test_same_magnitude(self):
        center = self.center()
        left_db = self.station('A')
        right_db = self.station('B')
        original = self.issue_measurement(left_db, 'A', OPPOSITE)
        corrected = self.issue_measurement(left_db, 'A', ALIGNED, previous=original.source.revision_id)
        right = self.issue_measurement(right_db, 'B', ALIGNED, IDENTITY)
        receipts = [self.receive(center, item) for item in (original, corrected, right)]
        left_db.close()
        right_db.close()
        weights = {'low': 1, 'high': 1}
        old_report = sign(center, (receipts[0].receipt_id, receipts[2].receipt_id), weights)
        new_report = sign(center, (receipts[1].receipt_id, receipts[2].receipt_id), weights)
        self.assert_outcome(old_report, 'exact', Fraction(4))
        self.assert_outcome(new_report, 'undetermined', None)

    def test_both_unanchored(self):
        center = self.center()
        for left_rows in (OPPOSITE, [('low', 0, 1), ('high', 0, -1)]):
            with self.subTest(left_rows=left_rows):
                left, right = self.offline_pair(center, left_rows, ALIGNED, right_factor=None)
                report = sign(center, (left.receipt_id, right.receipt_id), {'low': 1, 'high': 1})
                self.assert_outcome(report, 'exact', Fraction(4))

    def test_imaginary_cross_term(self):
        center = self.center()
        left, right = self.offline_pair(center, [('low', 0, 1), ('high', 0, 1)], ALIGNED)
        report = sign(center, (left.receipt_id, right.receipt_id), {'low': 1, 'high': 1})
        self.assert_outcome(report, 'undetermined', None)

    def test_unequal_weights(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, ALIGNED)
        report = sign(center, (left.receipt_id, right.receipt_id), {'low': 1, 'high': 2})
        self.assert_outcome(report, 'undetermined', None)
