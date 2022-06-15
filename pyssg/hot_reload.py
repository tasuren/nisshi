# PySSG - Hot Reload

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from watchdog.events import FileSystemEventHandler, FileSystemEvent

if TYPE_CHECKING:
    from .manager import Manager


class HotReloadFileEventHandler(FileSystemEventHandler):
    def __init__(self, manager: Manager, *args: Any, **kwargs: Any):
        self.manager = manager
        super().__init__(*args, **kwargs)
        self._waiting()

    def _waiting(self) -> None:
        self.manager.console.log("Waiting for change...")

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type != "closed":
            event.is_synthetic
            if self.manager.build(event.src_path):
                self._waiting()