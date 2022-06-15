# PySSG - Cache

from __future__ import annotations

from os.path import exists

from .common import Context
from .json import loads, dumps


__all__ = ("Caches", "OutputMetadata")


class OutputMetadata(Context):
    "Context for storing cache of output metadata."

    built_at: float
    output_path: str
class Caches(Context):
    "Context for storing cache."

    output_metadata: Context[OutputMetadata] = Context()

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