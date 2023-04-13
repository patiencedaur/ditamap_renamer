from functools import wraps
import logging
from tkinter import DISABLED, NORMAL, END


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(ch)


class DebugWindowLogHandler(logging.StreamHandler):

    def __init__(self, text_widget):
        super().__init__()
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.text = text_widget
        self.text.config(state=DISABLED)
        logger.addHandler(self)

    def emit(self, record):
        def write_record():
            msg = self.format(record)
            self.text.config(state=NORMAL)
            self.text.insert(END, msg + '\n')
            self.text.see(END)
            self.text.config(state=DISABLED)
        self.text.after(100, write_record)


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
