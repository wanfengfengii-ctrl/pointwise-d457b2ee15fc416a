import sqlite3

from .bands import require_name
from .revisions import Revision, get_revision


def require_predecessor(
    conn: sqlite3.Connection, station: str, run: str, previous_revision_id: str | None
) -> None:
    if previous_revision_id is None:
        return
    require_name(previous_revision_id, 'previous revision id')
    predecessor = get_revision(conn, previous_revision_id)
    if predecessor is None:
        raise ValueError(f'unknown predecessor {previous_revision_id!r}')
    if (predecessor.station, predecessor.run) != (station, run):
        raise ValueError('predecessor must belong to the same station and run')


def read_revision_lineage(conn: sqlite3.Connection, revision_id: str) -> tuple[Revision, ...]:
    revision = get_revision(conn, revision_id)
    if revision is None:
        return ()
    chain = [revision]
    seen = {revision.revision_id}
    while revision.previous_revision_id is not None:
        previous_id = revision.previous_revision_id
        if previous_id in seen:
            raise sqlite3.IntegrityError('revision lineage contains a cycle')
        revision = get_revision(conn, previous_id)
        if revision is None:
            raise sqlite3.IntegrityError('revision lineage is missing a predecessor')
        seen.add(revision.revision_id)
        chain.append(revision)
    return tuple(chain)
