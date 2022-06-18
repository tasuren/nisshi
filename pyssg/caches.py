# PySSG - Cache

from __future__ import annotations

from os.path import exists
from os import stat

from .common import Context
from .json import loads, dumps


__all__ = ("Caches", "OutputMetadata")


class OutputMetadata(Context):
    """Context for storing cache of output metadata.
    Output metadata is used to avoid having to re-build something that has already been built."""

    last_update: float
    output_path: str
class OutputMetadataContainer(Context[OutputMetadata]):
    "Context for storing :class:`OutputMetadata`."

    def process(self, path: str, output_path: str, is_exception: bool = False) -> bool | None:
        """Sets the specified output metadata.
        At this time, the last modified date is automatically updated.
        It returns a bool value or ``None``.
        The bool value is whether or not an update has been made, or ``False`` if a new cache has been created.
        If the last_update of the file and the last update date of the cache are the same, there is no need to write the cache.
        Return ``None`` then.

        Args:
            path: The original path of the output destination.
            output_path: The path of the output destination.
            is_exception: Whether to treat the cache as old even if the last modified date is the same as the last modified date of the file in the specified path."""
        last_update = stat(path).st_mtime
        if path in self:
            if self[path].last_update >= last_update and not is_exception:
                return None
            self[path].last_update = last_update
            return True
        else:
            self[path] = OutputMetadata(last_update=last_update, output_path=output_path)
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