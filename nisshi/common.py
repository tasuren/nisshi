# nisshi - Common

from __future__ import annotations

from typing import Generic, TypeVar, Any


__all__ = ("Context",)


ValueT = TypeVar("ValueT")
DiT = TypeVar("DiT")
class Context(dict[Any, ValueT], Generic[ValueT]):
    """Class for storing metadata.
    This class inherits from ``dict`` and makes the contents of its dictionary accessible via attributes."""

    def __init__(self, *args: Any, **kwargs: ValueT):
        super().__init__(*args, **kwargs)
        # 初期値を代入する。
        for name in dir(self):
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


def _color(m, c, t):
    return f"[{m} {c}]{t}[/{m} {c}]"
def _green(text: str) -> str:
    return _color("bold", "green", text)


def _update_text(is_updated: bool, update: str = "Updated", noupdate: str = "Built") -> str:
    return update if is_updated else noupdate