from distutils.core import setup
from Cython.Build import cythonize
import os
import pathlib


def all_py():
    fns = []
    cur_dir = pathlib.Path(os.path.curdir).as_posix()
    for filepath, dirnames, filenames in os.walk(r'.'):
        for filename in filenames:
            if os.path.basename(filename).endswith('.py') and '__' not in os.path.basename(filename):
                p = pathlib.Path(os.path.join(filepath, filename)).absolute().as_posix()
                fns.append(os.path.relpath(p, cur_dir))
    return fns


sss = all_py()


setup(
    name='hardware_station_common ',
    ext_modules=cythonize(all_py())
)