import json
import sqlite3
from contextlib import closing
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

from calibration import ReferenceRecord, freeze
from measurements import record
from phase_evidence import initialize_station, issue
from receiving import accept, collect_pair
from review import get_report, initialize_center, sign


SAMPLE = {
    'run': 'pump-17',
    'A': {'readings': [('low', 1, 0), ('high', -1, 0)], 'factor': None},
    'B': {'readings': [('high', 1, 0), ('low', 1, 0)], 'factor': (1, 0)},
    'correction': [('low', 1, 0), ('high', 1, 0)],
    'weights': {'low': 1, 'high': 1},
}


def issue_sample(path, station, readings, factor=None, previous=None):
    with closing(sqlite3.connect(path)) as db:
        initialize_station(db)
        revision_id = record(db, station, SAMPLE['run'], readings, previous)
        reference = None if factor is None else ReferenceRecord(revision_id, factor)
        analysis = freeze(db, revision_id, reference)
        return issue(db, analysis.analysis_id)


def outcome_json(report):
    energy = report.outcome.energy
    return {'status': report.outcome.status, 'energy': None if energy is None else str(energy)}


def main():
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        left_path, right_path, center_path = (folder / name for name in ('left.db', 'right.db', 'center.db'))
        with closing(sqlite3.connect(center_path)) as center:
            initialize_center(center)
            alpha = issue_sample(left_path, 'A', **SAMPLE['A'])
            beta = issue_sample(right_path, 'B', **SAMPLE['B'])
            left = accept(center, alpha.exchange, alpha.artifact_id)
            right = accept(center, beta.exchange, beta.artifact_id)
            ids = (left.receipt_id, right.receipt_id)
            pair = collect_pair(center, ids)
            both = sign(center, ids, SAMPLE['weights'])
            single = sign(center, ids, {'low': 1})
            assert (both.outcome.status, both.outcome.energy) == ('exact', Fraction(4))
            assert (single.outcome.status, single.outcome.energy) == ('undetermined', None)
            assert (pair.left.source.station, pair.right.source.station) == ('A', 'B')
            corrected = issue_sample(left_path, 'A', SAMPLE['correction'], previous=alpha.source.revision_id)
            replacement = accept(center, corrected.exchange, corrected.artifact_id)
            updated = sign(center, (replacement.receipt_id, right.receipt_id), SAMPLE['weights'])
            assert (updated.outcome.status, updated.outcome.energy) == ('undetermined', None)

        with closing(sqlite3.connect(center_path)) as center:
            initialize_center(center)
            readback = get_report(center, both.report_id)
            new_readback = get_report(center, updated.report_id)
            assert readback == both
            assert new_readback == updated
            assert readback.parents[0].artifact_id == alpha.artifact_id
            assert new_readback.parents[0].artifact_id == corrected.artifact_id
            assert readback.receipt.report_id == readback.report_id

        cases = [
            {
                'case_id': 'v6',
                'input': {'A': SAMPLE['A'], 'B': SAMPLE['B'], 'double_weights': SAMPLE['weights'], 'single_weights': {'low': 1}},
                'expected': {'double': {'status': 'exact', 'energy': '4'}, 'single': {'status': 'undetermined', 'energy': None}},
                'actual': {'double': outcome_json(both), 'single': outcome_json(single)},
                'downstream_expected': {'reopened_energy': '4', 'receipt_links_to_report': True},
                'downstream_actual': {'reopened_energy': str(readback.outcome.energy), 'receipt_links_to_report': readback.receipt.report_id == readback.report_id},
                'code_paths': ['phase_evidence/issue.py', 'receiving/admit.py', 'review/energy.py', 'review/history.py'],
                'oracle': '双带分别为 2+2Reρ 与 2−2Reρ，合计恒为 4。单带在 ρ=1 与 ρ=−1 时分别为 4 与 0。',
            },
            {
                'case_id': 'v8.history_original',
                'input': {'original_A': SAMPLE['A']['readings'], 'corrected_A': SAMPLE['correction'], 'B': SAMPLE['B'], 'weights': SAMPLE['weights']},
                'expected': {'old_energy': '4', 'new_status': 'undetermined', 'new_energy': None},
                'actual': {'old_energy': str(readback.outcome.energy), 'new_status': new_readback.outcome.status, 'new_energy': outcome_json(new_readback)['energy']},
                'downstream_expected': {'old_parents_and_receipt_preserved': True, 'new_parent_is_correction': True},
                'downstream_actual': {'old_parents_and_receipt_preserved': readback.parents == both.parents and readback.receipt == both.receipt, 'new_parent_is_correction': new_readback.parents[0].artifact_id == corrected.artifact_id},
                'code_paths': ['measurements/intake.py', 'review/energy.py', 'review/ledger.py', 'review/history.py'],
                'oracle': '原双带交叉项相消。勘误后两带同相，双带在相对相位为 1 与 −1 时分别为 8 与 0。',
            },
        ]
        for case in cases:
            print('POINTWISE_SCENARIO ' + json.dumps(case, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
