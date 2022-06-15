# PySSG - Config

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

from toml import load

from .common import Context


__all__ = ("Config",)


class Config(Context[Any]):
    "Context for storing settings."

    template_folder = "templates"
    source_folder = "source"
    output_folder = "output"
    script_folder = "script"
    layout_file = "templates/layout.html"
    exclude: Sequence[str] = ()
    include: Sequence[str] = ()
    file_ext: Sequence[str] = ("md",)
    caches_file = ".pyssg_cache.json"
    output_ext = "html"
    metadata: dict[str, Any] = {}

    @classmethod
    def from_file(cls, path: str) -> Config:
        """Load the configuration file.

        Args:
            path: The path to the configuration file."""
        with open(path, "r") as f:
            raw = load(f)

        data = cls()
        if "build" in raw:
            data.update(raw["build"])

        return data