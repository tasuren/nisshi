# nisshi - Hot Reload

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from watchdog import events

from .processor import IncludeProcessor, RenderProcessor
from .common import FastChecker
from .config import CURRENT

if TYPE_CHECKING:
    from .manager import Manager


class HotReloadFileEventHandler(events.FileSystemEventHandler, FastChecker):
    """`Manager`クラスのホットリロード版ビルドを実装するために使用するファイル監視クラスです。
    ファイルが変更され次第最適な処理を行います。"""

    def __init__(self, manager: Manager, *args: Any, **kwargs: Any):
        self.manager = manager
        super().__init__(*args, **kwargs)
        super(events.FileSystemEventHandler, self).__init__()

    def _split(self, path: str) -> tuple[str, str]:
        "パスを分けます。"
        place, _, path = path.replace(CURRENT, "")[1:].partition("/")
        path = f"{place}/{path}"
        return place, path

    def on_any_update(self, path: str) -> None:
        "何かしら更新があった際に呼び出すべき関数です。"
        place, path = self._split(path)

        if place == self.manager.config.layout_folder:
            if self.is_fast(path):
                self.manager.build()
        else:
            match place:
                case self.manager.config.include_folder:
                    processor = IncludeProcessor(self.manager, path, None)
                case self.manager.config.input_folder:
                    processor = RenderProcessor(self.manager, path, None)
                case _:
                    return
            processor.start()

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if not event.is_directory:
            self.on_any_update(event.src_path)

    def _clean(self, path: str) -> None:
        "渡されたパスのファイルの出力先にあるファイルを消す。"
        place, path = self._split(path)
        if place != self.manager.config.output_folder \
                and place in self.manager.config.FOLDERS:
            self.manager._clean(
                self.manager.exchange_path(path, place, self.config.output_folder),
                path
            )

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