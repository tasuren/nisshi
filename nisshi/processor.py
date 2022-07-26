# nisshi - Target

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dataclasses import dataclass

from pathlib import PurePath
from shutil import copy

from rich.traceback import Traceback

from .common import _color, _green, _update_text

if TYPE_CHECKING:
    from .manager import Manager


def get_target_directory(cls: type[Processor], manager: Manager) -> str:
    "処理をする対象のフォルダのパスを取得します。"
    return manager.config[f"{cls._target_directory_key}_folder"]


@dataclass
class Processor:
    "ビルドに必要な処理をする関数を実装するクラスです。"

    manager: Manager
    path: PurePath
    directory: PurePath | None

    result: Any | None = None
    output_path: PurePath | None = None
    error: Exception | None = None
    _target_directory_key: str = ""

    @property
    def target_directory(self) -> str:
        "処理をする対象のフォルダのパスを返します。"
        return get_target_directory(self.__class__, self.manager)

    def check(self) -> bool:
        """処理をしていいかどうかのチェックをする。
        デフォルトの実装は前の処理から時間が全く経っていないかどうかのチェックです。"""
        return self.manager.is_fast(self.path)

    def on_run(self) -> Any:
        "処理の実行が決まった際に呼ばれる関数です。"

    def process(self) -> Any:
        "処理するプログラムを実行する関数です。"

    def start(self) -> bool:
        "処理を実行します。`check`等を実行します。処理をする場合はこれを呼び出してください。"
        if self.check():
            try:
                self.result = self.process()
            except Exception as e:
                self.manager.console.log(Traceback(
                    show_locals=self.manager.config.debug_mode,
                    max_frames=100 if self.manager.config.debug_mode else 1
                ))
                self.error = e
                self.on_error(e)
            else:
                self.on_success()
                return True
        return False

    def on_error(self, _: Exception) -> Any:
        "エラー時に呼び出される関数です。"
        self.manager.console.log(_color("bold", "red", "Failed to process"), self.path)

    def on_success(self) -> Any:
        "成功時に呼び出される関数です。"


class CacheProcessor(Processor):
    "`OutputMetadataContainer._process`を実行する関数を実装したProcessorです。"

    def _cache(self, *args, **kwargs) -> None:
        "キャッシュの処理をします。"
        assert self.output_path is not None
        self.update = self.manager.waste_checker.judge(
            self.path, self.output_path, *args, **kwargs
        )


class RenderProcessor(CacheProcessor):
    "ビルドのレンダリングの過程をするProcessorです。"

    _target_directory_key = "input"

    def check(self) -> bool:
        if any(
            self.path.suffix.endswith(ext)
            for ext in self.manager.config.input_ext
        ) and super().check():
            self.page = self.manager.page_cls(self.manager, self.path)

            # レイアウトが変更されている場合は、レイアウトが変わったことがわかるようにしておく。
            if self.manager.waste_checker.judge(self.page.layout, None) is not None:
                self.manager._updated_layouts.add(self.page.layout)

            # 出力先を用意する。
            self.output_path = self.manager.swap_path(
                self.path, extension=self.manager.config.output_ext
            )
            self.manager.mkdir_if_not_exists(self.directory)
            self._cache(force=self.page.layout in self.manager._updated_layouts)

            return self.update is not None
        return False

    def process(self) -> Any:
        # ビルドする。
        self.page.build()

        assert self.output_path is not None and self.update is not None
        with open(self.output_path, "w") as f:
            f.write(self.page.result)

    def on_success(self):
        self.manager.console.log(_green(_update_text(self.update)), self.output_path)


class IncludeProcessor(CacheProcessor):
    "ビルドのincludesフォルダの中身をコピーする過程をするProcessorです。"

    _target_directory_key = "include"

    def check(self) -> bool:
        if super().check():
            self.output_path = self.manager.swap_path(self.path)
            self.manager.mkdir_if_not_exists(self.directory)
            self._cache()
            return self.update is not None
        return False

    def process(self) -> Any:
        # コピーする。
        assert self.output_path is not None
        copy(self.path, self.output_path)

    def on_success(self):
        self.manager.console.log(
            _green(_update_text(self.update, noupdate="Copied")),
            self.output_path
        )