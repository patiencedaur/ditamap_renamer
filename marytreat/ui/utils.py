from os import path
from subprocess import Popen, PIPE
from sys import exit
from tkinter import Tk, Toplevel, Label, Text, Button
from tkinter.ttk import Progressbar

from marytreat.core.constants import Constants


def position_window(window: Tk | Toplevel, width=None, height=None, offset_x=0, offset_y=0):
    window.wm_attributes('-alpha', 0)  # hide window

    if not width and not height:
        width = window.winfo_width()
        height = window.winfo_height()

    sc_width = window.winfo_screenwidth()
    sc_height = window.winfo_screenheight()
    x_pos = int(sc_width/2 - width/2)
    y_pos = int(sc_height/2 - height/2)

    window.update_idletasks()

    window.geometry("{}x{}+{}+{}".format(width, height, x_pos + offset_x, y_pos + offset_y))
    window.wm_attributes('-alpha', 1)  # show window


def get_icon():
    """
    :return: path to MaryTreat icon ..\..\marytreat.ico
    """
    path_to_icon = path.join(
        path.dirname(
            path.dirname(
                path.dirname(
                    path.abspath(__file__)))),
        'marytreat.ico')
    return path_to_icon


class MaryProgressBar(Toplevel):

    def __init__(self):
        super().__init__(relief='raised')
        self.title('Please wait...')
        x_pos = int(self.winfo_screenwidth() / 2)
        y_pos = int(self.winfo_screenheight() / 2)
        self.geometry(f'330x80+{x_pos}+{y_pos}')
        self.attributes('-toolwindow', True)
        self.protocol("WM_DELETE_WINDOW", None)
        # self.overrideredirect(True)
        # Label(self, text='Please wait...').pack()
        self.pb = Progressbar(self, orient='horizontal', mode='indeterminate', length='300')
        self.pb.pack(padx=15, pady=15)
        self.withdraw()

    def start(self):
        """
        Jump in the Tkinter event loop.
        """
        self.deiconify()
        self.focus_force()
        self.grab_set()
        self.after(50, self.pb.start)

    def stopandhide(self):
        self.grab_release()
        self.withdraw()


class ErrorDialog(Toplevel):

    def __init__(self, msg):
        super().__init__()
        self.focus_force()
        self.title('Error')
        self.msg = msg

        padding = Constants.PADDING.value

        error_img = Label(self, image="::tk::icons::error")
        error_img.grid(row=0, column=0, **padding, sticky='nsew')

        message_box = Text(self, width=40, height=6)
        message_box.insert(1.0, self.msg)
        message_box.configure(state='disabled')
        message_box.grid(row=0, column=1, columnspan=2, **padding, sticky='nsew')

        continue_btn = Button(self, command=self.destroy, text='Continue')
        continue_btn.grid(row=1, column=0, **padding, sticky='nsew')

        close_btn = Button(self, command=self.copy_and_close, text='Copy and close')
        close_btn.grid(row=1, column=1, **padding, sticky='nsew')

        self.protocol('WM_DELETE_WINDOW', exit)
        self.focus_force()
        self.grab_set()

    def copy_and_close(self):
        sp = Popen(['clip'], stdin=PIPE, stdout=PIPE, encoding='utf-8')  # Windows only
        sp.communicate(str(self.msg))
        self.destroy()
        exit()


