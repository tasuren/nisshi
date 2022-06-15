# PySSG - Metadata

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Any

from .common import Context
from . import config

if TYPE_CHECKING:
    from .manager import Manager


class PageContext(Context):
    "A class typed after :class:`Context` for web page metadata."

    title: str = "..."
    description: str = "..."
    head: str = ""


SelfT = TypeVar("SelfT", bound="Page")
class Page:
    def __init__(self: SelfT, manager: Manager[SelfT], path: str):
        self.manager, self.path = manager, path
        self.result, self.content = "", ""

        self.ctx = PageContext()

    def build(self, **kwargs: Any) -> str:
        kwargs.setdefault("__self__", self)
        self.result = self.manager.tempylate.render_from_file(
            self.path, **kwargs
        )
        self.result = self.manager.markdown(self.result)
        self.content = self.result
        self.result = self.manager.tempylate.render_from_file(
            self.get_layout(), **kwargs
        )
        return self.result

    def get_layout(self) -> str:
        """Gets the path to the layout file.
        Override this function if you want to dynamically change the layout file path."""
        return self.manager.config.layout_file