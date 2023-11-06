from __future__ import annotations, unicode_literals
import sys
from ooodev.dialog.msgbox import MsgBox
from ooodev.macro.macro_loader import MacroLoader


def show_paths(*args) -> None:
    with MacroLoader():
        msg = "\n".join(sys.path)
        MsgBox.msgbox(msg, "Python Paths")
