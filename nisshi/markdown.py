# nisshi - Markdown

try: from mizu import parse_ext
except ModuleNotFoundError: from mistletoe import markdown
else:
    from typing import Any
    def markdown(text: str, *args: Any, **kwargs: Any) -> str:
        kwargs.setdefault("tables", True)
        return parse_ext(text, *args, **kwargs)


__all__ = ("markdown",)
