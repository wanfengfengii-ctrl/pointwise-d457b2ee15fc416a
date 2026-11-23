from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from .bands import BandCatalog, build_band_catalog, require_name


@dataclass(frozen=True)
class QuadratureReading:
    band: str
    in_phase: Fraction
    quadrature: Fraction


def parse_rational(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f'invalid rational number {value!r}') from exc
    raise ValueError('a rational number requires an integer, Fraction, or text')


def parse_readings(rows: object) -> tuple[BandCatalog, tuple[QuadratureReading, ...]]:
    if isinstance(rows, (str, bytes, Mapping)):
        raise ValueError('readings require ordered band, I, Q records')
    try:
        iterator = iter(rows)
    except TypeError as exc:
        raise ValueError('readings require ordered band, I, Q records') from exc

    readings = []
    for row in iterator:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError('each reading requires band, I, and Q')
        band, in_phase, quadrature = row
        readings.append(QuadratureReading(
            require_name(band, 'band'), parse_rational(in_phase), parse_rational(quadrature)
        ))
    catalog = build_band_catalog(reading.band for reading in readings)
    return catalog, tuple(readings)
