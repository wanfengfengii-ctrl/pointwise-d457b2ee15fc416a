from fractions import Fraction

from calibration import ReferenceQualification, ReferenceRecord, freeze, get_fixed_analysis
from calibration.quadratures import RationalComplex
from measurements import get_revision, read_revision_lineage, record
from phase_evidence import get_issued_artifact, initialize_station, issue

from tests import IDENTITY, RUN, WorkbenchTestCase


class MeasurementTests(WorkbenchTestCase):
    def test_freeze(self):
        db = self.station('A')
        revision_id = record(db, 'A', RUN, [('low', 1, 0), ('high', 0, 1)])
        revision = get_revision(db, revision_id)
        self.assertEqual(revision.catalog.names, ('low', 'high'))
        self.assertEqual([(r.in_phase, r.quadrature) for r in revision.readings], [(1, 0), (0, 1)])
        fixed = freeze(db, revision_id, ReferenceRecord(revision_id, IDENTITY))
        self.assertEqual(fixed.inspection.responses, (
            ('low', RationalComplex(1, 0)), ('high', RationalComplex(0, 1)),
        ))
        self.assertEqual(fixed.inspection.energy, Fraction(2))
        self.assertEqual(fixed.revision_id, revision_id)
        self.assertEqual(get_fixed_analysis(db, fixed.analysis_id), fixed)

    def test_reference_rotation(self):
        db = self.station('A')
        revision_id = record(db, 'A', RUN, [('low', 1, 0), ('high', 0, 1)])
        fixed = freeze(db, revision_id, ReferenceRecord(revision_id, (0, 1)))
        self.assertIs(fixed.inspection.qualification, ReferenceQualification.ANCHORED)
        self.assertEqual(fixed.inspection.responses, (
            ('low', RationalComplex(0, 1)), ('high', RationalComplex(-1, 0)),
        ))
        self.assertEqual(fixed.inspection.energy, Fraction(2))
        self.assertEqual(get_fixed_analysis(db, fixed.analysis_id).reference, ReferenceRecord(revision_id, (0, 1)))

    def test_reference_absence(self):
        db = self.station('A')
        revision_id = record(db, 'A', RUN, [('low', 1, 0), ('high', 0, 1)])
        legal = (None, ReferenceRecord(revision_id, None))
        for candidate in legal:
            with self.subTest(candidate=candidate):
                fixed = freeze(db, revision_id, candidate)
                self.assertIs(fixed.inspection.qualification, ReferenceQualification.UNANCHORED)
                self.assertEqual(fixed.inspection.energy, Fraction(2))
                self.assertEqual(fixed.inspection.responses, (
                    ('low', RationalComplex(1, 0)), ('high', RationalComplex(0, 1)),
                ))
                self.assertEqual(get_fixed_analysis(db, fixed.analysis_id).reference, candidate)
        self.assertIs(freeze(db, revision_id, ReferenceRecord(revision_id, IDENTITY)).inspection.qualification,
                      ReferenceQualification.ANCHORED)
        wrong_revision = record(db, 'A', RUN, [('low', 1, 0)], revision_id)
        for invalid in (ReferenceRecord(wrong_revision, None), ReferenceRecord(revision_id, (2, 0)),
                        ReferenceRecord(revision_id, (1,)), ReferenceRecord(revision_id, ('x', 0)),
                        {'revision_id': revision_id, 'factor': (1, 0)}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                freeze(db, revision_id, invalid)
        with self.assertRaisesRegex(ValueError, 'unknown revision'):
            freeze(db, 'absent')
        self.assertEqual(db.execute('SELECT count(*) FROM fixed_analyses').fetchone()[0], 3)

    def test_pinned_revision(self):
        db = self.station('A')
        original = record(db, 'A', RUN, [('low', 1, 0), ('high', 0, 1)])
        corrected = record(db, 'A', RUN, [('low', 2, 0), ('high', 0, 1)], original)
        old_analysis = freeze(db, original)
        new_analysis = freeze(db, corrected)
        self.assertEqual((old_analysis.revision_id, old_analysis.inspection.energy), (original, Fraction(2)))
        self.assertEqual((new_analysis.revision_id, new_analysis.inspection.energy), (corrected, Fraction(5)))
        self.assertEqual(get_revision(db, corrected).previous_revision_id, original)

    def test_repeat_initialization(self):
        db = self.station('A')
        original = record(db, 'A', RUN, [('low', '1/2', 0)])
        corrected = record(db, 'A', RUN, [('low', '3/2', 0)], original)
        measured = freeze(db, original)
        artifact = issue(db, measured.analysis_id)
        initialize_station(db)
        db.close()
        reopened = self.station('A')
        chain = read_revision_lineage(reopened, corrected)
        self.assertEqual(tuple(row.revision_id for row in chain), (corrected, original))
        self.assertEqual(tuple(row.readings[0].in_phase for row in chain), (Fraction(3, 2), Fraction(1, 2)))
        self.assertEqual(get_fixed_analysis(reopened, measured.analysis_id), measured)
        self.assertEqual(get_issued_artifact(reopened, artifact.artifact_id), artifact)
        self.assertEqual(read_revision_lineage(reopened, 'absent'), ())

    def test_duplicate_bands(self):
        db = self.station('A')
        with self.assertRaisesRegex(ValueError, 'duplicate band'):
            record(db, 'A', RUN, [('low', 1, 0), ('low', 2, 0)])
        self.assertEqual(db.execute('SELECT count(*) FROM revisions').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT count(*) FROM fixed_analyses').fetchone()[0], 0)

    def test_invalid_predecessor(self):
        db = self.station('A')
        other_station = record(db, 'B', RUN, [('low', 1, 0)])
        other_run = record(db, 'A', 'other-run', [('low', 1, 0)])
        for predecessor in (other_station, other_run, 'missing'):
            with self.subTest(predecessor=predecessor), self.assertRaises(ValueError):
                record(db, 'A', RUN, [('low', 1, 0)], predecessor)
        revisions = db.execute('SELECT revision_id, previous_revision_id FROM revisions').fetchall()
        self.assertCountEqual(revisions, [(other_station, None), (other_run, None)])

    def test_invalid_reading(self):
        db = self.station('A')
        for invalid in ('1/0', 'not-a-number', 0.5, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                record(db, 'A', RUN, [('low', 1, 0), ('high', 0, invalid)])
        self.assertEqual(db.execute('SELECT count(*) FROM revisions').fetchone()[0], 0)
