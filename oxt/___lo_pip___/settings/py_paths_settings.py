from __future__ import annotations
from typing import cast, Tuple, Set

from .settings import Settings
from ..meta.singleton import Singleton
from ..lo_util.configuration import Configuration, SettingsT
from ..py_paths import PathItems, PathItem


class PyPathsSettings(metaclass=Singleton):
    """Singleton Class. Manages Settings for Python Paths."""

    def __init__(self) -> None:
        settings = Settings()
        self._configuration = Configuration()
        self._py_paths = PathItems(cast(Tuple, settings.current_settings.get("PyPathsList", ())))
        self._py_path_verify = bool(settings.current_settings.get("PyPathVerify", True))
        self._py_path_append = bool(settings.current_settings.get("PyPathAppend", True))
        self._node_value = f"/{settings.lo_implementation_name}.Settings/PyPaths"

    def append(self, pth: str) -> None:
        """Appends a python path to the current python paths."""
        self._py_paths.add_path(pth)

    def remove(self, pth: str) -> None:
        """Removes a python path from the current python paths."""
        self._py_paths.remove_path(pth)

    @property
    def py_paths(self) -> PathItems:
        """Gets/Sets the python paths."""
        return self._py_paths

    @py_paths.setter
    def py_paths(self, value: PathItems) -> None:
        self._configuration.save_configuration_str_lst(
            node_value=self._node_value, name="PyPathsList", value=value.get_as_tuple()
        )
        self._py_paths = value

    @property
    def py_path_verify(self) -> bool:
        """Gets/Sets the python path verification."""
        return self._py_path_verify

    @py_path_verify.setter
    def py_path_verify(self, value: bool) -> None:
        settings: SettingsT = {"names": ("PyPathVerify",), "values": (value,)}
        self._configuration.save_configuration(node_value=self._node_value, settings=settings)
        self._py_path_verify = value

    @property
    def py_path_append(self) -> bool:
        """Gets/Sets the python path append or insert."""
        return self._py_path_append

    @py_path_append.setter
    def py_path_append(self, value: bool) -> None:
        settings: SettingsT = {"names": ("PyPathAppend",), "values": (value,)}
        self._configuration.save_configuration(node_value=self._node_value, settings=settings)
        self._py_path_append = value
