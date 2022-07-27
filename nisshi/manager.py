# nisshi - Manager

from __future__ import annotations

from typing import Generic, TypeVar, Any
from types import ModuleType
from collections.abc import Callable, Iterable

from importlib import import_module

from pathlib import PurePath
from os import walk, mkdir
from os.path import exists

from time import time, sleep

from dataclasses import dataclass

from misaka import Markdown, HtmlRenderer
from tempylate import Manager as TempylateManager, Template

from rich.console import Console

from watchdog.observers import Observer

from .caches import Caches
from .hot_reload import HotReloadFileEventHandler
from .common import Context, FastChecker, _green
from .processor import Processor, RenderProcessor, IncludeProcessor, get_target_directory
from .waste_checker import WasteChecker
from .tools import OSTools, EventTool
from .config import Config
from .page import Page


__all__ = ("Manager",)


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


_UNKNOWN_TYPE = "I was given something I didn't understand."


PageT = TypeVar("PageT", bound=Page, covariant=True)
WasteCheckerT = TypeVar("WasteCheckerT", bound=WasteChecker, covariant=True)
class Manager(FastChecker, OSTools, EventTool, Generic[PageT, WasteCheckerT]):
    """Class for building html.

    Args:
        config: An instance of :class:`config.Config` where the configuration is stored.
        caches: Instance of :class:`config.config` where the cache is stored.
        *args: Arguments to be passed to the constructor of the template engine's class for template management (:class:`tempylate.manager.Manager`).
        misaka_html_renderer_kwargs: Keyword arguments to be passed to the constructor of :class:`misaka.HtmlRenderer` of missaka, a library for markdown rendering.
        misaka_markdown_kwargs: Keyword arguments to be passed to the constructor of :class:`misaka.Markdown` of missaka, a library for markdown rendering.
        waste_checker_cls: Class waste checker to check if you don't need to build. Default is :class:`.waste_checker.WasteChecker`.
        waste_checker_args: Arguments to be passed to the constructor of the waste checker.
        waste_checker_kwargs: Keyword arguments to be passed to the constructor of the waste checker.
        page_cls: This class is used to store page information. Default is :class:`page.Page`.
        **kwargs: Keyword arguments to be passed to the constructor of the template engine's class for template management (:class:`tempylate.manager.Manager`)."""

    observer: Observer | None

    def __init__(
        self, config: Config | None = None, caches: Caches | None = None,
        *args: Any, misaka_html_renderer_kwargs: dict[str, Any] | None = None,
        misaka_markdown_kwargs: dict[str, Any] | None = None,
        waste_checker_cls: type[WasteCheckerT] | None = None,
        waste_checker_args: Iterable[Any] = (),
        waste_checker_kwargs: dict[str, Any] | None = None,
        page_cls: type[PageT] | None = None, **kwargs: Any
    ):
        self.markdown = Markdown(
            HtmlRenderer(**misaka_html_renderer_kwargs or {}), **misaka_markdown_kwargs or {}
        )
        self.config = config or Config()
        self.page_cls = page_cls or Page
        self.waste_checker = (waste_checker_cls or WasteChecker)(
            *waste_checker_args, **(waste_checker_kwargs or {})
        )
        self.waste_checker.manager = self
        self.console = Console(quiet=True)

        self.caches = caches or Caches.from_file(self.config.caches_file)
        self.ctx: Context[Any] = Context()
        self._counter = Counter()

        self._last = ("", 0.0)
        self._updated_layouts = set[PurePath]()

        self.tempylate = TempylateManager[Template](*args, **kwargs)
        self.is_building_all = False

        super().__init__()
        super(FastChecker, self).__init__(self)
        super(OSTools, self).__init__(self)

        self.extensions: dict[str, ModuleType] = {}
        for name in self.config.extensions:
            self.load_extension(name)

    def extend_page(self, new: type[Page]) -> None:
        if not issubclass(new, Page):
            raise TypeError(_UNKNOWN_TYPE)
        if self.page_cls.__bases__[0] != Generic:
            new.__bases__ = self.page_cls.__bases__
        self.page_cls = new

    def extend_waste(self, new: type[WasteChecker]) -> None:
        if not issubclass(new, WasteChecker):
            raise TypeError(_UNKNOWN_TYPE)
        if self.waste_checker.__class__.__bases__:
            new.__bases__ = self.waste_checker.__class__.__bases__
        self.waste_checker.__class__ = new

    def load_extension(self, name: str) -> None:
        """Load the extension.

        Args:
            name: The name of the extension.

        Notes:
            This will import the specified one.
            It then executes the function `setup`, if present, passing an instance of this class.
            If you are making a third-party library for NISSHI, make it so that you can load it with this."""
        self.extensions[name] = import_module(name)
        if hasattr(self.extensions[name], "setup"):
            self.extensions[name].setup(self)

    def _print_exception(self) -> None:
        self.console.print_exception(
            show_locals=self.manager.config.debug_mode,
            max_frames=100 if self.manager.config.debug_mode else 1
        )

    def build(self, path: PurePath, force: bool = False) -> None:
        self.dispatch("on_build", path)
        try:
            path.parents[-2]
        except IndexError:
            return
        self.waste_checker.force_build = force
        if path.parents[-2].name == self.manager.config.layout_folder:
            if self.is_fast(path):
                self.manager.build_all()
        else:
            processor: Processor
            directory = self.manager.swap_path(path.parent, self.manager.config.output_folder)
            match path.parents[-2].name:
                case self.manager.config.include_folder:
                    processor = IncludeProcessor(self.manager, path, directory)
                case self.manager.config.input_folder:
                    processor = RenderProcessor(self.manager, path, directory)
                case _:
                    return
            processor.start()
        self.waste_checker.force_build = False

    def _build(self, processor_cls: type[Processor]) -> None:
        "指定された過程でのビルドを実行します。"
        for path, directory in self.walk_for_build(
            get_target_directory(processor_cls, self)
        ):
            processor = processor_cls(self, path, directory)
            if processor.start():
                self._counter.ok += 1
            elif processor.error is not None:
                self._counter.error += 1

    def build_all(self) -> int:
        "Build what is in the source folder."
        self.is_building_all = True
        self.dispatch("on_build_all")
        self.console.log("Building all...", highlight=False)

        if not exists(self.config.output_folder):
            mkdir(self.config.output_folder)

        count, start_at = 0, time()
        self._counter.reset()
        self._updated_layouts = set()

        # ソースフォルダにある全てまたは渡されたパスのファイルのビルドをする。
        with self.console.status("[bold blue]Building...", spinner="bouncingBar") as status:
            self._build(RenderProcessor)
            self._build(IncludeProcessor)

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
            self.clean()

            # キャッシュをセーブする。
            status.status = "[bold blue]Saving caches..."
            status.update()
            self.caches.save(self.config.caches_file)

        self.is_building_all = False
        return count

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

    def clean(self) -> None:
        "Delete unwanted files in the output folder."
        for raw_current_output, _, raw_output_paths in walk(self.config.output_folder):
            current_output = PurePath(raw_current_output)
            output_paths = set(map(current_output.joinpath, map(PurePath, raw_output_paths)))

            # オリジナルが存在しないものを探す。
            for folder in self.config.FOLDERS:
                if folder == self.config.output_folder:
                    continue

                # オリジナルのファイルのあるフォルダのパスを作る。
                original_current = self.swap_path(current_output, folder)

                # オリジナルが存在するかをを確かめる。
                found = []
                for output_path, original_path in map(lambda op: (
                    op, original_current.joinpath(op.name)
                ), output_paths):
                    if folder == self.config.input_folder:
                        # インプットフォルダの場合はインプット元の拡張子が変わるためありえる拡張子を全て試す。
                        for ext in self.config.input_ext:
                            new_path = self.exchange_extension(original_path, ext)
                            if exists(new_path):
                                found.append(output_path)
                    elif exists(original_path):
                        found.append(output_path)
                # 身元が見つかったものはチェック対象から外す。
                for path in found:
                    output_paths.remove(path)

            # 掃除をする。
            for output_path in output_paths:
                # キャッシュに存在するものは消す。
                if original_path in self.caches.outputs:
                    del self.caches.outputs[original_path]
                # オリジナルが存在しない出力結果を消す。
                self._clean(None, output_path, False)

    def _clean(self, input_path: PurePath | None, output_path: PurePath, is_directory: bool) -> None:
        """指定されたパスのキャッシュとファイルを削除します。
        出力先のパスのファイルの削除専用です。
        入力元のパスが渡された場合は、それがキャッシュに存在するかを確認して、存在する場合はそのキャッシュを消します。"""
        self.dispatch("on_clean", input_path, output_path, is_directory)
        raw_input_path = str(input_path)
        if is_directory:
            for raw_path in set(self.caches.outputs.keys()):
                if raw_path.startswith(str(raw_input_path)):
                    del self.caches.outputs[raw_path]
        elif raw_input_path in self.caches.outputs:
            del self.caches.outputs[raw_input_path]
        if is_directory:
            self.rmdir(output_path)
        else:
            self.remove(output_path)
        self.console.log("{} {}".format(_green('Cleaned'), output_path))