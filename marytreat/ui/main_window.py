import tkinter
from tkinter import ttk, Tk
import os
from marytreat.core.constants import Constants
from marytreat.ui.local_ui import LocalTab
from marytreat.ui.tridionclient_ui import ServerActionsTab
from marytreat.ui.utils import get_icon, position_window

padding = Constants.PADDING.value


class TabControl(ttk.Notebook):

    def __init__(self, master):
        super().__init__(master)
        self.enable_traversal()

        local_tab = LocalTab(self)
        client_tab = ServerActionsTab(self)
        self.add(local_tab, text='Local', sticky='nsew')
        self.add(client_tab, text='Server', sticky='nsew')


class App(Tk):

    def __init__(self):
        super().__init__()
        self.title('MaryTreat Indigo - Smart Content DITA Manager')
        self.iconbitmap(get_icon())

        tab_control = TabControl(self)
        tab_control.grid(row=0, column=0, sticky='nsew')

        position_window(self, 515, 290)
        self.resizable = False
        self.lift()
