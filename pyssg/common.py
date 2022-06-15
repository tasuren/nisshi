# PySSG - Common

from typing import Generic, TypeVar, Any


__all__ = ("Context",)


ValueT = TypeVar("ValueT")
class Context(dict[str, ValueT], Generic[ValueT]):
    """Class for storing metadata.
    This class inherits from ``dict`` and makes the contents of its dictionary accessible via attributes."""

    def __init__(self, *args: Any, **kwargs: ValueT):
        super().__init__(*args, **kwargs)
        # アノテーションと一緒に初期値が設定されている場合はそれを設定する。
        for name, value in map(
            lambda name: (name, getattr(self, name)),
            self.__class__.__annotations__
        ):
            self.setdefault(name, value)

    def __setattr__(self, name: str, value: ValueT) -> None:
        self[name] = value
        return super().__setattr__(name, value)

    def _get(self, name: str) -> ValueT:
        if isinstance(data := super().__getitem__(name), list):
            data = [Context(child) for child in data] # type: ignore
        elif isinstance(data, dict):
            data = Context(data) # type: ignore
        return data

    def __getattribute__(self, name: str) -> ValueT:
        if name in self:
            return super().__getattribute__("_get")(name)
        return super().__getattribute__(name)

    def __getitem__(self, name: str) -> ValueT:
        return self._get(name)