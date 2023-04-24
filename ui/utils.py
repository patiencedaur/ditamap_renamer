from tkinter import Toplevel
from tkinter.ttk import Progressbar


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
