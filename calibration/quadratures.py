from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from measurements.readings import QuadratureReading, parse_rational


@dataclass(frozen=True)
class RationalComplex:
    real: Fraction = Fraction(0)
    imag: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'real', parse_rational(self.real))
        object.__setattr__(self, 'imag', parse_rational(self.imag))

    def __add__(self, other: 'RationalComplex') -> 'RationalComplex':
        return RationalComplex(self.real + other.real, self.imag + other.imag)

    def __mul__(self, other: 'RationalComplex') -> 'RationalComplex':
        return RationalComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def conjugate(self) -> 'RationalComplex':
        return RationalComplex(self.real, -self.imag)

    def norm_squared(self) -> Fraction:
        return self.real ** 2 + self.imag ** 2


def responses_from_readings(
    readings: Iterable[QuadratureReading], correction: RationalComplex | None
) -> tuple[tuple[str, RationalComplex], ...]:
    responses = []
    for reading in readings:
        response = RationalComplex(reading.in_phase, reading.quadrature)
        if correction is not None:
            response = response * correction
        responses.append((reading.band, response))
    return tuple(responses)
