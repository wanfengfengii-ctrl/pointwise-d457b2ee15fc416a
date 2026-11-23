from dataclasses import dataclass

from calibration.quadratures import RationalComplex
from calibration.references import ReferenceQualification
from calibration.snapshots import FixedAnalysis
from measurements.readings import parse_readings


@dataclass(frozen=True)
class PhaseEvidence:
    anchored: bool
    responses: tuple[tuple[str, RationalComplex], ...]


def build_evidence(analysis: FixedAnalysis) -> PhaseEvidence:
    inspection = analysis.inspection
    return PhaseEvidence(
        inspection.qualification is ReferenceQualification.ANCHORED,
        inspection.responses,
    )


def encode_evidence(evidence: PhaseEvidence) -> dict:
    return {
        'anchored': evidence.anchored,
        'bands': [[name, str(value.real), str(value.imag)] for name, value in evidence.responses],
    }


def decode_evidence(body: object) -> PhaseEvidence:
    if not isinstance(body, dict) or body.keys() != {'anchored', 'bands'}:
        raise ValueError('invalid phase evidence fields')
    if type(body['anchored']) is not bool:
        raise ValueError('phase evidence requires a boolean reference qualification')
    bands = body['bands']
    if not isinstance(bands, list):
        raise ValueError('phase evidence bands must be a list')
    for row in bands:
        if not isinstance(row, list) or len(row) != 3 or not all(isinstance(part, str) for part in row):
            raise ValueError('phase evidence requires band, real text, and imaginary text')
    _, readings = parse_readings(bands)
    return PhaseEvidence(
        body['anchored'],
        tuple((reading.band, RationalComplex(reading.in_phase, reading.quadrature))
              for reading in readings),
    )
