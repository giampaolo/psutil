#!/usr/bin/env python
# psutil.py

"""A module providing convenience functions for managing processes 
in a portable way by using Python.

Example usages:

>>> import psutil
>>> psutil.list_processes()
[0, 4, 1108, 1180, 1208, 1252, 1264, 1432, 1444, 1528, 1968, 2000, 220, 296, 780
, 892, 1184, 1516, 1896, 436, 852, 828, 2056, 2276, 2300, 2320, 3796, 2964, 820,
 3672, 3004, 4048, 1140, 1844, 2720, 3664, 2628, 3288, 1092, 3564]
>>> psutil.get_process_path(2720)
u'C:\\Programmi\\xchat\\xchat.exe'
>>> psutil.kill_process_by_name('xchat')
>>>
"""

import sys


__all__ = []

# this follows the same behavior of os.py

_names = sys.builtin_module_names

if 'posix' in _names:
    from _posix import *
    import _posix
    __all__.extend(_posix.__all__)
    del posix   
elif 'nt' in _names:
    from _win32 import *
    import _win32
    __all__.extend(_win32.__all__)
    del _win32
else:
    raise ImportError, 'no os specific module found'
