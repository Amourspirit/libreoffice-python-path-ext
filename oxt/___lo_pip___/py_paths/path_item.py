from __future__ import annotations


class PathItem:
    """Represents a path item."""

    def __init__(self, pth: str, sort_order: int) -> None:
        self._path = pth
        self._sort_order = sort_order

    @property
    def path(self) -> str:
        """Gets/Sets the path."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._path = value

    @property
    def sort_order(self) -> int:
        """Gets/Sets the sort order."""
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: int) -> None:
        self._sort_order = value
