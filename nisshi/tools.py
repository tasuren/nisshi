# nisshi - Path Tools

from __future__ import annotations

from typing import TYPE_CHECKING
from collections.abc import Iterator

from pathlib import PurePath
from os import listdir, rmdir, walk, mkdir, remove
from os.path import exists

if TYPE_CHECKING:
    from .manager import Manager


__all__ = ("OSTools", "enum")


class OSTools:
    """This class is a collection of functions to create file paths, etc. for :class:`Manager`.

    Args:
        manager: A instance of :class:`Manager`."""

    def __init__(self, manager: Manager):
        self.manager = manager

    def exchange_extension(self, path: PurePath, extension: str) -> PurePath:
        """Exchange extensions.

        Args:
            path: The path.
            extension: The extension."""
        return path.with_suffix(f".{extension}")

    def swap_path(
        self, path: PurePath, after: str | None = None,
        extension: str | None = None
    ) -> PurePath:
        """Swap a folder path with another folder path.

        Args:
            path: The path.
            before: Original directory path.
            after: New directory path. (Default is output folder.)
            extension: New path extension."""
        after_ = PurePath(after or self.manager.config.output_folder)
        path = after_.joinpath(*path.parts[1:])
        if extension is not None:
            path = self.exchange_extension(path, extension)
        return path

    def walk_for_build(self, target_directory: str) -> Iterator[tuple[PurePath, PurePath]]:
        """This is :func:`os.walk` for build.
        Returns the path to a file in the specified directory and the path to the output directory when a file of that path is built."""
        if exists(target_directory):
            for current_, _, raw_paths in walk(target_directory):
                current_output = PurePath(self.manager.config.output_folder)
                try:
                    (current := PurePath(current_)).parts[1]
                except IndexError:
                    ...
                else:
                    current_output = current_output.joinpath(*current.parts[1:])
                # ファイルのパスを返す。
                for raw_path in raw_paths:
                    yield current.joinpath(raw_path), current_output

    def mkdir_if_not_exists(self, path: PurePath | None) -> None:
        """If there is no folder with the specified path, create one.

        Args:
            path: The path."""
        if path is not None:
            if not exists(path):
                mkdir(path)

    def remove(self, path: PurePath) -> None:
        """Deletes the file at the specified path and then attempts to delete the folder in which the file resided.

        Args:
            path: The path of the file."""
        remove(path)
        try:
            rmdir(path)
        except (FileNotFoundError, OSError):
            ...


def enum(path: PurePath) -> Iterator[PurePath]:
    """Enumerates the paths to files in the specified directory.

    Args:
        path: The path to the directory."""
    return map(PurePath, listdir(path))