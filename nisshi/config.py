# nisshi - Config

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

from os.path import exists
from os import getcwd

from toml import load

from .common import Context


__all__ = ("Config",)


CURRENT = getcwd()


class Config(Context[Any]):
    "Context for storing settings."

    layout_folder = "layouts"
    include_folder = "includes"
    input_folder = "inputs"
    output_folder = "outputs"
    script_folder = "scripts"
    default_layout = "layout.html"
    exclude: Sequence[str] = ()
    caches_file = ".nisshi_caches.json"
    input_ext: Sequence[str] = ("md",)
    output_ext = "html"
    debug_mode: bool = False
    metadata: dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.FOLDERS = tuple(
            value for name, value in map(lambda n: (n, getattr(self, n)), dir(self))
            if name.endswith("_folder")
        )
        self.FOLDER_PATHS = {
            folder: f"{CURRENT}/{folder}"
            for folder in self.FOLDERS
        }

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