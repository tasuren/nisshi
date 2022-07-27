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
    """Context for storing settings.
    It can also be written to a configuration file."""

    include_folder = "includes"
    "This is the folder where the files to be copied to the output folder will be placed."
    input_folder = "inputs"
    "This is the folder that contains the contents of the website."
    output_folder = "outputs"
    "Destination folder."
    script_folder = "scripts"
    """This is the folder where the scripts are placed.
    It is imported at build time.
    Also, if there is a ``setup`` function, it is executed by passing it an instance of the :class:`Manager` class."""
    layout_folder = "layouts"
    "This is the folder where layout files are placed."
    default_layout = "layouts/layout.html"
    "The name of the file for the default layout."
    caches_file = ".nisshi_caches.json"
    "The name of the cache file."
    input_ext: Sequence[str] = ("md",)
    "File format of the input."
    output_ext = "html"
    "The file format of the output."
    debug_mode: bool = False
    "If this is set to `True`, the error will be displayed in full when an error occurs."
    extensions: Sequence[str] = ()
    "Sequence of names of extensions to be loaded."
    metadata: dict[str, Any] = {}
    "This data can be accessed from within the template."

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