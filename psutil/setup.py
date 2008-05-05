import sys
from distutils.core import setup, Extension

# Windows
if sys.platform.lower().startswith("win"):
    # build Windows module
    module1 = Extension('_psutil_mswindows', sources = ['_psutil_mswindows.c'],
                        define_macros=[('_WIN32_WINNT', '0x0500')],
                        libraries=["psapi"])

    setup (name = 'PsutilMswindows',
            version = '1.0',
            description = 'Windows implementation',
            ext_modules = [module1])


# OS X
if sys.platform.lower().startswith("darwin"): 
    # build OS X module
    module2 = Extension('_psutil_osx', sources = ['_psutil_osx.c'],)
    setup (name = 'PsutilOSX',
            version = '1.0',
            description = 'OS X implementation',
            ext_modules = [module2])

if sys.platform.lower().startswith("linux"):
    # build Linux module
    # TODO: no compilation needed here
    pass
