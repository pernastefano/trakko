from collections.abc import Sequence
from typing import Protocol

from app.errors import InvalidError


class Positioned(Protocol):
    id: int
    position: int


def apply_order(items: Sequence[Positioned], ids: list[int], label: str) -> None:
    """Set `position` on `items` following `ids`, which must list every item exactly once."""
    by_id = {item.id: item for item in items}
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise InvalidError(f"ids must list every {label} exactly once")
    for position, item_id in enumerate(ids):
        by_id[item_id].position = position
