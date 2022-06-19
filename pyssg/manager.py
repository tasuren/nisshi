# PySSG - Manager

from __future__ import annotations

from typing import Generic, TypeVar, Literal, Any
from collections.abc import Callable, Iterator

from os.path import exists
from os import walk, remove, rmdir, mkdir
from shutil import copy
from time import time, sleep

from collections import defaultdict
from dataclasses import dataclass

from misaka import Markdown, HtmlRenderer
from tempylate import Manager as TempylateManager, Template

from rich.traceback import Traceback
from rich.console import Console

from watchdog.observers import Observer

from .caches import Caches
from .hot_reload import HotReloadFileEventHandler
from .common import Context
from .config import Config
from .page import Page


__all__ = ("Manager",)


def _color(m, c, t):
    return f"[{m} {c}]{t}[/{m} {c}]"
def _green(text: str) -> str:
    return _color("bold", "green", text)


def _update_text(is_updated: bool, update: str = "Updated", noupdate: str = "Built") -> str:
    return update if is_updated else noupdate


@dataclass
class Counter():

    ok: int = 0
    error: int = 0
    stop: bool = True

    def reset(self) -> None:
        self.stop = False
        for name in self.__annotations__.keys():
            setattr(self, name, 0)

    def sum_(self) -> int:
        return sum(map(lambda n: getattr(self, n), self.__annotations__.keys()))


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
        self, config: Config | None = None, caches: Caches | None = None,
        *args: Any, misaka_html_renderer_kwargs: dict[str, Any] | None = None,
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
        self.ctx: Context[Any] = Context()
        self._counter = Counter()

        self._last = ("", 0.0)
        self._updated_layouts = set[str]()

        self.tempylate = TempylateManager[Template](*args, **kwargs)

    def _exchange_extension(self, path: str, ext: str) -> str:
        # 拡張子を交換する。
        if "." in path:
            path = f'{path[:path.rfind(".")+1]}{ext}'
        return path

    def exchange_path(
        self, path: str, original: str,
        to: str | None = None,
        ext: str | None = None
    ) -> str:
        """Exchange the folder path to the another folder path to make it the output destination path.

        Args:
            path: The path.
            original: Original directory path.
            to: New directory path. (Default is output folder.)
            ext: New path extension."""
        path = path.replace(original, to or self.config.output_folder)
        if ext is not None:
            path = self._exchange_extension(path, ext)
        return path

    def build_hot_reload(self, other_task: Callable[[], Any] = lambda: sleep(1)) -> None:
        """Automatically run :meth:`.build` on file changes in the source folder.

        Args:
            other_task: Another program to run during file monitoring."""
        self.observer = Observer()
        self.observer.schedule(HotReloadFileEventHandler(self), "./", recursive=True)
        self.observer.start()
        try:
            while True:
                other_task()
        finally:
            self.observer.stop()
            self.observer.join()

    _ReT = TypeVar("_ReT")
    def _try(self, function: Callable[..., _ReT], *args, **kwargs) -> _ReT | Exception:
        # 実行を試みます。エラーは表示するだけにします。
        try:
            data = function(*args, **kwargs)
        except Exception as error:
            self.console.log(Traceback(
                show_locals=self.config.debug_mode, max_frames=100
                    if self.config.debug_mode else 1
            ))
            return error
        else:
            return data

    def _walk_for_build(self, base_path: str) -> Iterator[tuple[str, str]]:
        # 全ファイルを一つづつ列挙する。また、出力先のフォルダのパスも作る。
        if exists(base_path):
            for current, _, paths in walk(base_path):
                current_output = current.replace(base_path, self.config.output_folder)
                # ファイルのパスを返す。
                for path in map(lambda p: "/".join((current, p)), paths):
                    yield path, current_output

    def _mkdir_if_not_exists(self, path: str | None) -> None:
        # 指定されたパスにフォルダがないのなら作る。
        if path is not None:
            if not exists(path):
                mkdir(path)

    def _render(self, path: str, directory: str | None) -> bool:
        if not path.endswith(tuple(self.config.input_ext)):
            return False

        self._mkdir_if_not_exists(directory)

        # 一つのファイルのビルド(レンダリング)を行う。
        page = self.page_cls(self, path)
        if self.caches.outputs._process(page.layout, "", True) is not None:
            # レイアウトが変更されている場合は、レイアウトが変わったことがわかるようにしておく。
            self._updated_layouts.add(page.layout)

        output_path = self.exchange_path(
            path, self.config.input_folder,
            ext=self.config.output_ext
        )

        if (update := self.caches.outputs._process(
            path, output_path, is_exception=page.layout in self._updated_layouts
        )) is None:
            return False

        # ビルドする。
        page.build()
        with open(output_path, "w") as f:
            f.write(page.result)

        self.console.log(_green(_update_text(update)), output_path)
        return True

    def _include(self, path: str, directory: str | None) -> bool:
        # includesにあるファイルをコピーします。
        self._mkdir_if_not_exists(directory)

        output_path = self.exchange_path(path, self.config.include_folder)
        if (update := self.caches.outputs._process(path, output_path)) is None:
            return False

        copy(path, output_path)

        self.console.log(_green(_update_text(update, noupdate="Copied")), output_path)
        return True

    def _before_process(self, path: str) -> bool:
        # 処理の前に実行するものです。
        if self._last[0] == path and time() - self._last[1] < 0.3:
            # 前回から時間が経っていないのに変更があったとなった時は、テキストエディタがなんらかのアクセスをしたためなのでパスする。
            return False
        self._last = (path, time())
        return True

    def _after_process(self, path: str, result):
        # 処理後に実行するものです。
        if isinstance(result, Exception):
            self.console.log(_color("bold", "red", "Failed to process"), path)
        elif result:
            if not self._counter.stop:
                self._counter.ok += 1

    def _process(
        self, function: Callable[[str, str | None], Any], path: str | None,
        directory: str | None, parent: str | None,
        missing_paths: list[str] | None = None
    ) -> None:
        # ビルド等を行います。
        if path is None:
            assert missing_paths is not None and parent is not None
            # パスが指定されてない場合は、全ファイルを一つづつビルドする。
            for path, directory in self._walk_for_build(parent):
                if path in missing_paths:
                    missing_paths.remove(path)
                if self._before_process(path):
                    self._after_process(path, self._try(function, path, directory))
        elif self._before_process(path):
            self._counter.stop = True
            self._after_process(path, self._try(function, path, directory))
            self._counter.stop = False

    def build(self) -> int:
        "Build what is in the source folder."
        # ビルド先がないのなら作る。
        self.console.log("Building all...", highlight=False)

        if not exists(self.config.output_folder):
            mkdir(self.config.output_folder)

        count, start_at = 0, time()
        missing_paths = list(self.caches.outputs.keys())
        self._counter.reset()

        # ソースフォルダにある全てまたは渡されたパスのファイルのビルドをする。
        with self.console.status("[bold blue]Building...", spinner="bouncingBar") as status:
            # ビルドを行う。
            self._process(
                self._render, None, None,
                self.config.input_folder,
                missing_paths
            )
            # assets内のファイルのコピーを行う。
            self._process(
                self._include, None, None,
                self.config.include_folder,
                missing_paths
            )

            # 何個処理をしたか表示する。
            self.console.log("[bold blue]{} files were processed in {:.4f}ms.".format(
                self._counter.sum_(), (time() - start_at) / 1000
            ))
            if self._counter.error:
                self.console.log(
                    "[bold red]But %s files were made errors but were ignored."
                    % self._counter.error
                )

            # オリジナルが存在しないファイルを消す。
            status.status = "[bold blue]Cleaning..."
            status.update()
            for current_output, _, raw_output_paths in walk(self.config.output_folder):
                # オリジナルが存在しないものを探す。
                delete_after: defaultdict[str, list[str]] = defaultdict(list)
                for folder in self.config.FOLDERS:
                    if folder == self.config.output_folder:
                        continue

                    # オリジナルのパスを作る。
                    original_current = current_output.replace(self.config.output_folder, folder)
                    paths = set(map(
                        lambda op: (f"{current_output}/{op}", f"{original_current}/{op}"),
                        raw_output_paths
                    ))

                    # オリジナルが存在するかをを確かめる。
                    for output_path, original_path in paths:
                        if folder == self.config.input_folder:
                            # インプットフォルダの場合はインプット元の拡張子が変わるためありえる拡張子を全て試す。
                            for ext in self.config.input_ext:
                                new_path = self._exchange_extension(original_path, ext)
                                if exists(new_path):
                                    break
                                delete_after[output_path].append(new_path)
                            else:
                                continue
                            break
                        elif exists(original_path):
                            break
                        else:
                            delete_after[output_path].append(original_path)
                    else:
                        continue
                    break
                else:
                    # 掃除をする。
                    for output_path, original_paths in delete_after.items():
                        # キャッシュに存在するものは消す。
                        for original_path in original_paths:
                            if original_path in self.caches.outputs:
                                del self.caches.outputs[original_path]
                        # オリジナルが存在しない出力結果を消す。
                        self._clean(output_path)

            # キャッシュをセーブする。
            status.status = "[bold blue]Saving caches..."
            status.update()
            self.caches.save(self.config.caches_file)

        return count

    def join_path(
        self, target: Literal["includes", "layout", "input", "output"] | str,
        path: str
    ) -> str:
        """Concatenates the specified folder with the path passed.

        Args:
            target: Folder type. (e.g. `asset`)
            path: The path."""
        return f'{getattr(self.config, f"{target}_folder", target)}/{path}'

    def _remove(self, path: str) -> None:
        # 指定されたファイルを削除して、その元のフォルダの削除を試みます。
        remove(path)
        try:
            rmdir(path[:path.rfind("/")])
        except (FileNotFoundError, OSError):
            ...

    def _clean(self, output_path: str) -> None:
        # 指定されたパスのキャッシュとファイルを削除します。
        # 出力先のパスのファイルの削除専用です。
        self._remove(output_path)
        self.console.log("{} {}".format(_green('Cleaned'), output_path))