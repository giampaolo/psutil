from distutils.core import setup, Extension
 
module1 = Extension('_psutil_mswindows', sources = ['_psutil_mswindows.c'])
 
setup (name = 'PsutilMswindows',
        version = '1.0',
        description = 'Windows implementation',
        ext_modules = [module1])
