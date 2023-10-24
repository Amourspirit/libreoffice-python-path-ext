from __future__ import annotations
from typing import Any, TYPE_CHECKING, cast, Callable, Set
from pathlib import Path

import uno
import unohelper

from com.sun.star.awt import XActionListener
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.awt import XItemListener
from com.sun.star.ui.dialogs import (
    TemplateDescription,
)  # import FILESAVE_AUTOEXTENSION, FILEOPEN_SIMPLE  # type: ignore

from ...basic_config import BasicConfig
from ...lo_util.resource_resolver import ResourceResolver
from ...lo_util.configuration import Configuration, SettingsT
from ...settings.settings import Settings
from ..file_open_dialog import FileOpenDialog
from ..folder_open_dialog import FolderOpenDialog
from ...oxt_logger import OxtLogger
from ...settings.py_paths import PyPathsSettings
from ..message_dialog import MessageDialog
from com.sun.star.awt.MessageBoxType import INFOBOX, ERRORBOX

if TYPE_CHECKING:
    from com.sun.star.awt import UnoControlDialog  # service
    from com.sun.star.awt import UnoControlButton  # service
    from com.sun.star.awt import UnoControlButtonModel  # service
    from com.sun.star.awt import UnoControlListBox  # service
    from com.sun.star.awt import UnoControlListBoxModel  # service
    from com.sun.star.awt import ItemEvent  # struct


IMPLEMENTATION_NAME = f"{BasicConfig().lo_implementation_name}.PyPathsOptionsPage"


class ItemListener(unohelper.Base, XItemListener):
    """
    Listener class that listens for UNO Item State
    """

    def __init__(self, callback: Callable):
        """
        Inits ItemListener

        Args:
            callback (callable): Callback function that is called
                when item state change is preformed
        """
        self._callback: Callable = callback

    def itemStateChanged(self, aEvent: ItemEvent):
        self._callback()


class ButtonListener(unohelper.Base, XActionListener):
    def __init__(self, cast: "OptionsDialogHandler"):
        self._logger = OxtLogger(log_name=__name__)
        self._logger.debug("ButtonListener.__init__")
        self.cast = cast
        self._logger.debug("ButtonListener.__init__ done")

    def disposing(self, ev: Any):
        pass

    def actionPerformed(self, ev: Any):
        self._logger.debug("ButtonListener.actionPerformed")
        try:
            cmd = str(ev.ActionCommand)
            self._logger.debug(f"ButtonListener.actionPerformed cmd: {cmd}")
            # if cmd == "ChooseEditor":
            #     if ret := self.cast.choose_file():
            #         path = uno.fileUrlToSystemPath(ret)
            #         ev.Source.getContext().getControl("txtTest").setText(path)
            if cmd == "Add":
                self.cast.action_add()
            elif cmd == "AddFile":
                self.cast.action_add_file()
            elif cmd == "Remove":
                self.cast.action_remove()
            elif cmd == "Verify":
                self.cast.action_verify()
        except Exception as err:
            self._logger.error(f"ButtonListener.actionPerformed: {err}", exc_info=True)
            raise err


class OptionsDialogHandler(unohelper.Base, XContainerWindowEventHandler):
    def __init__(self, ctx: Any):
        self._logger = OxtLogger(log_name=__name__)
        self._logger.debug("PyPaths-OptionsDialogHandler.__init__")
        self.ctx = ctx
        self._config = BasicConfig()
        self._resource_resolver = ResourceResolver(self.ctx)
        self._config_node = f"/{self._config.lo_implementation_name}.Settings/Logging"
        self._window_name = "paths"
        self._window: UnoControlDialog | None = None
        self._settings = Settings()
        self._py_settings = PyPathsSettings()
        self._logger.debug("PyPaths-OptionsDialogHandler.__init__ done")

    # region XContainerWindowEventHandler
    def callHandlerMethod(self, window: UnoControlDialog, eventObject: Any, method: str):
        self._logger.debug(f"PyPaths-OptionsDialogHandler.callHandlerMethod: {method}")
        if method == "external_event":
            try:
                self._handle_external_event(window, eventObject)
            except Exception as e:
                print(e)
            return True

    def getSupportedMethodNames(self):
        return ("external_event",)

    # endregion XContainerWindowEventHandler

    def _handle_external_event(self, window: UnoControlDialog, ev_name: str):
        self._logger.debug(f"PyPaths-OptionsDialogHandler._handle_external_event: {ev_name}")
        if ev_name == "ok":
            self._save_data(window)
        elif ev_name == "back":
            self._load_data(window, "back")
        elif ev_name == "initialize":
            self._load_data(window, "initialize")
        return True

    def _save_data(self, window: UnoControlDialog):
        name = cast(str, window.getModel().Name)  # type: ignore
        self._logger.debug(f"PyPaths-OptionsDialogHandler._save_data name: {name}")
        if name != self._window_name:
            return
        data = self._get_list_data(window)
        self._py_settings.py_paths = data

    def _load_data(self, window: UnoControlDialog, ev_name: str):
        # sourcery skip: extract-method
        name = cast(str, window.getModel().Name)  # type: ignore
        self._logger.debug(f"PyPaths-OptionsDialogHandler._load_data name: {name}")
        self._logger.debug(f"PyPaths-OptionsDialogHandler._load_data ev_name: {ev_name}")
        if name != self._window_name:
            return
        self._window = window
        try:
            if ev_name == "initialize":
                listener = ButtonListener(self)
                btn_add = self._get_ctl_add(window)
                btn_add.setActionCommand("Add")
                btn_add.addActionListener(listener)

                btn_add_file = self._get_ctl_add_file(window)
                btn_add_file.setActionCommand("AddFile")
                btn_add_file.addActionListener(listener)

                btn_remove = self._get_ctl_remove(window)
                btn_remove.setActionCommand("Remove")
                btn_remove.addActionListener(listener)
                btn_remove.setEnable(False)

                btn_verify = self._get_ctl_verify(window)
                btn_verify.setActionCommand("Verify")
                btn_verify.addActionListener(listener)
                btn_verify.setEnable(False)

                for control in window.Controls:  # type: ignore
                    if not control.supportsService("com.sun.star.awt.UnoControlListBox"):
                        model = control.Model
                        model.Label = self._resource_resolver.resolve_string(model.Label)
                        if model.getServiceName() == "stardiv.vcl.controlmodel.Button":
                            model.HelpText = self._resource_resolver.resolve_string(model.HelpText)

                self._init_list_data(window)

        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler._load_data: {err}", exc_info=True)
            raise err
        return

    # region update UI
    def _update_ui(self, has_selection: bool) -> None:
        if self.window is None:
            self._logger.debug("PyPaths-OptionsDialogHandler._update_ui: window is None")
            return
        cmd_clt_remove = self._get_ctl_remove(self.window)
        cmd_clt_remove.setEnable(has_selection)

        cmd_ctl_verify = self._get_ctl_verify(self.window)
        cmd_ctl_verify.setEnable(has_selection)

    # endregion update UI

    # region Listbox
    def _init_list_data(self, window: UnoControlDialog):
        lb = self._get_ctl_lst_py_paths(window)
        lb.addItemListener(ItemListener(self._lb_py_paths_item_changed))
        self._refresh_list_data(window)

    def _refresh_list_data(self, window: UnoControlDialog):
        model = self._get_model_lst_py_paths(window)
        model.removeAllItems()
        items = sorted(self._py_settings.py_paths)
        # items = ["Test1", "Test2", "Test3"]
        for i, itm in enumerate(items):
            model.insertItemText(i, itm)

    def _lb_py_paths_item_changed(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler._lb_py_paths_item_changed")
        if self.window is None:
            self._logger.debug("PyPaths-OptionsDialogHandler._lb_py_paths_item_changed: window is None")
            return
        lb = self._get_model_lst_py_paths(self.window)
        if not lb.SelectedItems:
            self._logger.debug("PyPaths-OptionsDialogHandler._lb_py_paths_item_changed: no selection")
            self._update_ui(False)
            return
        self._logger.debug(f"PyPaths-OptionsDialogHandler._lb_py_paths_item_changed: {lb.SelectedItems}")
        self._update_ui(True)

    def _append_list_data(self, window: UnoControlDialog, data: str) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler._append_list_data")
        lb = self._get_model_lst_py_paths(window)
        index = lb.ItemCount
        lb.insertItemText(index, data)

    def _get_list_data(self, window: UnoControlDialog) -> Set[str]:
        lb = self._get_model_lst_py_paths(window)
        return set(lb.getItemText(i) for i in range(lb.ItemCount))

    def _get_selected_item_text(self, window: UnoControlDialog) -> str:
        lb = self._get_model_lst_py_paths(window)
        if not lb.SelectedItems:
            return ""
        return lb.getItemText(cast(int, lb.SelectedItems[0]))

    # endregion Listbox

    # region Actions
    def action_add(self) -> None:
        if not self.window:
            return
        self._logger.debug("PyPaths-OptionsDialogHandler.action_add")
        if ret := self.choose_folder():
            path = uno.fileUrlToSystemPath(ret)
            self._logger.debug(f"PyPaths-OptionsDialogHandler.action_add path: {path}")
            self._append_list_data(self.window, path)

    def action_add_file(self) -> None:
        if not self.window:
            return
        self._logger.debug("PyPaths-OptionsDialogHandler.action_add_file")
        if ret := self.choose_file():
            path = uno.fileUrlToSystemPath(ret)
            self._logger.debug(f"PyPaths-OptionsDialogHandler.action_add_file path: {path}")
            self._append_list_data(self.window, path)

    def action_remove(self) -> None:
        if not self.window:
            return
        self._logger.debug("PyPaths-OptionsDialogHandler.action_remove")
        lb = self._get_model_lst_py_paths(self.window)
        index = cast(int, lb.SelectedItems[0])
        lb.removeItem(index)
        self._update_ui(bool(lb.SelectedItems))

    def action_verify(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler.action_verify")
        if not self.window:
            return
        path = self._get_selected_item_text(self.window)
        if not path:
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=self._resource_resolver.resolve_string("dlg08"),
                title=self._resource_resolver.resolve_string("msg01"),
            )
            msg_box.execute()
            return
        p = Path(path)
        if p.exists():
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=INFOBOX,
                message=self._resource_resolver.resolve_string("dlg06"),
                title=self._resource_resolver.resolve_string("title02"),
            )
            msg_box.execute()
        else:
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=self._resource_resolver.resolve_string("dlg07"),
                title=self._resource_resolver.resolve_string("msg01"),
            )
            msg_box.execute()

    # endregion Actions

    # region Get Controls
    def _get_ctl_add(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdAdd"))

    def _get_ctl_add_file(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdAddFile"))

    def _get_ctl_remove(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdRemove"))

    def _get_ctl_verify(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdVerify"))

    def _get_ctl_lst_py_paths(self, window: UnoControlDialog) -> UnoControlListBox:
        return cast("UnoControlListBox", window.getControl("lstPaths"))

    def _get_model_add(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_add(window).getModel())

    def _get_model_add_file(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_add_file(window).getModel())

    def _get_model_remove(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_remove(window).getModel())

    def _get_model_verify(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_verify(window).getModel())

    def _get_model_lst_py_paths(self, window: UnoControlDialog) -> UnoControlListBoxModel:
        return cast("UnoControlListBoxModel", self._get_ctl_lst_py_paths(window).getModel())

    # endregion Get Controls

    def _config_writer(self, settings: SettingsT):
        try:
            cfg = Configuration()
            cfg.save_configuration(self._config_node, settings)
        except Exception as e:
            raise e

    def choose_file(self):
        """Gets file url from picker dialog or empty string if canceled."""
        self._logger.debug("PyPaths-OptionsDialogHandler.choose_file")
        try:
            return self._get_file_url()
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.choose_file: {err}", exc_info=True)
            raise err

    def choose_folder(self):
        """Gets folder url from folder picker dialog or empty string if canceled."""
        self._logger.debug("PyPaths-OptionsDialogHandler.choose_file")
        try:
            return self._get_folder_url()
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.choose_file: {err}", exc_info=True)
            raise err

    def _get_file_url(self):
        url = FileOpenDialog(
            self.ctx,
            template=TemplateDescription.FILEOPEN_SIMPLE,
            filters=(
                (self._resource_resolver.resolve_string("ex05"), "*.zip"),
                (self._resource_resolver.resolve_string("ex03"), "*.*"),
            ),
        ).execute()
        return url or False

    def _get_folder_url(self) -> str:
        """Gets folder url from folder picker dialog or empty string if canceled."""
        return FolderOpenDialog(self.ctx).execute()

    # region Properties
    @property
    def py_settings(self) -> PyPathsSettings:
        return self._py_settings

    @property
    def window(self) -> UnoControlDialog | None:
        return self._window

    # endregion Properties
