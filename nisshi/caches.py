# nisshi - Cache

from __future__ import annotations

from os.path import exists

from .common import Context
from .json import loads, dumps


__all__ = ("Caches", "OutputMetadata", "OutputMetadataContainer")


class OutputMetadata(Context):
    """Context for storing cache of output metadata.
    Output metadata is used to avoid having to re-build something that has already been built on :class:`.waste_checker.WasteChecker`."""

    last_update: float
    output_path: str


class Caches(Context):
    "Context for storing cache."

    outputs: Context[OutputMetadata] = Context()

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