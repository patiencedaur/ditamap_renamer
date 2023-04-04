from functools import wraps
import logging
from tkinter import DISABLED, NORMAL, END

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def debug(func):
    name = func.__qualname__
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug('Running', name)
        return func(*args, **kwargs)
    return wrapper


def debugmethods(cls):
    for k, v in vars(cls).items():
        if callable(v):
            type(v)
            setattr(cls, k, debug(v))
    return cls


class MaryLogHandler(logging.Handler):

    def __init__(self, app: 'App'):
        super().__init__()
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        widget = getattr(app, 'debug_window')
        self.text = getattr(widget, 'text')
        self.text.config(state=DISABLED)

    def emit(self, record):
        self.text.config(state=NORMAL)
        self.text.insert(END, self.format(record) + '\n')
        self.text.see(END)
        self.text.config(state=DISABLED)
