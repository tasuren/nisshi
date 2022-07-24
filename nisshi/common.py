# nisshi - Common

from __future__ import annotations

from typing import Generic, TypeVar, Any

from pathlib import PurePath
from time import time


__all__ = ("Context",)


ValueT = TypeVar("ValueT")
DiT = TypeVar("DiT")
class Context(dict[Any, ValueT], Generic[ValueT]):
    """Class for storing metadata.
    This class inherits from ``dict`` and makes the contents of its dictionary accessible via attributes."""

    def __init__(self, *args: Any, **kwargs: ValueT):
        super().__init__(*args, **kwargs)
        # 初期値を代入する。
        for name in dir(self.__class__):
            if not name.startswith("_") and not callable(value := getattr(self, name)) \
                    and name not in self:
                value = value.copy() \
                    if isinstance(value, dict) or isinstance(value, list) \
                    else value
                self[name] = value
        # 初期値のトランスフォームを行う。
        for key, value in self.items():
            self[key] = self._transform(value)

    @staticmethod
    def _transform(value):
        "`dict`か`list`の場合は`Context`にします。"
        if isinstance(value, dict):
            new = Context()
            for key, v in list(value.items()):
                new[key] = Context._transform(v)
            return new
        elif isinstance(value, list) and value and isinstance(value[0], dict | list):
            return list(map(Context._transform, value))
        return value

    def __setattr__(self, name: str, value: ValueT) -> None:
        self[name] = value

    def __getattribute__(self, name: str) -> ValueT | Any:
        if name in self:
            return self[name]
        return super().__getattribute__(name)


class FastChecker:
    """This class is used to check if a file path has been re-updated at an abnormally fast rate.
    This is used to prevent duplicate builds from being accessed by text editors."""

    def __init__(self):
        self.path = ""
        self.time_ = 0.0

    def is_fast(self, path: str | PurePath, interval: float = 0.3) -> bool:
        """This function returns whether this function has been executed within the last `interval` at the specified path.

        Args:
            path: The path.
            interval: It is how many seconds or less to check."""
        path = str(path) if isinstance(path, PurePath) else path
        now = time()
        if self.path == path and now - self.time_ < interval:
            return False
        self.path, self.time_ = path, now
        return True


def _color(m, c, t):
    return f"[{m} {c}]{t}[/{m} {c}]"
def _green(text: str) -> str:
    return _color("bold", "green", text)


def _update_text(is_updated: bool, update: str = "Updated", noupdate: str = "Built") -> str:
    return update if is_updated else noupdate