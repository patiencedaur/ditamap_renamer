from tkinter import ttk, Tk
import os
from marytreat.core.constants import Constants
from marytreat.ui.local_ui import LocalTab
from marytreat.ui.tridionclient_ui import ServerActionsTab

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
        self.title('MaryTreat - HP Indigo Smart Content DITA Manager')
        path_to_icon = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__)))),
            'marytreat.ico')  # ..\..\marytreat.ico
        self.iconbitmap(path_to_icon)

        tab_control = TabControl(self)
        tab_control.grid(row=0, column=0, sticky='nsew')
