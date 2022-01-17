__author__ = 'elton'

from functools import wraps

def retries_it(max_try=2):
    def retries_this_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            retries = 0
            while retries <= max_try:
                try:
                    return func(*args, **kwargs)
                except:
                    if retries == max_try:
                        raise
                finally:
                    retries += 1
        return wrapped_function
    return retries_this_decorator
