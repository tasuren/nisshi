# nisshi - Target

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dataclasses import dataclass

from pathlib import PurePath
from os.path import exists
from shutil import copy

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
    input_path: PurePath
    output_directory: PurePath

    result: Any | None = None
    output_path: PurePath | None = None
    error: Exception | None = None
    _target_directory_key: str = ""

    @property
    def target_directory(self) -> str:
        "処理をする対象のフォルダのパスを返します。"
        return get_target_directory(self.__class__, self.manager)

    def check(self) -> bool:
        "処理をしていいかどうかのチェックをする。"
        return True

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
                self.manager._print_exception()
                self.error = e
                self.on_error(e)
                # もし出力先のファイルが存在するなら消す。
                if self.output_path is not None and exists(self.output_path):
                    self.manager.remove(self.output_path)
            else:
                self.on_success()
                return True
        return False

    def on_error(self, _: Exception) -> Any:
        "エラー時に呼び出される関数です。"
        self.manager.console.log(_color("bold", "red", "Failed to process"), self.input_path)

    def on_success(self) -> Any:
        "成功時に呼び出される関数です。"


class CacheProcessor(Processor):
    "`OutputMetadataContainer._process`を実行する関数を実装したProcessorです。"

    def _cache(self, *args, **kwargs) -> None:
        "キャッシュの処理をします。"
        assert self.output_path is not None
        self.update = self.manager.waste_checker.judge(
            self.input_path, self.output_path, *args, **kwargs
        )


class RenderProcessor(CacheProcessor):
    "ビルドのレンダリングの過程をするProcessorです。"

    _target_directory_key = "input"

    def check(self) -> bool:
        if any(
            self.input_path.suffix.endswith(ext)
            for ext in self.manager.config.input_exts
        ) and super().check():
            self.page = self.manager.page_cls(self.manager, self.input_path)

            # レイアウトが変更されている場合は、レイアウトが変わったことがわかるようにしておく。
            if self.manager.waste_checker.judge(self.page.layout, None) is not None:
                self.manager._updated_layouts.add(self.page.layout)

            # 出力先を用意する。
            self.output_path = self.manager.swap_path(
                self.input_path, extension=self.manager.config.output_ext
            )
            self.manager.mkdir_if_not_exists(self.output_directory)
            self._cache(force=self.page.layout in self.manager._updated_layouts)
            self.page.output_path = self.output_path

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
            self.output_path = self.manager.swap_path(self.input_path)
            self.manager.mkdir_if_not_exists(self.output_directory)
            self._cache()
            return self.update is not None
        return False

    def process(self) -> Any:
        # コピーする。
        assert self.output_path is not None
        copy(self.input_path, self.output_path)

    def on_success(self):
        self.manager.console.log(
            _green(_update_text(self.update, noupdate="Copied")),
            self.output_path
        )