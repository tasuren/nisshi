# nisshi - Path Tools

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Any, overload
from collections.abc import Iterator, Callable, Sequence

from collections import defaultdict

from pathlib import PurePath
from os import listdir, rmdir, walk, mkdir, remove
from os.path import exists
from shutil import rmtree

if TYPE_CHECKING:
    from .manager import Manager


__all__ = ("OSTools", "enum", "EventTools")


class OSTools:
    """This class is a collection of functions to create file paths, etc. for :class:`Manager`.

    Args:
        manager: A instance of :class:`Manager`."""

    def __init__(self, manager: Manager):
        self.manager = manager

    def exchange_extension(self, path: PurePath, extension: str) -> PurePath:
        """Exchange extensions.

        Args:
            path: The path.
            extension: The extension."""
        return path.with_suffix(f".{extension}")

    def swap_path(
        self, path: PurePath, after: str | None = None,
        extension: str | None = None
    ) -> PurePath:
        """Swap a folder path with another folder path.
        The path passed must be relative.

        Args:
            path: The path.
            before: Original directory path.
            after: New directory path. (Default is output folder.)
            extension: New path extension."""
        after_ = PurePath(after or self.manager.config.output_folder)
        path = after_.joinpath(*path.parts[1:])
        if extension is not None:
            path = self.exchange_extension(path, extension)
        return path

    def walk_for_build(self, target_directory: str) -> Iterator[tuple[PurePath, PurePath]]:
        """This is :func:`os.walk` for build.
        Returns the path to a file in the specified directory and the path to the output directory when a file of that path is built."""
        if exists(target_directory):
            for current_, _, raw_paths in walk(target_directory):
                current_output = PurePath(self.manager.config.output_folder)
                try:
                    (current := PurePath(current_)).parts[1]
                except IndexError:
                    ...
                else:
                    current_output = current_output.joinpath(*current.parts[1:])
                # ファイルのパスを返す。
                for raw_path in raw_paths:
                    yield current.joinpath(raw_path), current_output
                self.manager.dispatch("on_after_build_directory", current_output)

    def mkdir_if_not_exists(self, path: PurePath | None) -> None:
        """If there is no folder with the specified path, create one.

        Args:
            path: The path."""
        if path is not None:
            if not exists(path):
                mkdir(path)

    def remove(self, path: PurePath) -> None:
        """Deletes the file at the specified path and then attempts to delete the folder in which the file resided.

        Args:
            path: The path of the file."""
        remove(path)
        try:
            rmdir(path.parent)
        except (FileNotFoundError, OSError):
            ...

    def rmdir(self, path: PurePath) -> None:
        """Delete the directory.

        Args:
            path: The path of the directory."""
        if exists(path):
            rmtree(path)

    def remove_local_folder_path(self, path: PurePath) -> PurePath:
        """Delete the local folder portion from the path passed.
        For example, if the path is ``inputs/profile.md``, the path ``profile.md`` is returned.
        The path passed must be relative.

        Args:
            path: The path."""
        return PurePath().joinpath(*path.parts[1:])


def enum(path: PurePath) -> Iterator[PurePath]:
    """Enumerates the paths to files in the specified directory.

    Args:
        path: The path to the directory."""
    return map(path.joinpath, listdir(path))


LiT = TypeVar("LiT", bound=Callable)
class EventTools:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.listeners = defaultdict[str, list[Callable]](list)

    def add_listener(self, listener: Callable, name: str | None = None) -> None:
        """Add an event listener.

        Args:
            listener: Event listener function.
            name: The name of the event.
                If ``None``, the function name is used."""
        self.listeners[name or listener.__name__].append(listener)

    def remove_listener(self, target: Callable | str) -> None:
        """Delete event listener.

        Args:
            target: The name of the event listener function or event."""
        if isinstance(target, str):
            if target in self.listeners:
                del self.listeners[target]
        else:
            for listeners in self.listeners.values():
                if target in listeners:
                    listeners.remove(target)
                    break

    def listen(self, name: str | None = None) -> Callable[[LiT], LiT]:
        """Decorator for registering event listeners.
        It uses :meth:`EventTools.add_listener`.

        Args:
            name: The name of the event.
                If ``None``, the function name is used."""
        def decorator(func: LiT) -> LiT:
            self.add_listener(func, name)
            return func
        return decorator

    def dispatch(
        self, event_name: str, /, *args: Any,
        collect_return_value: bool = False,
        **kwargs: Any
    ) -> Sequence[Any]:
        """Execute event listeners.

        Args:
            event_name: The name of the event.
            *args: Arguments to be passed to event listeners.
            collect_return_value: Whether to collect the return value of the event listener.
            **kwargs: Keyword arguments to be passed to event listeners."""
        return_values: list[Any] | None = [] if collect_return_value else None
        for listener in self.listeners[event_name]:
            result = listener(*args, **kwargs)
            if collect_return_value:
                return_values.append(result) # type: ignore
        return return_values or ()