# nisshi - Metadata

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, Any

from pathlib import PurePath

from .common import Context

if TYPE_CHECKING:
    from .waste_checker import WasteChecker
    from .manager import Manager


__all__ = ("PageContext", "Page")


class PageContext(Context):
    "A class typed after :class:`Context` for web page metadata."

    title: str = ""
    description: str = ""
    head: str = ""
    layout: str | None = None


SelfT = TypeVar("SelfT", bound="Page")
WasteCheckerT = TypeVar("WasteCheckerT", bound=WasteChecker)
class Page(Generic[WasteCheckerT]):

    result = ""
    content = ""
    _layout: PurePath | None = None

    def __init__(self: SelfT, manager: Manager[SelfT, WasteCheckerT], path: PurePath):
        self.manager, self.path = manager, path

        self.ctx = PageContext()
        self.ctx.metadata = self.manager.config.metadata

    def build(self, **kwargs: Any) -> str:
        kwargs.setdefault("__self__", self)
        self.result = self.manager.tempylate.render_from_file(
            str(self.path), **kwargs
        )
        self.result = self.manager.markdown(self.result)
        self.content = self.result
        self.result = self.manager.tempylate.render_from_file(
            str(self.layout), **kwargs
        )
        return self.result

    @property
    def layout(self) -> PurePath:
        "Gets the path to the layout file."
        if self._layout is None:
            self._layout = PurePath(
                self.manager.config.default_layout
                if self.ctx.layout is None
                else self.ctx.layout
            )
        return self._layout

    @layout.setter
    def layout(self, value: str) -> None:
        self._layout = PurePath(value)