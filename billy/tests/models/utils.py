import os
import contextlib


@contextlib.contextmanager
def cd(path):
    '''Creates the path if it doesn't exist'''
    old_dir = os.getcwd()
    try:
        os.makedirs(path)
    except OSError:
        pass
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)
