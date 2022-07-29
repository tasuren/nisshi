# nisshi - Waste Checker

from __future__ import annotations

from pathlib import PurePath
from os.path import exists
from os import stat

from .manager import Manager, _replace_cls
from .caches import OutputMetadata


__all__ = ("WasteChecker",)


@_replace_cls("waste_checker_cls")
class WasteChecker:
    """A waste checker that implements a function to check if a build is not wasteful.
    The mechanism implemented in this class is to check if the last modified date of the already built file is the same as that of the file to be built, when the file has already been built at build time.
    For layout files, where the file to build to is a nonexistent file, the last-modified date is stored in the cache instead.

    Args:
        force_cache: Whether to write the last modified date of all files to the cache for processing."""

    def __init__(self, manager: Manager, force_cache: bool = False) -> None:
        self.force_cache, self.manager = force_cache, manager

    def judge(self, path: PurePath, output_path: PurePath | None, force: bool = False) -> bool | None:
        if self.manager.config.force_build:
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