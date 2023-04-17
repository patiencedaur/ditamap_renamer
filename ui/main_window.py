from tkinter import ttk, Tk
from ui.local_ui import LocalTab
from ui.tridionclient_ui import ServerActionsTab
from utils.constants import Constants

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

        tab_control = TabControl(self)
        tab_control.grid(row=0, column=0, sticky='nsew')
