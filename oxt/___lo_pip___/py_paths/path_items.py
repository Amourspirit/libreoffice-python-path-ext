from __future__ import annotations
import contextlib
from typing import List, Set, Sequence
from .path_item import PathItem


class PathItems:
    """Represents a collection of path item."""

    def __init__(self, items: Sequence[str] | None = None) -> None:
        self._paths: List[PathItem] = []
        if items:
            for i, pth in enumerate(items):
                self._paths.append(PathItem(pth, i + 1))
        self._iter_index = 0

    def __eq__(self, value: object) -> bool:
        """Returns True if equal to the value."""
        if not isinstance(value, PathItems):
            return False
        return self.get_as_item_set() == value.get_as_item_set()

    def __len__(self) -> int:
        """Returns the length of the collection."""
        return len(self._paths)

    def __iter__(self):
        self._iter_index = 0
        while self._iter_index < len(self):
            yield self._paths[self._iter_index]
            self._iter_index += 1

    def __next__(self):
        if self._iter_index > len(self):
            raise StopIteration
        else:
            self._iter_index += 1
            return self._paths[self._iter_index - 1]

    def __reversed__(self):
        self._iter_index = len(self) - 1
        while self._iter_index >= 0:
            yield self._paths[self._iter_index]
            self._iter_index -= 1

    def add(self, path: PathItem) -> None:
        """Adds a path item to the collection."""
        itm = self.find_path_item(path.path)
        if not itm:
            self._paths.append(path)
            self._update_sort_order()

    def add_path(self, pth: str) -> PathItem:
        """Adds a path item to the collection."""
        itm = self.find_path_item(pth)
        if itm:
            return itm
        else:
            index = len(self._paths) + 1
            pi = PathItem(pth, index)
            self._paths.append(pi)
        return pi

    def remove(self, path: PathItem) -> None:
        """Removes a path item from the collection."""
        with contextlib.suppress(ValueError):
            self._paths.remove(path)
            self._update_sort_order()

    def remove_path(self, pth: str) -> None:
        """Removes a path item from the collection."""
        if not pth:
            return
        for path in self._paths:
            if path.path == pth:
                self._paths.remove(path)
                self._update_sort_order()

    def find_path_item(self, pth: str) -> PathItem | None:
        """Gets a path item from the collection."""
        if not pth:
            return None
        for path in self._paths:
            if path.path == pth:
                return path
        return None

    def sort(self) -> None:
        """Sorts the path items by sort order."""
        self._paths.sort(key=lambda x: x.sort_order)

    def _update_sort_order(self) -> None:
        """Updates the sort order of the path items."""
        for i, path in enumerate(self._paths):
            path.sort_order = i + 1

    def move_up(self, path: PathItem) -> None:
        """Moves a path item up in the sort order."""
        index = self._paths.index(path)
        if index > 0:
            self._paths[index - 1], self._paths[index] = self._paths[index], self._paths[index - 1]
            self._update_sort_order()

    def move_down(self, path: PathItem) -> None:
        """Moves a path item down in the sort order."""
        index = self._paths.index(path)
        if index < len(self._paths) - 1:
            self._paths[index + 1], self._paths[index] = self._paths[index], self._paths[index + 1]
            self._update_sort_order()

    def get_as_path_set(self) -> Set[str]:
        """Gets the path items as a set."""
        return set(p.path for p in self._paths)

    def get_as_item_set(self) -> Set[PathItem]:
        """Gets the path items as a set."""
        return set(path for path in self._paths)

    def get_as_tuple(self) -> tuple[str, ...]:
        """Gets the path items as a tuple."""
        return tuple(path.path for path in self._paths)

    def update_from_set(self, paths: Set[PathItem]) -> None:
        """Updates the path items from a set."""
        self._paths = list(paths)
        self.sort()

    def clone(self) -> PathItems:
        """Clones the path items."""
        return PathItems(self.get_as_tuple())

    def union(self, paths: PathItems) -> PathItems:
        """Returns the union of the path items."""
        items = PathItems(self.get_as_tuple() + paths.get_as_tuple())
        items.remove_duplicates()
        return items

    def clear(self) -> None:
        """Clears the path items."""
        self._paths.clear()

    def remove_duplicates(self) -> None:
        """Removes duplicate path items by path."""
        orig = self.clone()
        found = set()
        self.clear()
        for p in orig:
            if p.path not in found:
                self._paths.append(p)
                found.add(p.path)
        self.sort()
