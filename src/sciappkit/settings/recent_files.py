"""Recent-files list helper.

Both source apps keep a capped, de-duplicated most-recently-used list
(graphulator in a sidecar dotfile, Diagrammer in its settings JSON). This
normalizes that into one helper that can be backed by a
:class:`~sciappkit.settings.store.SettingsStore` list field (so it
persists with everything else) or run standalone in memory.

``add`` moves an existing entry to the front, de-duplicates, and caps the
list; ``prune_missing`` drops entries whose files no longer exist.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MAX_ITEMS = 10


class RecentFiles:
    """An ordered, de-duplicated, capped most-recently-used path list."""

    def __init__(self, store=None, *, field: str = "recent_files", max_items: int = DEFAULT_MAX_ITEMS) -> None:
        self._store = store
        self._field = field
        self._max = max_items
        self._mem: list[str] = []

    # -- backing storage ----------------------------------------------------

    def _load(self) -> list[str]:
        if self._store is not None:
            return list(getattr(self._store, self._field, []) or [])
        return list(self._mem)

    def _store_items(self, items: list[str]) -> None:
        items = items[: self._max]
        if self._store is not None:
            setattr(self._store, self._field, items)
            self._store.save()
        else:
            self._mem = items

    # -- API ----------------------------------------------------------------

    def items(self) -> list[str]:
        return self._load()

    def add(self, path: str | os.PathLike) -> None:
        p = str(path)
        items = [x for x in self._load() if x != p]
        items.insert(0, p)
        self._store_items(items)

    def remove(self, path: str | os.PathLike) -> None:
        p = str(path)
        self._store_items([x for x in self._load() if x != p])

    def clear(self) -> None:
        self._store_items([])

    def prune_missing(self) -> None:
        self._store_items([x for x in self._load() if Path(x).exists()])

    def __iter__(self):
        return iter(self._load())

    def __len__(self) -> int:
        return len(self._load())

    def __contains__(self, path: str | os.PathLike) -> bool:
        return str(path) in self._load()
