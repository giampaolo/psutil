#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Nicely print wheels print in dist/ directory."""

import collections
import glob
import os

from psutil._common import print_color
from psutil._common import bytes2human


def main():
    def is64bit(name):
        return name.endswith(('x86_64.whl', 'amd64.whl'))

    groups = collections.defaultdict(list)
    for path in glob.glob('dist/*.whl'):
        name = os.path.basename(path)
        plat = name.split('-')[-1]
        pyimpl = name.split('-')[3]
        ispypy = 'pypy' in pyimpl
        if 'linux' in plat:
            if ispypy:
                groups['pypy_on_linux'].append(name)
            else:
                groups['linux'].append(name)
        elif 'win' in plat:
            if ispypy:
                groups['pypy_on_windows'].append(name)
            else:
                groups['windows'].append(name)
        elif 'macosx' in plat:
            if ispypy:
                groups['pypy_on_macos'].append(name)
            else:
                groups['macos'].append(name)
        else:
            assert 0, name

    totsize = 0
    templ = "%-54s %7s %7s %7s"
    for platf, names in groups.items():
        ppn = "%s (total = %s)" % (platf.replace('_', ' '), len(names))
        s = templ % (ppn, "size", "arch", "pyver")
        print_color('\n' + s, color=None, bold=True)
        for name in sorted(names):
            path = os.path.join('dist', name)
            size = os.path.getsize(path)
            totsize += size
            arch = '64' if is64bit(name) else '32'
            pyver = 'pypy' if name.split('-')[3].startswith('pypy') else 'py'
            pyver += name.split('-')[2][2:]
            s = templ % (name, bytes2human(size), arch, pyver)
            if 'pypy' in pyver:
                print_color(s, color='violet')
            else:
                print_color(s, color='brown')


if __name__ == '__main__':
    main()
