from tkinter import ttk, Tk, Frame, Checkbutton, Text, Scrollbar

from ui.local_ui import LocalTab
from ui.tridionclient_ui import ServerActionsTab
from utils.constants import Constants

padding = Constants.PADDING.value


class TabControl(ttk.Notebook):

    def __init__(self, master):
        super().__init__(master)

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

        self.debug_window = DebugWindow(self)
        self.debug_window.grid(row=1, column=0, **padding, sticky='nsew')


class DebugWindow(Frame):

    def __init__(self, master):
        super().__init__(master)

        toggle = Checkbutton(self, text='Show debug window', command=self.toggle_debug_window)
        toggle.select()
        toggle.grid(row=0, column=0, sticky='w')

        self.text = Text(self, height=8, width=60, wrap='word', state='disabled')
        self.text.grid(row=1, column=0, sticky='w')

        self.scrollbar = Scrollbar(self)
        self.scrollbar.config(command=self.text.yview)
        self.scrollbar.grid(row=1, column=1, sticky='ns')

    def toggle_debug_window(self):
        if self.text.winfo_viewable():
            self.text.grid_remove()
            self.scrollbar.grid_remove()
        else:
            self.text.grid()
            self.scrollbar.grid()
