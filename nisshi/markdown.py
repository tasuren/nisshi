# nisshi - Markdown

try: from mizu import parse as markdown
except ModuleNotFoundError: from mistletoe import markdown


__all__ = ("markdown",)