# PySSG - Common

from __future__ import annotations

from typing import Generic, TypeVar, Any

from inspect import get_annotations
from types import SimpleNamespace


__all__ = ("Context",)


def _get_context(cls: type[Context], name: str, annotations: dict[str, Any] | None = None) -> Any:
    annotations = annotations or get_annotations(cls, eval_str=True)
    if name in annotations:
        if annotations[name]:
            return annotations[name]
    return cls


def _transform(
    cls: type[Context], name: str, data: dict | list | Any,
    annotation: Any = None
) -> tuple[dict | list | Any, bool]:
    if isinstance(data, list):
        annotation = annotation or _get_context(cls, name)
        data = list(map(annotation, data)) # type: ignore
    elif isinstance(data, dict):
        annotation = annotation or _get_context(cls, name)
        data = annotation(data) # type: ignore
    else:
        return data, False
    return data, True


ValueT = TypeVar("ValueT")
class Context(dict[Any, ValueT], Generic[ValueT]):
    """Class for storing metadata.
    This class inherits from ``dict`` and makes the contents of its dictionary accessible via attributes."""

    def __init__(self, *args: Any, **kwargs: ValueT):
        super().__init__(*args, **kwargs)
        # アノテーションが`Context`なものは`Context`にする。
        for name, annotation in get_annotations(self.__class__, eval_str=True).items():
            if name in self:
                self._get(name, annotation)
        for name in dir(self):
            if not name.startswith("__"):
                value = getattr(self, name)
                if isinstance(value, dict) or isinstance(value, list):
                    self[name] = value.copy() # type: ignore

    def __setattr__(self, name: str, value: ValueT) -> None:
        self[name] = value

    def _get(self, name: str, annotation: Any = None) -> ValueT:
        data, is_transformed = _transform(
            super().__getattribute__("__class__"),
            name, super().__getitem__(name),
            annotation
        )
        if is_transformed:
            super().__setitem__(name, data) # type: ignore
        return data # type: ignore

    def __getattribute__(self, name: str) -> ValueT:
        if name in self:
            return self[name]
        return super().__getattribute__(name)

    def __getitem__(self, name: str) -> ValueT:
        return self._get(name)