from functools import wraps


def debug(func):
    name = func.__qualname__
    @wraps(func)
    def wrapper(*args, **kwargs):
        print('Running', name)
        return func(*args, **kwargs)
    return wrapper


def debugmethods(cls):
    for k, v in vars(cls).items():
        if callable(v):
            setattr(cls, k, debug(v))
    return cls