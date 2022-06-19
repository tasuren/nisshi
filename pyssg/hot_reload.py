# PySSG - Hot Reload

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from time import time

from watchdog import events

from .config import CURRENT

if TYPE_CHECKING:
    from .manager import Manager


class HotReloadFileEventHandler(events.FileSystemEventHandler):
    def __init__(self, manager: Manager, *args: Any, **kwargs: Any):
        self.manager = manager
        super().__init__(*args, **kwargs)
        self._last: tuple[str, float] = ("", 0.0)

    def _split(self, path: str) -> tuple[str, str]:
        place, _, path = path.replace(CURRENT, "")[1:].partition("/")
        path = f"{place}/{path}"
        return place, path

    def on_any_update(self, path: str) -> None:
        place, path = self._split(path)

        if place == self.manager.config.layout_folder:
            if (now := time()) - self._last[1] >= 0.3:
                self.manager.build()
                self._last = (path, now)
        else:
            if place == self.manager.config.include_folder:
                self.manager._process(self.manager._include, path, None, None)
            elif place == self.manager.config.input_folder:
                self.manager._process(self.manager._render, path, None, None)

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if not event.is_directory:
            self.on_any_update(event.src_path)

    def _clean(self, path: str) -> None:
        place, path = self._split(path)
        if place in self.manager.config.FOLDERS and path in self.manager.caches.outputs:
            self.manager._clean(path)

    def on_deleted(self, event: events.DirDeletedEvent | events.FileDeletedEvent) -> None:
        if not event.is_directory:
            self._clean(event.src_path)

    def on_modified(self, event: events.DirModifiedEvent | events.FileModifiedEvent) -> None:
        if not event.is_directory:
            self.on_any_update(event.src_path)

    def on_moved(self, event: events.DirMovedEvent | events.FileMovedEvent) -> None:
        if not event.is_directory:
            self._clean(event.src_path)
            self.on_any_update(event.dest_path)