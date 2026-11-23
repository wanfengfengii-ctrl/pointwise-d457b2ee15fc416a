import json
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from measurements.readings import parse_rational
from measurements.revisions import Revision

from .inspection import InspectionResult
from .quadratures import RationalComplex
from .references import ReferenceQualification, ReferenceRecord


@dataclass(frozen=True)
class FixedAnalysis:
    analysis_id: str
    station: str
    revision_id: str
    reference: ReferenceRecord | None
    inspection: InspectionResult


def initialize_analysis_store(conn: sqlite3.Connection) -> None:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fixed_analyses (
            analysis_id TEXT PRIMARY KEY NOT NULL,
            station TEXT NOT NULL,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            reference_record TEXT,
            qualification TEXT NOT NULL CHECK (qualification IN ('anchored', 'unanchored')),
            responses TEXT NOT NULL,
            energy TEXT NOT NULL
        )
    ''')


def save_fixed_analysis(
    conn: sqlite3.Connection,
    revision: Revision,
    reference: ReferenceRecord | None,
    inspection: InspectionResult,
) -> FixedAnalysis:
    analysis = FixedAnalysis(uuid4().hex, revision.station, revision.revision_id, reference, inspection)
    reference_payload = None
    if reference is not None:
        factor = None if reference.factor is None else [str(part) for part in reference.factor]
        reference_payload = json.dumps({'revision_id': reference.revision_id, 'factor': factor})
    responses = [[band, str(value.real), str(value.imag)] for band, value in inspection.responses]
    conn.execute('''
        INSERT INTO fixed_analyses (
            analysis_id, station, revision_id, reference_record, qualification, responses, energy
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        analysis.analysis_id, analysis.station, analysis.revision_id, reference_payload,
        inspection.qualification.value, json.dumps(responses), str(inspection.energy),
    ))
    return analysis


def get_fixed_analysis(conn: sqlite3.Connection, analysis_id: str) -> FixedAnalysis | None:
    row = conn.execute('''
        SELECT analysis_id, station, revision_id, reference_record, qualification, responses, energy
        FROM fixed_analyses WHERE analysis_id = ?
    ''', (analysis_id,)).fetchone()
    if row is None:
        return None
    stored_id, station, revision_id, reference_payload, qualification, responses, energy = row
    reference = None
    if reference_payload is not None:
        reference_data = json.loads(reference_payload)
        factor = reference_data['factor']
        components = None if factor is None else (parse_rational(factor[0]), parse_rational(factor[1]))
        reference = ReferenceRecord(reference_data['revision_id'], components)
    inspection = InspectionResult(
        ReferenceQualification(qualification),
        tuple((band, RationalComplex(real, imag)) for band, real, imag in json.loads(responses)),
        parse_rational(energy),
    )
    return FixedAnalysis(stored_id, station, revision_id, reference, inspection)
