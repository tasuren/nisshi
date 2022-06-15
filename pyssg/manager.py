# PySSG - Manager

from __future__ import annotations

from typing import Generic, TypeVar, Any
from collections.abc import Callable

from os.path import exists
from os import walk, stat, remove
from time import time, sleep

from misaka import Markdown, HtmlRenderer
from tempylate import Manager as TempylateManager, Template

from rich.console import Console

from watchdog.observers import Observer

from .caches import Caches, OutputMetadata
from .hot_reload import HotReloadFileEventHandler
from .config import Config
from .page import Page


PageT = TypeVar("PageT", bound=Page, covariant=True)
class Manager(Generic[PageT]):
    """Class for building html.

    Args:
        config: An instance of :class:`config.Config` where the configuration is stored.
        caches: Instance of :class:`config.config` where the cache is stored.
        *args: Arguments to be passed to the constructor of the template engine's class for template management (:class:`tempylate.manager.Manager`).
        misaka_html_renderer_kwargs: Keyword arguments to be passed to the constructor of :class:`misaka.HtmlRenderer` of missaka, a library for markdown rendering.
        misaka_markdown_kwargs: Keyword arguments to be passed to the constructor of :class:`misaka.Markdown` of missaka, a library for markdown rendering.
        cls: This class is used to store page information. Default is :class:`page.Page`.
        **kwargs: Keyword arguments to be passed to the constructor of the template engine's class for template management (:class:`tempylate.manager.Manager`)."""

    observer: Observer | None

    def __init__(
        self, config: Config | None = None, caches: Caches | None = None, *args: Any,
        misaka_html_renderer_kwargs: dict[str, Any] | None = None,
        misaka_markdown_kwargs: dict[str, Any] | None = None,
        cls: type[PageT] | None = None, **kwargs: Any
    ):
        self.markdown = Markdown(
            HtmlRenderer(**misaka_html_renderer_kwargs or {}), **misaka_markdown_kwargs or {}
        )
        self.config = config or Config()
        self.page_cls = cls or Page
        self.console = Console(quiet=True)

        self.caches = caches or Caches.from_file(self.config.caches_file)
        self._last = ("", 0.0)

        self.tempylate = TempylateManager[Template](*args, **kwargs)

    def exchange_output_path(self, path: str, ext: str | None = None) -> str:
        """Exchange the source folder path to the output folder path to make it the output destination path.

        Args:
            path: The path.
            ext: New path extension."""
        path = path.replace(self.config.source_folder, self.config.output_folder)
        if ext is not None and "." in path:
            path = f'{path[:path.rfind(".")+1]}{ext}'
        return path

    def build_hot_reload(self, other_task: Callable[[], Any] = lambda: sleep(1)) -> None:
        """Automatically run :meth:`.build` on file changes in the source folder.

        Args:
            other_task: Another program to run during file monitoring."""
        self.observer = Observer()
        self.observer.schedule(
            HotReloadFileEventHandler(self),
            self.config.source_folder,
            recursive=True
        )
        self.observer.start()
        try:
            while True:
                other_task()
        finally:
            self.observer.stop()
            self.observer.join()

    def _build(self, path: str, missing_paths: list[str]) -> None:
        # 一つのファイルのビルドを行う。
        if path in missing_paths:
            missing_paths.remove(path)

        # 前回から時間が経っていないのに変更があったとなった時は、テキストエディタがなんらかのアクセスをしたためなのでパスする。
        if self._last[0] == path and time() - self._last[1] < 0.3:
            return

        # 最終更新日が前のビルド時のものと変わっていないのならパスする。
        update, last_update = False, stat(path).st_mtime
        if path in self.caches.output_metadata:
            if self.caches.output_metadata[path].built_at >= last_update:
                return
            update = True
            self.caches.output_metadata[path].built_at = last_update
        else:
            self.caches.output_metadata[path] = OutputMetadata(
                built_at=last_update, output_path=self.exchange_output_path(
                    path, self.config.output_ext
                )
            )

        # ビルドする。
        page = self.page_cls(self, path)
        page.build()
        with open(self.caches.output_metadata[path].output_path, "w") as f:
            f.write(page.result)

        self._last = (path, time())
        self.console.log(
            "Update" if update else "Bulit",
            self.caches.output_metadata[path].output_path
        )

    def build(self, target: str | None = None) -> int:
        """Build what is in the source folder.

        Args:
            target: The target files to build.
                If not specified, everything in the source folder is targeted."""
        count, start_at = 0, time()
        missing_paths = list(self.caches.output_metadata.keys())

        # ソースフォルダにある全てまたは渡されたパスのファイルのビルドをする。
        with self.console.status("[bold blue]Building...", spinner="bouncingBar") as status:
            if target is None:
                for current, _, files in walk(self.config.source_folder):
                    for path in map(lambda p: "/".join((current, p)), files):
                        self._build(path, missing_paths)
                        count += 1
            else:
                self._build(target, missing_paths)

            if count:
                self.console.log(f"[bold blue]{count} files were processed in {time() - start_at:.1f}.")

            # 削除されたファイルのキャッシュを消す。
            status.status = "[bold blue]Cleaning..."
            status.update()
            for missing_path in missing_paths:
                if exists(self.caches.output_metadata[missing_path].output_path):
                    # もし身元不明のファイルがあった場合は消す。
                    remove(self.caches.output_metadata[missing_path].output_path)
                    self.console.log(f"Delete unknown file: {self.caches.output_metadata[missing_path].output_path}")
                del self.caches.output_metadata[missing_path]

            status.status = "[bold blue]Saving caches..."
            status.update()
            self.caches.save(self.config.caches_file)

        return count