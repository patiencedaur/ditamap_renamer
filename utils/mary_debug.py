from tkinter import Toplevel, Tk, Button, Text, Label
from tkinter.ttk import Progressbar
from subprocess import Popen, PIPE
from functools import wraps
import logging
from utils.constants import Constants
from sys import exit
from queue import Queue


"""
Logging
"""


class ErrorDialog(Toplevel):

    def __init__(self, msg):
        super().__init__()
        self.focus_force()
        self.title('Error')
        self.msg = msg

        padding = Constants.PADDING.value

        error_img = Label(self, image = "::tk::icons::error")
        error_img.grid(row=0, column=0, **padding, sticky='nsew')

        message_box = Text(self, width=40, height=6)
        message_box.insert(1.0, self.msg)
        message_box.configure(state='disabled')
        message_box.grid(row=0, column=1, columnspan=2, **padding, sticky='nsew')

        close_btn = Button(self, command=self.copy_and_close, text='Copy and close')
        close_btn.grid(row=1, column=1, **padding, sticky='nsew')

        self.protocol('WM_DELETE_WINDOW', exit)

    def copy_and_close(self):
        sp = Popen(['clip'], stdin=PIPE, stdout=PIPE, encoding='utf-8') # Windows only
        sp.communicate(str(self.msg))
        self.destroy()
        exit()


class MaryLogger(logging.Logger):

    def __init__(self, name):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        log_filename = './logs/marytreat.log'
        with open(log_filename, 'w'): # clear file contents
            pass
        fh = logging.FileHandler(log_filename, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        self.addHandler(fh)

    def error(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, args, **kwargs)
        ErrorDialog(msg)

    def critical(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, args, **kwargs)
        ErrorDialog(msg)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        """
        Delegate an exception call to the underlying logger.
        """
        self.log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)
        ErrorDialog(msg)


logging.setLoggerClass(MaryLogger)
logger = logging.getLogger(__name__)


"""
Threading and progress bar for long-running functions
"""

q = Queue(maxsize=1)
returned_values = {}


def run_long_task():
    """
    Get a task from the queue and run it in a separate thread.
    Store the return value in a global dictionary. Later it can be accessed from the Tkinter UI.
    """
    while True:
        task = q.get()
        if task is None:
            return
        func = task.get('func')
        kwargs = task.get('kwargs')
        returned_values[func.__name__] = func(**kwargs)


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
        self.focus_force()

    def start(self):
        """
        Jump in the Tkinter event loop.
        """
        self.after(50, self.pb.start)


def show_progressbar(func):
    """
    This decorator gets applied to functions run by run_long_task() in a separate thread.
    The function return is stored in a global dictionary, so it later can be accessed
    from the Tkinter UI.
    Tkinter UI does not allow threads within itself and must function independently
    of the backend.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        pb = MaryProgressBar()
        pb.start()
        try:
            retvalue = func(*args, **kwargs)
            return retvalue
        except:
            pb.destroy()

    return wrapper


"""
Auxiliary debugging functions
"""


def debug(func):
    name = func.__qualname__

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug('Running ' + name)
        return func(*args, **kwargs)
    return wrapper


def debugmethods(cls):
    for k, v in vars(cls).items():
        if callable(v):
            type(v)
            setattr(cls, k, debug(v))
    return cls
