"""
On some systems such as Mac and AppImage (Linux) the python extension suffix does not match the
cpython suffix used by the embedded python interpreter.

This class creates symlinks for all .so files in dest folder that match the current python embedded suffix.

For example a file named ``indexers.cpython-38-x86_64-linux-gnu.so`` would be symlinked to ``indexers.cpython-3.8.so``.
This renaming allows the python interpreter to find the import.
"""
from __future__ import annotations
from typing import List
from pathlib import Path
from importlib import machinery
import logging
from ..config import Config
from ..oxt_logger import OxtLogger


class LinkCPython:
    def __init__(self, pth: str) -> None:
        """
        Constructor

        Args:
            pth (str): Path to site-packages folder.
            overwrite (bool, optional): Override any existing sys links. Defaults to False.
        """
        self._logger = OxtLogger(log_name=__name__)
        self._current_suffix = self._get_current_suffix()
        self._logger.debug("CPythonLink.__init__")
        self._config = Config()
        self._link_root = Path(pth)
        if not self._link_root.exists():
            raise FileNotFoundError(f"Path does not exist {self._link_root}")
        self._logger.debug("CPythonLink.__init__ done")

    def _get_current_suffix(self) -> str:
        """Gets suffix currently used by the embedded python interpreter such as ``cpython-3.8``"""
        for suffix in machinery.EXTENSION_SUFFIXES:
            if suffix.startswith(".cpython-") and suffix.endswith(".so"):
                # remove leading . and trailing .so
                return suffix[1:][:-3]
        return ""

    def _get_all_files(self, path: Path) -> List[Path]:
        return [p for p in path.glob(f"**/*{self.file_suffix}.so") if p.is_file()]

    def _get_all_links(self, path: Path) -> List[Path]:
        return [p for p in path.glob(f"**/*{self.current_suffix}.so") if p.is_symlink()]

    def _create_symlink(self, src: Path, dst: Path, overwrite: bool) -> bool:
        log = self._config.log_level <= logging.DEBUG
        if dst.is_symlink():
            if overwrite:
                if log:
                    self._logger.debug(f"Removing existing symlink {dst}")
                dst.unlink()
            else:
                if log:
                    self._logger.debug(f"Symlink already exists {dst}")
                return False
        dst.symlink_to(src)
        if log:
            self._logger.debug(f"Created symlink {dst} -> {src}")
        return True

    def _find_current_installed_suffix(self, path: Path) -> str:
        """
        Finds the current suffix from the current installed python so files such as ``cpython-38-x86_64-linux-gnu``.

        Args:
            path (Path): Path to search in. Usually site-packages.

        Returns:
            str: suffix if found, otherwise empty string.
        """
        return next(
            (str(p).rsplit(".", 2)[1] for p in path.glob("**/*.cpython-*.so") if not p.is_symlink()),
            "",
        )

    def link(self, overwrite: bool = False) -> int:
        """
        Creates symlinks for all .so files in site-packages that match the current suffix.

        Args:
            overwrite (bool, optional): Override any existing sys links. Defaults to False.

        Returns:
            int: Number of symlinks created.
        """
        count = 0
        self._logger.debug("CPythonLink.link starting")
        if not self._link_root:
            self._logger.debug("No site-packages found")
            return count
        if not self.file_suffix:
            self._logger.debug("No current file suffix found")
            return count
        if not self._link_root.exists():
            self._logger.debug(f"Site-packages does not exist {self._link_root}")
            return count
        self._logger.debug(f"Python current suffix: {self._current_suffix}")
        self._logger.debug(f"Found file suffix: {self.file_suffix}")
        files = self._get_all_files(self._link_root)
        if not files:
            self._logger.debug(f"No files found in {self._link_root}")
            return count
        cp_old = self.file_suffix
        cp_new = self._current_suffix
        if cp_old == cp_new:
            self._logger.debug(f"Suffixes match, no need to link: {cp_old} == {cp_new}")
            return count

        for file in files:
            ln_name = file.name.replace(cp_old, cp_new)
            src = file
            if not src.is_absolute():
                src = file.resolve()
            dst = src.parent / ln_name
            if self._create_symlink(src, dst, overwrite):
                count += 1
        self._logger.debug(f"Created {count} symlinks")
        return count

    def unlink(self, broken_only: bool = True) -> int:
        """
        Unlinks remove symbolic links.

        Args:
            broken_only (bool, optional): Specifies if only broken links are removed. Defaults to True.

        Returns:
            int: Number of links removed.
        """
        links = self._get_all_links(self._link_root)
        count = 0
        if not links:
            self._logger.debug(f"No links found in {self._link_root}")
            return count
        for link in links:
            if broken_only:
                if not link.exists():
                    self._logger.debug(f"Removing broken symlink {link}")
                    link.unlink()
                    count += 1
            else:
                link.unlink()
                count += 1
        if broken_only:
            self._logger.debug(f"Removed {count} broken symlinks")
        else:
            self._logger.debug(f"Removed {count} symlinks")
        return count

    # region Properties
    @property
    def cpy_name(self) -> str:
        """Gets/Sets CPython name, e.g. cpython-3.8"""
        return self._current_suffix

    @cpy_name.setter
    def cpy_name(self, value: str) -> None:
        self._current_suffix = value

    @property
    def overwrite(self) -> bool:
        """Gets/Sets if existing symlinks should be overwritten"""
        return self._overwrite

    @overwrite.setter
    def overwrite(self, value: bool) -> None:
        self._overwrite = value

    @property
    def current_suffix(self) -> str:
        """Current Suffix such as ``cpython-3.8``"""
        return self._current_suffix

    @property
    def file_suffix(self) -> str:
        """Current Suffix such as ``cpython-38-x86_64-linux-gnu``"""
        try:
            return self._file_suffix
        except AttributeError:
            self._file_suffix = self._find_current_installed_suffix(self._link_root)
            return self._file_suffix

    # endregion Properties
