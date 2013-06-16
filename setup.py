#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
import os
import shutil
import fnmatch
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension


def clean():
    """'python setup.py clean' custom command."""
    def rglob(path, pattern):
        return [os.path.join(dirpath, f)
            for dirpath, dirnames, files in os.walk(path)
            for f in fnmatch.filter(files, pattern)]

    for dirname in ('build', 'dist'):
        if os.path.isdir(dirname):
            sys.stdout.write('removing directory: %s\n' % dirname)
            shutil.rmtree(dirname)

    for dirpath, dirnames, files in os.walk('.'):
        if dirpath.endswith(('__pycache__', '.egg-info')):
            sys.stdout.write('removing directory %s\n' % dirpath)
            shutil.rmtree(dirpath)

    for pattern in ['*.py[co]', '*.s[ol]', '*~', '*.orig', '*.rej', '*.swp']:
        for x in rglob('.', pattern):
           sys.stdout.write('removing file %s\n' % x)
           os.remove(x)

def get_version():
    INIT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           'psutil', '__init__.py'))
    f = open(INIT, 'r')
    try:
        for line in f:
            if line.startswith('__version__'):
                ret = eval(line.strip().split(' = ')[1])
                assert ret.count('.') == 2, ret
                for num in ret.split('.'):
                    assert num.isdigit(), ret
                return ret
        else:
            raise ValueError("couldn't find version string")
    finally:
        f.close()

def get_description():
    README = os.path.abspath(os.path.join(os.path.dirname(__file__), 'README'))
    f = open(README, 'r')
    try:
        return f.read()
    finally:
        f.close()

VERSION = get_version()


# POSIX
if os.name == 'posix':
    posix_extension = Extension('_psutil_posix',
                                sources = ['psutil/_psutil_posix.c'])
# Windows
if sys.platform.startswith("win32"):

    def get_winver():
        maj, min = sys.getwindowsversion()[0:2]
        return '0x0%s' % ((maj * 100) + min)

    extensions = [Extension('_psutil_mswindows',
                            sources=['psutil/_psutil_mswindows.c',
                                     'psutil/_psutil_common.c',
                                     'psutil/arch/mswindows/process_info.c',
                                     'psutil/arch/mswindows/process_handles.c',
                                     'psutil/arch/mswindows/security.c'],
                            define_macros=[('_WIN32_WINNT', get_winver()),
                                           ('_AVAIL_WINVER_', get_winver())],
                            libraries=["psapi", "kernel32", "advapi32",
                                       "shell32", "netapi32", "iphlpapi",
                                       "wtsapi32"],
                            #extra_compile_args=["/Z7"],
                            #extra_link_args=["/DEBUG"]
                            )]
# OS X
elif sys.platform.startswith("darwin"):
    extensions = [Extension('_psutil_osx',
                            sources = ['psutil/_psutil_osx.c',
                                       'psutil/_psutil_common.c',
                                       'psutil/arch/osx/process_info.c'],
                            extra_link_args=['-framework', 'CoreFoundation',
                                             '-framework', 'IOKit']
                            ),
                  posix_extension]
# FreeBSD
elif sys.platform.startswith("freebsd"):
    extensions = [Extension('_psutil_bsd',
                            sources = ['psutil/_psutil_bsd.c',
                                       'psutil/_psutil_common.c',
                                       'psutil/arch/bsd/process_info.c'],
                            libraries=["devstat"],
                            ),
                  posix_extension]
# Linux
elif sys.platform.startswith("linux"):
    extensions = [Extension('_psutil_linux',
                            sources=['psutil/_psutil_linux.c'],
                            ),
                  posix_extension]
# Solaris
elif sys.platform.lower().startswith('sunos'):
    extensions = [Extension('_psutil_sunos',
                            sources=['psutil/_psutil_sunos.c'],
                            libraries=['kstat', 'nsl'],
                            ),
                  posix_extension]
else:
    sys.exit('platform %s is not supported' % sys.platform)


def main():
    # "python setup.py clean" custom command
    if len(sys.argv) > 1 and sys.argv[1] == 'clean':
        return clean()

    setup_args = dict(
        name='psutil',
        version=VERSION,
        download_url="http://psutil.googlecode.com/files/psutil-%s.tar.gz" \
                     % VERSION,
        description='A process and system utilities module for Python',
        long_description=get_description(),
        keywords=['ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice',
                  'tty', 'ionice', 'uptime', 'taskmgr', 'process', 'df',
                  'iotop', 'iostat', 'ifconfig', 'taskset', 'who', 'pidof',
                  'pmap', 'smem', 'monitoring',],
        author='Giampaolo Rodola',
        author_email='psutil@googlegroups.com',
        maintainer='Giampaolo Rodola',
        maintainer_email='g.rodola <at> gmail <dot> com',
        url='http://code.google.com/p/psutil/',
        platforms='Platform Independent',
        license='License :: OSI Approved :: BSD License',
        packages=['psutil'],
        test_suite='test.test_psutil',
        # see: python setup.py register --list-classifiers
        classifiers=[
              'Development Status :: 5 - Production/Stable',
              'Environment :: Console',
              'Operating System :: MacOS :: MacOS X',
              'Operating System :: Microsoft',
              'Operating System :: Microsoft :: Windows :: Windows NT/2000',
              'Operating System :: POSIX',
              'Operating System :: POSIX :: Linux',
              'Operating System :: POSIX :: BSD :: FreeBSD',
              'Operating System :: POSIX :: SunOS/Solaris',
              'Operating System :: OS Independent',
              'Programming Language :: C',
              'Programming Language :: Python',
              'Programming Language :: Python :: 2',
              'Programming Language :: Python :: 2.4',
              'Programming Language :: Python :: 2.5',
              'Programming Language :: Python :: 2.6',
              'Programming Language :: Python :: 2.7',
              'Programming Language :: Python :: 3',
              'Programming Language :: Python :: 3.0',
              'Programming Language :: Python :: 3.1',
              'Programming Language :: Python :: 3.2',
              'Programming Language :: Python :: 3.3',
              'Topic :: System :: Monitoring',
              'Topic :: System :: Networking',
              'Topic :: System :: Networking :: Monitoring',
              'Topic :: System :: Benchmark',
              'Topic :: System :: Hardware',
              'Topic :: System :: Systems Administration',
              'Topic :: Utilities',
              'Topic :: Software Development :: Libraries',
              'Topic :: Software Development :: Libraries :: Python Modules',
              'Intended Audience :: Developers',
              'Intended Audience :: System Administrators',
              'License :: OSI Approved :: BSD License',
              ],
        )
    if extensions is not None:
        setup_args["ext_modules"] = extensions
    setup(**setup_args)

if __name__ == '__main__':
    main()
