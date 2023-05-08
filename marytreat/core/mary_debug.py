import logging
import os
from functools import wraps
from marytreat.ui.utils import ErrorDialog
import marytreat

"""
Logging
"""


def create_log_file():
    root = os.path.dirname(marytreat.__file__)
    log_folder = os.path.join(root, 'logs')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    log_filename = os.path.join(log_folder, 'marytreat.log')
    if os.path.exists(log_filename):
        with open(log_filename, 'w'):  # clear file contents
            pass
    return log_filename


class MaryLogger(logging.Logger):

    def __init__(self, name):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        log_filename = create_log_file()
        fh = logging.FileHandler(log_filename, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        self.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        self.addHandler(ch)

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
