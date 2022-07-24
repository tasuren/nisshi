# nisshi - Hot Reload

from __future__ import annotations
from os import getcwd

from typing import TYPE_CHECKING, Any

from pathlib import PurePath

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

    def _relative(self, path: str) -> PurePath:
        "パスをルートフォルダ(inputs等)とファイルのパスに分けます。"
        return PurePath(path).relative_to(getcwd())

    def on_any_update(self, raw_path: str) -> None:
        "何かしら更新があった際に呼び出すべき関数です。"
        path = self._relative(raw_path)

        if path.parents[-2].name == self.manager.config.layout_folder:
            if self.is_fast(path):
                self.manager.build()
        else:
            match path.parents[-2].name:
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

    def _clean(self, path_raw: str) -> None:
        "渡されたパスのファイルの出力先にあるファイルを消す。"
        path = self._relative(path_raw)
        if path.parents[-2].name != self.manager.config.output_folder \
                and path.parents[-2].name in self.manager.config.FOLDERS:
            self.manager._clean(self.manager.swap_path(
                PurePath(path), self.config.output_folder
            ), path)

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