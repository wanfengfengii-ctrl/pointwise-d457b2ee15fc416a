from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from measurements.revisions import Revision

from .quadratures import RationalComplex


class ReferenceQualification(str, Enum):
    ANCHORED = 'anchored'
    UNANCHORED = 'unanchored'


@dataclass(frozen=True)
class ReferenceRecord:
    revision_id: str
    factor: tuple[Fraction | int | str, Fraction | int | str] | None


def qualify_reference(
    revision: Revision, reference: ReferenceRecord | None
) -> tuple[ReferenceQualification, RationalComplex | None]:
    if reference is None:
        return ReferenceQualification.UNANCHORED, None
    if not isinstance(reference, ReferenceRecord):
        raise ValueError('reference must be a ReferenceRecord')
    if reference.revision_id != revision.revision_id:
        raise ValueError('reference belongs to a different revision')
    if reference.factor is None:
        return ReferenceQualification.UNANCHORED, None
    if not isinstance(reference.factor, (tuple, list)) or len(reference.factor) != 2:
        raise ValueError('reference factor requires real and imaginary components')
    correction = RationalComplex(*reference.factor)
    if correction.norm_squared() != 1:
        raise ValueError('reference factor must have unit modulus')
    return ReferenceQualification.ANCHORED, correction
