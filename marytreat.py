from tkinter import *
from tkinter import ttk
from local_ui import LocalTab
from tridionclient_ui import ServerActionsTab
from constants import Constants

padding = Constants.PADDING.value


class TabControl(ttk.Notebook):

    def __init__(self, master):
        super().__init__(master)

        local_tab = LocalTab(self)
        client_tab = ServerActionsTab(self)
        self.add(local_tab, text='Local', sticky=NSEW)
        self.add(client_tab, text='Server', sticky=NSEW)


class DebugWindow(Frame):

    def __init__(self, master):
        super().__init__(master)

        toggle = Checkbutton(self, text='Show debug window', command=self.toggle_debug_window)
        toggle.select()
        toggle.grid(row=0, column=0, sticky=W)

        self.text = Text(self, height=8, width=64, wrap='word', state=DISABLED)
        self.text.grid(row=1, column=0, sticky=W)

    def toggle_debug_window(self):
        if self.text.winfo_viewable():
            self.text.grid_remove()
        else:
            self.text.grid()


class App(Tk):

    def __init__(self):
        super().__init__()
        self.title('MaryTreat - HP Indigo Smart Content DITA Manager')

        tab_control = TabControl(self)
        tab_control.grid(row=0, column=0, sticky=NSEW)

        debug_window = DebugWindow(self)
        debug_window.grid(row=1, column=0, **padding, sticky=NSEW)


if __name__ == '__main__':
    app = App()
    app.mainloop()
