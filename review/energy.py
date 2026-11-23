from dataclasses import dataclass
from fractions import Fraction

from calibration.quadratures import RationalComplex

from .request import ValidatedRequest


@dataclass(frozen=True)
class EnergyOutcome:
    status: str
    energy: Fraction | None


def determine_energy(validated: ValidatedRequest) -> EnergyOutcome:
    left = validated.pair.left.evidence
    right = validated.pair.right.evidence
    left_values = dict(left.responses)
    right_values = dict(right.responses)
    base = Fraction(0)
    cross = RationalComplex()
    for band, weight in validated.request.weights:
        a = left_values[band]
        b = right_values[band]
        base += weight * (a.norm_squared() + b.norm_squared())
        cross += RationalComplex(weight) * a * b.conjugate()

    # A single relative phase multiplies the entire sum of cross terms.
    # It is 1 for two anchored pieces and can be any unit phase otherwise.
    if left.anchored and right.anchored:
        return EnergyOutcome('exact', base + 2 * cross.real)
    if cross.real == 0 and cross.imag == 0:
        return EnergyOutcome('exact', base)
    return EnergyOutcome('undetermined', None)
