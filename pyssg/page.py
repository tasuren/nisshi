# PySSG - Metadata

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Any

from .common import Context
from . import config

if TYPE_CHECKING:
    from .manager import Manager


__all__ = ("PageContext", "Page")


class PageContext(Context):
    "A class typed after :class:`Context` for web page metadata."

    title: str = ""
    description: str = ""
    head: str = ""
    layout: str | None = None


SelfT = TypeVar("SelfT", bound="Page")
class Page:

    result = ""
    content = ""
    _layout: str | None = None

    def __init__(self: SelfT, manager: Manager[SelfT], path: str):
        self.manager, self.path = manager, path

        self.ctx = PageContext()
        self.ctx.metadata = self.manager.config.metadata

    def build(self, **kwargs: Any) -> str:
        kwargs.setdefault("__self__", self)
        self.result = self.manager.tempylate.render_from_file(
            self.path, **kwargs
        )
        self.result = self.manager.markdown(self.result)
        self.content = self.result
        self.result = self.manager.tempylate.render_from_file(
            self.layout, **kwargs
        )
        return self.result

    @property
    def layout(self) -> str:
        "Gets the path to the layout file."
        if self._layout is None:
            self._layout = "{}/{}".format(
                self.manager.config.layout_folder,
                self.manager.config.default_layout
                if self.ctx.layout is None
                else self.ctx.layout
            )
        return self._layout

    @layout.setter
    def layout(self, value: str) -> None:
        self._layout = value