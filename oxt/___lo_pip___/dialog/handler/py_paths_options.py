from __future__ import annotations
import contextlib
from typing import Any, TYPE_CHECKING, Literal, cast, Callable, Set, Sequence
from pathlib import Path

import uno
import unohelper

from com.sun.star.awt import XActionListener
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.awt import XItemListener
from com.sun.star.beans import PropertyChangeEvent  # struct
from com.sun.star.beans import XPropertyChangeListener
from com.sun.star.ui.dialogs import TemplateDescription
from com.sun.star.awt.MessageBoxType import INFOBOX, ERRORBOX, QUERYBOX
from com.sun.star.awt import MessageBoxButtons
from com.sun.star.awt import MessageBoxResults


from ...basic_config import BasicConfig
from ...config import Config
from ...lo_util.configuration import Configuration, SettingsT
from ...lo_util.link_cpython import LinkCPython
from ...lo_util.resource_resolver import ResourceResolver
from ...oxt_logger import OxtLogger
from ...settings.py_paths_settings import PyPathsSettings
from ...settings.settings import Settings
from ..file_open_dialog import FileOpenDialog
from ..folder_open_dialog import FolderOpenDialog
from ..message_dialog import MessageDialog
from ...py_paths import PathItems

if TYPE_CHECKING:
    from com.sun.star.awt import ItemEvent  # struct
    from com.sun.star.awt import UnoControlButton  # service
    from com.sun.star.awt import UnoControlButtonModel  # service
    from com.sun.star.awt import UnoControlCheckBoxModel
    from com.sun.star.awt import UnoControlDialog  # service
    from com.sun.star.awt import UnoControlListBox  # service
    from com.sun.star.awt import UnoControlListBoxModel  # service


IMPLEMENTATION_NAME = f"{BasicConfig().lo_implementation_name}.PyPathsOptionsPage"


class CheckBoxListener(unohelper.Base, XPropertyChangeListener):
    def __init__(self, handler: "OptionsDialogHandler"):
        self._logger = OxtLogger(log_name=__name__)
        self._logger.debug("CheckBoxListener.__init__")
        self.handler = handler
        self._logger.debug("CheckBoxListener.__init__ done")

    def disposing(self, ev: Any):
        pass

    def propertyChange(self, ev: PropertyChangeEvent):
        self._logger.debug("CheckBoxListener.propertyChange")
        try:
            # state (evn.NewValue) will be 1 for true and 0 for false
            src = cast("UnoControlCheckBoxModel", ev.Source)
            if src.Name == "chkVerify":
                self._logger.debug("CheckBoxListener.propertyChange: chkVerify")
                self.handler.path_verify = self.handler.state_to_bool(cast(int, (ev.NewValue)))
                self._logger.debug(f"CheckBoxListener.propertyChange: chkVerify: {self.handler.path_verify}")
        except Exception as err:
            self._logger.error(f"CheckBoxListener.propertyChange: {err}", exc_info=True)
            raise


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
            if cmd == "Add":
                self.cast.action_add()
            elif cmd == "AddFile":
                self.cast.action_add_file()
            elif cmd == "Remove":
                self.cast.action_remove()
            elif cmd == "Verify":
                self.cast.action_verify()
            elif cmd == "Link":
                self.cast.action_link()
            elif cmd == "Unlink":
                self.cast.action_unlink()
            elif cmd == "Import":
                self.cast.action_import()
            elif cmd == "Export":
                self.cast.action_export()
            elif cmd == "MoveUp":
                self.cast.action_move("up")
            elif cmd == "MoveDown":
                self.cast.action_move("dn")
        except Exception as err:
            self._logger.error(f"ButtonListener.actionPerformed: {err}", exc_info=True)
            raise err


class OptionsDialogHandler(unohelper.Base, XContainerWindowEventHandler):
    def __init__(self, ctx: Any):
        self._logger = OxtLogger(log_name=__name__)
        self._logger.debug("PyPaths-OptionsDialogHandler.__init__")
        self.ctx = ctx
        self._config = Config()
        self._resource_resolver = ResourceResolver(self.ctx)
        self._config_node = f"/{self._config.lo_implementation_name}.Settings/PyPaths"
        self._window_name = "paths"
        self._window: UnoControlDialog | None = None
        self._settings = Settings()
        self._py_settings = PyPathsSettings()
        self._path_verify = True
        self._path_verify_orig = True
        self._btn_link_visible = self._config.is_mac or self._config.is_app_image
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
        if self._py_settings.py_paths != data or self._path_verify_orig != self._path_verify:
            if self._py_settings.py_paths != data:
                self._logger.debug("PyPaths-OptionsDialogHandler._save_data: data changed")
                self._py_settings.py_paths = data
            else:
                self._logger.debug("PyPaths-OptionsDialogHandler._save_data: data not changed")
            if self._path_verify_orig != self._path_verify:
                self._logger.debug(
                    f"PyPaths-OptionsDialogHandler._save_data: path_verify changed: {self._path_verify}"
                )
                self._py_settings.py_path_verify = self._path_verify
            else:
                self._logger.debug("PyPaths-OptionsDialogHandler._save_data: path_verify not changed")
            title = self._resource_resolver.resolve_string("msg09")
            msg = self._resource_resolver.resolve_string("msg10")
            _ = MessageDialog(
                self.ctx,
                window.getPeer(),
                title=title,
                message=msg,
            ).execute()

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
                chk_listener = CheckBoxListener(self)
                btn_listener = ButtonListener(self)
                btn_add = self._get_ctl_add(window)
                btn_add.setActionCommand("Add")
                btn_add.addActionListener(btn_listener)

                btn_add_file = self._get_ctl_add_file(window)
                btn_add_file.setActionCommand("AddFile")
                btn_add_file.addActionListener(btn_listener)

                btn_remove = self._get_ctl_remove(window)
                btn_remove.setActionCommand("Remove")
                btn_remove.addActionListener(btn_listener)
                btn_remove.setEnable(False)

                btn_verify = self._get_ctl_verify(window)
                btn_verify.setActionCommand("Verify")
                btn_verify.addActionListener(btn_listener)
                btn_verify.setEnable(False)

                btn_import = self._get_ctl_import(window)
                btn_import.setActionCommand("Import")
                btn_import.addActionListener(btn_listener)
                btn_import.setEnable(True)

                btn_export = self._get_ctl_export(window)
                btn_export.setActionCommand("Export")
                btn_export.addActionListener(btn_listener)
                btn_export.setEnable(False)

                btn_up = self._get_ctl_move_up(window)
                btn_up.setActionCommand("MoveUp")
                btn_up.addActionListener(btn_listener)
                btn_up.setEnable(False)

                btn_down = self._get_ctl_move_down(window)
                btn_down.setActionCommand("MoveDown")
                btn_down.addActionListener(btn_listener)
                btn_down.setEnable(False)

                if self._btn_link_visible:
                    btn_link = self._get_ctl_link(window)
                    btn_link.setActionCommand("Link")
                    btn_link.addActionListener(btn_listener)
                    btn_link.setEnable(False)

                    btn_link_model = self._get_model_link(window)
                    # btn_link_model.EnableVisible = True
                    btn_link_model.setPropertyValue("EnableVisible", True)

                    btn_unlink = self._get_ctl_unlink(window)
                    btn_unlink.setActionCommand("Unlink")
                    btn_unlink.addActionListener(btn_listener)
                    btn_unlink.setEnable(False)

                    btn_unlink_model = self._get_model_unlink(window)
                    btn_unlink_model.setPropertyValue("EnableVisible", True)

                self._path_verify = self._py_settings.py_path_verify
                self._path_verify_orig = self._path_verify

                ellipse = self._resource_resolver.resolve_string("ellipse")

                el_buttons = {"cmdAdd", "cmdAddFile", "cmdImport", "cmdExport", "cmdLink", "cmdUnlink"}

                for control in window.Controls:  # type: ignore
                    if not control.supportsService("com.sun.star.awt.UnoControlListBox"):
                        model = control.Model
                        if model.Name in el_buttons:
                            model.Label = self._resource_resolver.resolve_string(model.Label) + ellipse
                        else:
                            model.Label = self._resource_resolver.resolve_string(model.Label)
                        if model.getServiceName() == "stardiv.vcl.controlmodel.Button" and model.HelpText:
                            model.HelpText = self._resource_resolver.resolve_string(model.HelpText)
                        if model.Name == "chkVerify":
                            model.State = self.bool_to_state(self.path_verify)
                            model.addPropertyChangeListener("State", chk_listener)

                self._init_list_data(window)
                self._update_ui(False)

        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler._load_data: {err}", exc_info=True)
            raise err
        return

    # region update UI
    def _update_ui(self, has_selection: bool) -> None:
        if self.window is None:
            self._logger.debug("PyPaths-OptionsDialogHandler._update_ui: window is None")
            return
        lb = self._get_model_lst_py_paths(self.window)
        lst_count = lb.ItemCount
        cmd_clt_remove = self._get_ctl_remove(self.window)
        cmd_clt_remove.setEnable(has_selection)

        cmd_ctl_verify = self._get_ctl_verify(self.window)
        cmd_ctl_verify.setEnable(has_selection)

        cmd_ctl_export = self._get_ctl_export(self.window)
        cmd_ctl_export.setEnable(lst_count > 0)

        if has_selection:
            sel_index = self._get_selected_item_index(self.window, lb)
            cmd_ctl_up = self._get_ctl_move_up(self.window)
            cmd_ctl_up.setEnable(lst_count > 1 and sel_index > 0)
            cmd_ctl_dn = self._get_ctl_move_down(self.window)
            cmd_ctl_dn.setEnable(lst_count > 1 and sel_index < lst_count - 1)

        if self._btn_link_visible:
            cmd_ctl_link = self._get_ctl_link(self.window)
            cmd_ctl_unlink = self._get_ctl_unlink(self.window)
            if has_selection:
                pth = Path(self._get_selected_item_text(self.window, lb))
                if pth.exists() and pth.is_dir():
                    cmd_ctl_link.setEnable(True)
                    cmd_ctl_unlink.setEnable(True)
                else:
                    cmd_ctl_link.setEnable(False)
                    cmd_ctl_unlink.setEnable(False)
            else:
                cmd_ctl_link.setEnable(False)
                cmd_ctl_unlink.setEnable(False)

    # endregion update UI

    # region Listbox
    def _init_list_data(self, window: UnoControlDialog):
        lb = self._get_ctl_lst_py_paths(window)
        lb.addItemListener(ItemListener(self._lb_py_paths_item_changed))
        self._refresh_list_data(window)

    def _refresh_list_data(
        self, window: UnoControlDialog, data: PathItems | None = None, lb: UnoControlListBoxModel | None = None
    ):
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        lb.removeAllItems()
        items = self._py_settings.py_paths if data is None else data
        items.sort()
        for i, itm in enumerate(items):
            lb.insertItemText(i, itm.path)

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

    def _append_list_data(self, window: UnoControlDialog, data: str, lb: UnoControlListBoxModel | None = None) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler._append_list_data")
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        index = lb.ItemCount
        lb.insertItemText(index, data)

    def _get_list_data(self, window: UnoControlDialog, lb: UnoControlListBoxModel | None = None) -> PathItems:
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        return PathItems([lb.getItemText(i) for i in range(lb.ItemCount)])

    def _get_list_data_count(self, window: UnoControlDialog, lb: UnoControlListBoxModel | None = None) -> int:
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        return lb.ItemCount

    def _get_selected_item_text(self, window: UnoControlDialog, lb: UnoControlListBoxModel | None = None) -> str:
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        index = self._get_selected_item_index(window, lb)
        if index < 0:
            return ""
        return lb.getItemText(index)

    def _get_selected_item_index(self, window: UnoControlDialog, lb: UnoControlListBoxModel | None = None) -> int:
        if lb is None:
            lb = self._get_model_lst_py_paths(window)
        if not lb.SelectedItems:
            return -1
        return cast(int, lb.SelectedItems[0])

    def _set_selected_index(self, index: int, window: UnoControlDialog) -> None:
        lb = self._get_ctl_lst_py_paths(window)
        if index < 0:
            lb.selectItemPos(0, False)
        else:
            lb.selectItemPos(index, True)

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
            lb = self._get_model_lst_py_paths(self.window)
            self._update_ui(bool(lb.SelectedItems))

    def action_add_file(self) -> None:
        if not self.window:
            return
        self._logger.debug("PyPaths-OptionsDialogHandler.action_add_file")
        if ret := self.choose_file():
            path = uno.fileUrlToSystemPath(ret)
            self._logger.debug(f"PyPaths-OptionsDialogHandler.action_add_file path: {path}")
            self._append_list_data(self.window, path)
            lb = self._get_model_lst_py_paths(self.window)
            self._update_ui(bool(lb.SelectedItems))

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

    def action_link(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler.action_link")
        if not self.window:
            return
        msg_box = MessageDialog(
            ctx=self.ctx,
            parent=self.window.getPeer(),
            type=QUERYBOX,
            message=self._resource_resolver.resolve_string("msg12"),  # overwrite?
            title=self._resource_resolver.resolve_string("msg11"),
            buttons=MessageBoxButtons.BUTTONS_YES_NO_CANCEL,
        )
        result = msg_box.execute()
        if result == MessageBoxResults.CANCEL:
            return
        overwrite = result == MessageBoxResults.YES
        pth = self._get_selected_item_text(self.window)
        self._logger.debug(f"PyPaths-OptionsDialogHandler.action_link: {pth}")
        try:
            link = LinkCPython(pth=pth)
            result = link.link(overwrite=overwrite)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=INFOBOX,
                message=self._resource_resolver.resolve_string("msg21").format(result),
                title=self._resource_resolver.resolve_string("msg11"),
            )
            _ = msg_box.execute()
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.action_link: {err}", exc_info=True)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=self._resource_resolver.resolve_string("msg13"),
                title=self._resource_resolver.resolve_string("msg11"),
            )
            _ = msg_box.execute()

    def action_unlink(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler.action_unlink")
        if not self.window:
            return
        msg_box = MessageDialog(
            ctx=self.ctx,
            parent=self.window.getPeer(),
            type=QUERYBOX,
            message=self._resource_resolver.resolve_string("msg23"),  # overwrite?
            title=self._resource_resolver.resolve_string("msg22"),
            buttons=MessageBoxButtons.BUTTONS_YES_NO_CANCEL,
        )
        result = msg_box.execute()
        if result == MessageBoxResults.CANCEL:
            return
        broken_only = result == MessageBoxResults.YES
        pth = self._get_selected_item_text(self.window)
        self._logger.debug(f"PyPaths-OptionsDialogHandler.action_unlink: {pth}")
        try:
            link = LinkCPython(pth=pth)
            result = link.unlink(broken_only)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=INFOBOX,
                message=self._resource_resolver.resolve_string("msg20").format(result),
                title=self._resource_resolver.resolve_string("msg19"),
            )
            _ = msg_box.execute()
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.action_link: {err}", exc_info=True)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=self._resource_resolver.resolve_string("msg13"),
                title=self._resource_resolver.resolve_string("msg11"),
            )
            _ = msg_box.execute()

    # region Import Export
    def action_import(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler.cmd_import")
        if not self.window:
            return
        try:
            if ret := self.choose_file(file_type="txt"):
                path = uno.fileUrlToSystemPath(ret)
                self._logger.debug(f"PyPaths-OptionsDialogHandler.cmd_import path: {path}")
                pth = Path(path)
                if not pth.exists():
                    msg_box = MessageDialog(
                        ctx=self.ctx,
                        parent=self.window.getPeer(),
                        type=ERRORBOX,
                        message=self._resource_resolver.resolve_string("msg15"),
                        title=self._resource_resolver.resolve_string("msg01"),
                    )
                    _ = msg_box.execute()
                    return
                data: PathItems = PathItems()
                try:
                    with open(pth, "r") as f:
                        for line in f:
                            if line_data := line.strip():
                                data.add_path(line_data)
                except UnicodeDecodeError as err:
                    msg_box = MessageDialog(
                        ctx=self.ctx,
                        parent=self.window.getPeer(),
                        type=ERRORBOX,
                        message=self._resource_resolver.resolve_string("msg16"),
                        title=self._resource_resolver.resolve_string("msg01"),
                    )
                    _ = msg_box.execute()
                    return

                current_data = self._get_list_data(self.window)
                if current_data == data:
                    self._logger.debug("PyPaths-OptionsDialogHandler.cmd_import: data not changed. Nothing to do.")
                    return
                else:
                    if current_data:
                        msg_box = MessageDialog(
                            ctx=self.ctx,
                            parent=self.window.getPeer(),
                            type=QUERYBOX,
                            message=self._resource_resolver.resolve_string("msg18"),
                            title=self._resource_resolver.resolve_string("title03"),
                            buttons=MessageBoxButtons.BUTTONS_YES_NO_CANCEL,
                        )
                        result = msg_box.execute()
                        if result == MessageBoxResults.CANCEL:
                            return
                        if result == MessageBoxResults.YES:
                            data = data.union(current_data)

                self._refresh_list_data(self.window, data)
                lb = self._get_model_lst_py_paths(self.window)
                self._update_ui(bool(lb.SelectedItems))
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.cmd_import: {err}", exc_info=True)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=str(err),
                title=self._resource_resolver.resolve_string("msg01"),
            )
            _ = msg_box.execute()

    def action_export(self) -> None:
        self._logger.debug("PyPaths-OptionsDialogHandler.cmd_export")
        if not self.window:
            return
        try:
            data = self._get_list_data(self.window)
            if not data:
                msg_box = MessageDialog(
                    ctx=self.ctx,
                    parent=self.window.getPeer(),
                    type=ERRORBOX,
                    message=self._resource_resolver.resolve_string("msg17"),
                    title=self._resource_resolver.resolve_string("msg01"),
                )
                _ = msg_box.execute()
                return
            if ret := self.choose_file(file_type="txt", template=TemplateDescription.FILESAVE_AUTOEXTENSION):
                path = uno.fileUrlToSystemPath(ret)
                with open(path, "w") as f:
                    for item in data:
                        f.write(f"{item.path}\n")
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.cmd_export: {err}", exc_info=True)
            msg_box = MessageDialog(
                ctx=self.ctx,
                parent=self.window.getPeer(),
                type=ERRORBOX,
                message=str(err),
                title=self._resource_resolver.resolve_string("msg01"),
            )
            _ = msg_box.execute()

    # endregion Import Export

    def action_move(self, direction: Literal["up", "dn"]) -> None:
        self._logger.debug(f"PyPaths-OptionsDialogHandler.action_move: {direction}")
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
        selected_index = self._get_selected_item_index(self.window)
        if selected_index < 0:
            raise ValueError("PyPaths-OptionsDialogHandler.action_move: selected_index < 0")
        data = self._get_list_data(self.window)
        sel_item = data.find_path_item(path)
        if not sel_item:
            self._logger.debug("PyPaths-OptionsDialogHandler.action_move: item not found")
            return
        if direction == "up":
            data.move_up(sel_item)
        else:
            data.move_down(sel_item)
        self._refresh_list_data(self.window, data)
        self._update_ui(selected_index > 0)
        if direction == "up":
            selected_index -= 1
        else:
            selected_index += 1
        if selected_index > 0:
            self._set_selected_index(selected_index, self.window)
        else:
            self._set_selected_index(0, self.window)

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

    def _get_ctl_import(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdImport"))

    def _get_ctl_export(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdExport"))

    def _get_ctl_link(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdLink"))

    def _get_ctl_unlink(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdUnlink"))

    def _get_ctl_lst_py_paths(self, window: UnoControlDialog) -> UnoControlListBox:
        return cast("UnoControlListBox", window.getControl("lstPaths"))

    def _get_ctl_move_up(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdMoveUp"))

    def _get_ctl_move_down(self, window: UnoControlDialog) -> UnoControlButton:
        return cast("UnoControlButton", window.getControl("cmdMoveDown"))

    def _get_model_add(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_add(window).getModel())

    def _get_model_add_file(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_add_file(window).getModel())

    def _get_model_remove(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_remove(window).getModel())

    def _get_model_verify(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_verify(window).getModel())

    def _get_model_link(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_link(window).getModel())

    def _get_model_unlink(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_unlink(window).getModel())

    def _get_model_lst_py_paths(self, window: UnoControlDialog) -> UnoControlListBoxModel:
        return cast("UnoControlListBoxModel", self._get_ctl_lst_py_paths(window).getModel())

    def _get_model_move_up(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_move_up(window).getModel())

    def _get_model_move_down(self, window: UnoControlDialog) -> UnoControlButtonModel:
        return cast("UnoControlButtonModel", self._get_ctl_move_down(window).getModel())

    # endregion Get Controls

    def _config_writer(self, settings: SettingsT):
        try:
            cfg = Configuration()
            cfg.save_configuration(self._config_node, settings)
        except Exception as e:
            raise e

    def choose_file(self, file_type: str = "zip", template: int = TemplateDescription.FILEOPEN_SIMPLE):
        """
        Gets file url from picker dialog or empty string if canceled.

        Args:
            file_type (str, optional): File type ( zip or txt ). Defaults to "zip".
            template (int, optional): Dialog template. Defaults to TemplateDescription.FILEOPEN_SIMPLE.
        """
        self._logger.debug("PyPaths-OptionsDialogHandler.choose_file")
        try:
            if file_type == "zip":
                return self._get_file_zip(template)
            elif file_type == "txt":
                return self._get_file_txt(template)
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.choose_file: {err}", exc_info=True)
            raise err

    def choose_folder(self):
        """
        Gets folder url from folder picker dialog or empty string if canceled.
        """
        self._logger.debug("PyPaths-OptionsDialogHandler.choose_file")
        try:
            return self._get_folder_url()
        except Exception as err:
            self._logger.error(f"PyPaths-OptionsDialogHandler.choose_file: {err}", exc_info=True)
            raise err

    def _get_file_zip(self, template: int):
        url = FileOpenDialog(
            self.ctx,
            template=template,
            filters=(
                (self._resource_resolver.resolve_string("ex05"), "*.zip"),
                (self._resource_resolver.resolve_string("ex03"), "*.*"),
            ),
        ).execute()
        return url or False

    def _get_file_txt(self, template: int):
        url = FileOpenDialog(
            self.ctx,
            template=template,
            filters=(
                (self._resource_resolver.resolve_string("ex07"), "*.txt"),
                (self._resource_resolver.resolve_string("ex03"), "*.*"),
            ),
        ).execute()
        return url or False

    def _get_folder_url(self) -> str:
        """Gets folder url from folder picker dialog or empty string if canceled."""
        return FolderOpenDialog(self.ctx).execute()

    def state_to_bool(self, state: int) -> bool:
        return bool(state)

    def bool_to_state(self, value: bool) -> int:
        return int(value)

    # region Properties
    @property
    def py_settings(self) -> PyPathsSettings:
        return self._py_settings

    @property
    def window(self) -> UnoControlDialog | None:
        return self._window

    @property
    def path_verify(self) -> bool:
        return self._path_verify

    @path_verify.setter
    def path_verify(self, value: bool) -> None:
        self._path_verify = value

    # endregion Properties
