from dataclasses import replace

from calibration.quadratures import RationalComplex
from phase_evidence import get_issued_artifact, issue
from phase_evidence.export import pack_exchange, unpack_exchange
from receiving import accept, collect_pair, lookup_received

from tests import ALIGNED, OPPOSITE, WorkbenchTestCase


class HandoffTests(WorkbenchTestCase):
    def test_phase_preservation(self):
        station = self.station('A')
        center = self.center()
        original = self.issue_measurement(station, 'A', OPPOSITE)
        corrected = self.issue_measurement(station, 'A', ALIGNED, previous=original.source.revision_id)
        self.assertEqual(get_issued_artifact(station, original.artifact_id), original)
        self.assertEqual(issue(station, original.source.analysis_id), original)
        first = self.receive(center, original)
        second = self.receive(center, corrected)
        station.close()
        self.assertEqual(self.receive(center, original), first)
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        old_item = lookup_received(center, first.receipt_id)
        new_item = lookup_received(center, second.receipt_id)
        self.assertFalse(old_item.evidence.anchored)
        self.assertFalse(new_item.evidence.anchored)
        old_values = dict(old_item.evidence.responses)
        new_values = dict(new_item.evidence.responses)
        self.assertEqual(old_values['low'] * old_values['high'].conjugate(), RationalComplex(-1))
        self.assertEqual(new_values['low'] * new_values['high'].conjugate(), RationalComplex(1))

    def test_lookup_original(self):
        station = self.station('A')
        center = self.center()
        original = self.issue_measurement(station, 'A', OPPOSITE)
        corrected = self.issue_measurement(station, 'A', ALIGNED, previous=original.source.revision_id)
        deliveries = [(item, self.receive(center, item)) for item in (original, corrected)]
        station.close()
        center.close()
        center = self.center()
        for artifact, receipt in deliveries:
            item = lookup_received(center, receipt.receipt_id)
            self.assertEqual(item.receipt, receipt)
            self.assertEqual(item.source, artifact.source)
            self.assertEqual(item.delivery.exchange, artifact.exchange)
            self.assertEqual(item.delivery.envelope.artifact_id, artifact.artifact_id)
        self.assertIsNone(lookup_received(center, 'missing'))

    def test_offline_pair(self):
        center = self.center()
        left, right = self.offline_pair(center, OPPOSITE, ALIGNED)
        pair = collect_pair(center, (right.receipt_id, left.receipt_id))
        self.assertEqual((pair.left.source.station, pair.right.source.station), ('B', 'A'))
        self.assertEqual((pair.left.receipt, pair.right.receipt), (right, left))
        self.assertTrue(pair.left.evidence.anchored)
        self.assertFalse(pair.right.evidence.anchored)

    def test_wrong_identity(self):
        station = self.station('A')
        center = self.center()
        first = self.issue_measurement(station, 'A', OPPOSITE)
        second = self.issue_measurement(station, 'A', ALIGNED)
        receipt = self.receive(center, first)
        first_envelope = unpack_exchange(first.exchange)
        second_envelope = unpack_exchange(second.exchange)
        with self.assertRaisesRegex(ValueError, 'declared identity'):
            accept(center, first.exchange, second.artifact_id)
        with self.assertRaisesRegex(ValueError, 'source and evidence'):
            accept(center, pack_exchange(replace(first_envelope, body=second_envelope.body)), first.artifact_id)
        with self.assertRaisesRegex(ValueError, 'source and evidence'):
            accept(center, pack_exchange(replace(first_envelope, source=second_envelope.source)), first.artifact_id)
        self.assertEqual(center.execute('SELECT artifact_id FROM received_artifacts').fetchall(), [(first.artifact_id,)])
        self.assertEqual(center.execute('SELECT receipt_id FROM receipts').fetchall(), [(receipt.receipt_id,)])
        self.assertEqual(lookup_received(center, receipt.receipt_id).delivery.exchange, first.exchange)
        with self.assertRaisesRegex(ValueError, 'unknown fixed analysis'):
            issue(station, 'missing')
        self.assertEqual(station.execute('SELECT count(*) FROM issued_artifacts').fetchone()[0], 2)
