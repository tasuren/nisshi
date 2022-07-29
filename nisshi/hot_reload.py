# nisshi - Hot Reload

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pathlib import PurePath
from os.path import exists

from watchdog import events

from .config import CURRENT

if TYPE_CHECKING:
    from .manager import Manager


class HotReloadFileEventHandler(events.FileSystemEventHandler):
    """`Manager`クラスのホットリロード版ビルドを実装するために使用するファイル監視クラスです。
    ファイルが変更され次第最適な処理を行います。"""

    def __init__(self, manager: Manager, *args: Any, **kwargs: Any):
        self.manager = manager
        super().__init__(*args, **kwargs)
        super(events.FileSystemEventHandler, self).__init__()

    def _relative(self, path: str) -> PurePath:
        "パスをルートフォルダ(inputs等)とファイルのパスに分けます。"
        return PurePath(path).relative_to(CURRENT)

    def _wrap(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            self.manager._print_exception()

    def on_any_update(self, raw_path: str) -> None:
        "何かしら更新があった際に呼び出すべき関数です。"
        if exists(raw_path):
            self._wrap(self.manager.build, self._relative(raw_path))

    def on_created(self, event: events.DirCreatedEvent | events.FileCreatedEvent) -> None:
        if not event.is_directory:
            self.on_any_update(event.src_path)

    def _clean(self, path_raw: str, is_directory: bool = False) -> None:
        "渡されたパスのファイルの出力先にあるファイルを消す。"
        path = self._relative(path_raw)

        try: path.parents[-2]
        except IndexError: return

        if path.parents[-2].name not in (
            self.manager.config.output_folder,
            self.manager.config.script_folder
        ) and path.parents[-2].name in self.manager.config.FOLDERS and (
            path.parents[-2].name != self.manager.config.input_folder
            or not path.suffix or path.suffix[1:] in self.manager.config.input_exts
        ):
            self.manager._clean(path, self.manager.swap_path(
                PurePath(path), self.manager.config.output_folder,
                None if is_directory else self.manager.config.output_ext
            ), is_directory)

    def on_deleted(self, event: events.DirDeletedEvent | events.FileDeletedEvent) -> None:
        self._wrap(self._clean, event.src_path, event.is_directory)

    def on_modified(self, event: events.DirModifiedEvent | events.FileModifiedEvent) -> None:
        if not event.is_directory:
            self.on_any_update(event.src_path)

    def on_moved(self, event: events.DirMovedEvent | events.FileMovedEvent) -> None:
        self._wrap(self._clean, event.src_path, event.is_directory)
        if not event.is_directory:
            self.on_any_update(event.dest_path)