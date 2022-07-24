# nisshi - Waste Checker

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abc import ABC, abstractmethod

from pathlib import PurePath
from os.path import exists
from os import stat

from .caches import OutputMetadata

if TYPE_CHECKING:
    from .manager import Manager


__all__ = ("WasteChecker",)


class AbcWasteChecker(ABC):
    """This is the base class for the waste checker, a class used to determine if a build is a build that does not need to be done.
    If you are building your own waste checker, you must extend this class and implement the methods in this class.

    Args:
        force_build: Whether to always build without waste checking by waste checker."""

    def __init__(self, force_build: bool = False):
        self.force_build = force_build

    manager: Manager

    @abstractmethod
    def judge(self, path: PurePath, output_path: PurePath, force: bool = False) -> bool | None:
        """Determines whether a file in the given path should be built or not, based on the given path and the destination path after the path is built.
        This is used to avoid the waste of building again when it has already been built.
        If ``None`` is returned, it means there is no point in building.
        It may also return a bool value.
        The bool value in that case indicates whether the build will be overwritten if it is built, or not because it has never been built.
        If ``.force_build`` is ``True``, then this is a no-brainer and will return a bool value instead of ``None``.

        Args:
            path: The path of a file to be used to bulid.
            output_path: The path of a file to be built by using a file of ``path``.
                If the output destination does not exist, it will be ``None``.
            force_bool: Whether to return a bool value instead of returning ``None`` when ``None`` is reached."""


class WasteChecker(AbcWasteChecker):
    """A waste checker that implements a function to check if a build is not wasteful.
    The mechanism implemented in this class is to check if the last modified date of the already built file is the same as that of the file to be built, when the file has already been built at build time.
    For layout files, where the file to build to is a nonexistent file, the last-modified date is stored in the cache instead.

    Args:
        force_cache: Whether to write the last modified date of all files to the cache for processing.
        *args: Arguments to be passed to the constructor of the :class:`AbcWasteChecker`.
        **kwargs: Keyword arguments to be passed to the constructor of the :class:`AbcWasteChecker`."""

    def __init__(self, force_cache: bool = False, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.force_cache = force_cache

    def judge(self, path: PurePath, output_path: PurePath | None, force: bool = False) -> bool | None:
        if self.force_build:
            if output_path is not None and exists(output_path):
                return True
        else:
            last_update = stat(path).st_mtime
            if path.parents[-2].name == self.manager.config.layout_folder or self.force_cache:
                if (raw_path := str(path)) in self.manager.caches.outputs:
                    if self.manager.caches.outputs[raw_path].last_update >= last_update \
                            and not force:
                        return None
                    self.manager.caches.outputs[raw_path].last_update = last_update
                    return True
                self.manager.caches.outputs[raw_path] = OutputMetadata(
                    last_update=last_update, output_path=output_path
                )
            else:
                if output_path is not None and exists(output_path):
                    if stat(output_path).st_mtime >= last_update and not force:
                        return None
                    return True

        return False