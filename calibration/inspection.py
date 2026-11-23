from dataclasses import dataclass
from fractions import Fraction

from measurements.revisions import Revision

from .quadratures import RationalComplex, responses_from_readings
from .references import ReferenceQualification


@dataclass(frozen=True)
class InspectionResult:
    qualification: ReferenceQualification
    responses: tuple[tuple[str, RationalComplex], ...]
    energy: Fraction


def inspect_revision(
    revision: Revision,
    qualification: ReferenceQualification,
    correction: RationalComplex | None,
) -> InspectionResult:
    responses = responses_from_readings(revision.readings, correction)
    energy = sum((value.norm_squared() for _, value in responses), Fraction(0))
    return InspectionResult(qualification, responses, energy)
