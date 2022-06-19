# PySSG - Cache

from __future__ import annotations

from os.path import exists
from os import stat, utime

from dataclasses import dataclass

from .common import Context
from .json import loads, dumps


__all__ = ("Caches", "OutputMetadata", "OutputMetadataContainer")


class OutputMetadata(Context):
    """Context for storing cache of output metadata.
    Output metadata is used to avoid having to re-build something that has already been built."""

    last_update: float
    output_path: str
class OutputMetadataContainer(Context[OutputMetadata]):
    "Context for storing :class:`OutputMetadata`."

    def _process(
        self, path: str, output_path: str,
        is_required_cache_file: bool = False,
        is_exception: bool = False
    ) -> bool | None:
        last_update = stat(path).st_mtime

        if is_required_cache_file:
            if path in self:
                if self[path].last_update >= last_update and not is_exception:
                    return None
                self[path].last_update = last_update
                return True
            self[path] = OutputMetadata(last_update=last_update, output_path=output_path)
        else:
            if exists(output_path):
                if stat(output_path).st_mtime >= last_update and not is_exception:
                    return None
                return True

        return False


class Caches(Context):
    "Context for storing cache."

    outputs: OutputMetadataContainer = OutputMetadataContainer()

    @classmethod
    def from_file(cls, path: str) -> Caches:
        "Load cache. This will be called automatically."
        if exists(path):
            with open(path, 'r') as f:
                raw = f.read()
            data = cls(loads(raw))
        else:
            with open(path, "w") as f:
                f.write(dumps(data := cls()))
        return data


    def save(self, path: str) -> None:
        "Save cache."
        with open(path, 'w') as f:
            f.write(dumps(self))