import json
from dataclasses import dataclass

from measurements.bands import require_name

from .identity import SourceBinding


@dataclass(frozen=True)
class ExchangeEnvelope:
    artifact_id: str
    source: SourceBinding
    body: dict


def pack_exchange(envelope: ExchangeEnvelope) -> str:
    return json.dumps({
        'version': 1,
        'artifact_id': envelope.artifact_id,
        'source': envelope.source.as_dict(),
        'body': envelope.body,
    }, separators=(',', ':'), ensure_ascii=True)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate exchange member {key!r}')
        result[key] = value
    return result


def unpack_exchange(exchange: str) -> ExchangeEnvelope:
    if not isinstance(exchange, str):
        raise ValueError('exchange must be JSON text')
    try:
        exchange.encode('utf-8')
        data = json.loads(exchange, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid exchange JSON') from exc
    if not isinstance(data, dict) or data.keys() != {'version', 'artifact_id', 'source', 'body'}:
        raise ValueError('invalid exchange fields')
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('unsupported exchange version')
    artifact_id = data['artifact_id']
    if (not isinstance(artifact_id, str) or len(artifact_id) != 64
            or any(char not in '0123456789abcdef' for char in artifact_id)):
        raise ValueError('invalid artifact identity')
    source = data['source']
    if not isinstance(source, dict) or source.keys() != {'station', 'revision_id', 'analysis_id'}:
        raise ValueError('invalid source binding')
    source_binding = SourceBinding(**{field: require_name(value, field) for field, value in source.items()})
    if not isinstance(data['body'], dict):
        raise ValueError('exchange body must be an object')
    return ExchangeEnvelope(artifact_id, source_binding, data['body'])
