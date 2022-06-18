# PySSG - Config

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

from os.path import exists

from toml import load

from .common import Context


__all__ = ("Config",)


class Config(Context[Any]):
    "Context for storing settings."

    layout_folder = "layouts"
    include_folder = "includes"
    source_folder = "sources"
    output_folder = "outputs"
    script_folder = "scripts"
    default_layout = "layout.html"
    exclude: Sequence[str] = ()
    include: Sequence[str] = ()
    file_ext: Sequence[str] = ("md",)
    caches_file = ".pyssg_caches.json"
    output_ext = "html"
    debug_mode: bool = False
    metadata: dict[str, Any] = {}

    @classmethod
    def from_file(cls, path: str, ignore_missing: bool = False) -> Config:
        """Load the configuration file.

        Args:
            path: The path to the configuration file.
            ignore_missing: Whether to ignore missing the configuration file."""
        if not ignore_missing or exists(path):
            with open(path, "r") as f:
                raw = load(f)
        else:
            raw = {}

        data = cls(raw)

        return data