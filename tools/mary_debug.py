from tkinter import Toplevel, Button, Text, Label
from subprocess import Popen, PIPE
from functools import wraps
import logging
from tools.constants import Constants
from sys import exit
from threading import Thread


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
        self.focus_force()
        self.grab_set()

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


class ThreadedLocalMapFactory(Thread):
    def __init__(self, file_path, q):
        super().__init__(daemon=True)
        self.q = q
        self.file_path = file_path

    def run(self):
        from tools.local import LocalMap
        mp = LocalMap(self.file_path)
        self.q.put(mp)


# def show_progressbar(func):
#     """
#     This decorator gets applied to functions run by run_long_task() in a separate thread.
#     The function return is stored in a global dictionary, so it later can be accessed
#     from the Tkinter UI.
#     Tkinter UI does not allow threads within itself and must function independently
#     of the backend.
#     """
#
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         pb = MaryProgressBar()
#         pb.start()
#         q.put(func(*args, **kwargs))
#         pb.stopandhide()
#
#     return wrapper


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
