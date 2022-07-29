# nisshi - Metadata

from __future__ import annotations

from typing import Any

from pathlib import PurePath

from .manager import Manager, _replace_cls
from .common import Context


__all__ = ("PageContext", "Page")


class PageContext(Context):
    "A class typed after :class:`Context` for web page metadata."

    title: str = ""
    description: str = ""
    head: str = ""


@_replace_cls("page_cls")
class Page:

    result = ""
    content = ""
    context_cls = PageContext
    output_path: PurePath
    _layout: PurePath | None = None

    def __init__(self, manager: Manager, input_path: PurePath):
        self.manager, self.input_path = manager, input_path
        self.ctx = self.context_cls()
        self.manager.dispatch("on_init_page", self)

    def render(self, **kwargs: Any) -> None:
        """Renders the page.
        The default implementation renders this class of page first, then renders the markdown.
        And finally, we render the finished product to embed it in the layout file.

        Args:
            **kwargs: Keyword arguments to be passed to page."""
        self.result = self.manager.tempylate.render_from_file(
            str(self.input_path), **kwargs
        )
        self.result = self.manager.markdown(self.result)
        self.content = self.result
        self.result = self.manager.tempylate.render_from_file(
            str(self.layout), **kwargs
        )

    def build(self, **kwargs: Any) -> str:
        """Execute :meth:`Page.render` to build.

        Args:
            **kwargs: Keyword arguments to be passed to page."""
        kwargs.setdefault("__self__", self)
        self.manager.dispatch("on_before_build_page", self)
        self.render(**kwargs)
        self.manager.dispatch("on_after_build_page", self)
        return self.result

    @property
    def layout(self) -> PurePath:
        "Gets the path to the layout file."
        if self._layout is None:
            self._layout = PurePath(self.manager.config.default_layout)
        return self._layout

    @layout.setter
    def layout(self, value: str) -> None:
        self._layout = PurePath(value)