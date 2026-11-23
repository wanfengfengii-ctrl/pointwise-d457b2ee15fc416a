import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceBinding:
    station: str
    revision_id: str
    analysis_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            'station': self.station,
            'revision_id': self.revision_id,
            'analysis_id': self.analysis_id,
        }


def artifact_identity(source: SourceBinding, body: dict) -> str:
    """Hash the source and the semantically encoded evidence body."""
    canonical_body = dict(body)
    canonical_body['bands'] = sorted(body['bands'], key=lambda band: band[0])
    identity_data = {'version': 1, 'source': source.as_dict(), 'body': canonical_body}
    payload = json.dumps(identity_data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode('ascii')).hexdigest()
