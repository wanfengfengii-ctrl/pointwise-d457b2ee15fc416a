from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class BandCatalog:
    names: tuple[str, ...]


def require_name(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be nonblank text')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise ValueError(f'{field} must be valid Unicode text') from exc
    return value


def build_band_catalog(names: Iterable[str]) -> BandCatalog:
    if isinstance(names, (str, bytes)):
        raise ValueError('band catalog requires a sequence of names')
    ordered = []
    seen = set()
    for value in names:
        name = require_name(value, 'band')
        if name in seen:
            raise ValueError(f'duplicate band {name!r}')
        seen.add(name)
        ordered.append(name)
    if not ordered:
        raise ValueError('a measurement must contain at least one band')
    return BandCatalog(tuple(ordered))
