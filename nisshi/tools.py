# nisshi - Path Tools

from __future__ import annotations

from typing import TYPE_CHECKING
from collections.abc import Iterator

from os.path import exists
from os import walk, mkdir, rmdir, remove

if TYPE_CHECKING:
    from .manager import Manager


__all__ = ("OSTools",)


class OSTools:
    """This class is a collection of functions to create file paths, etc. for :class:`Manager`.

    Args:
        manager: A instance of :class:`Manager`."""

    def __init__(self, manager: Manager):
        self.manager = manager

    def exchange_extension(self, path: str, extension: str) -> str:
        """Exchange extensions.

        Args:
            path: The path.
            extension: The extension."""
        if "." in path:
            path = f'{path[:path.rfind(".")+1]}{extension}'
        return path

    def exchange_path(
        self, path: str, before: str,
        after: str | None = None,
        extension: str | None = None
    ) -> str:
        """Exchange the folder path to the another folder path to make it the output destination path.

        Args:
            path: The path.
            before: Original directory path.
            after: New directory path. (Default is output folder.)
            extension: New path extension."""
        path = path.replace(before, after or self.manager.config.output_folder)
        if extension is not None:
            path = self.exchange_extension(path, extension)
        return path

    def walk_for_build(self, target_directory: str) -> Iterator[tuple[str, str]]:
        """This is :func:`os.walk` for build.
        Returns the path to a file in the specified directory and the path to the output directory when a file of that path is built."""
        if exists(target_directory):
            for current, _, paths in walk(target_directory):
                current_output = current.replace(
                    target_directory, self.manager.config.output_folder
                )
                # ファイルのパスを返す。
                for path in map(lambda p: "/".join((current, p)), paths):
                    yield path, current_output

    def mkdir_if_not_exists(self, path: str | None) -> None:
        """If there is no folder with the specified path, create one.

        Args:
            path: The path."""
        if path is not None:
            if not exists(path):
                mkdir(path)

    def remove(self, path: str) -> None:
        """Deletes the file at the specified path and then attempts to delete the folder in which the file resided.

        Args:
            path: The path of the file."""
        remove(path)
        try:
            rmdir(path[:path.rfind("/")])
        except (FileNotFoundError, OSError):
            ...