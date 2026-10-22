#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Purge psutil installation by removing psutil-related files and
directories found in site-packages directories. This is needed mainly
because sometimes "import psutil" imports a leftover installation
from site-packages directory instead of the main working directory.
"""

import os
import shutil
import site

PKGNAME = "psutil"

locations = [site.getusersitepackages()] + site.getsitepackages()


def rmpath(path):
    if os.path.isdir(path):
        print("rmdir " + path)
        shutil.rmtree(path)
    else:
        print("rm " + path)
        os.remove(path)


def purge():
    for root in locations:
        if os.path.isdir(root):
            for name in os.listdir(root):
                if PKGNAME in name:
                    abspath = os.path.join(root, name)
                    rmpath(abspath)


def purge_windows():
    r"""Uninstalling psutil on Windows is more tricky. On "import
    psutil" tests may import a psutil version living in
    C:\PythonXY\Lib\site-packages which is not what we want, so other
    than "pip uninstall psutil" we also manually remove stuff from
    site-packages dirs.
    """
    for dir in locations:
        for name in os.listdir(dir):
            path = os.path.join(dir, name)
            if name.startswith(PKGNAME):
                rmpath(path)
            elif name == 'easy-install.pth':
                # easy_install can add a line (installation path) into
                # easy-install.pth; that line alters sys.path.
                path = os.path.join(dir, name)
                with open(path) as f:
                    lines = f.readlines()
                    hasit = False
                    for line in lines:
                        if PKGNAME in line:
                            hasit = True
                            break
                if hasit:
                    with open(path, "w") as f:
                        for line in lines:
                            if PKGNAME not in line:
                                f.write(line)
                            else:
                                print(f"removed line {line!r} from {path!r}")


def main():
    purge()
    if os.name == "nt":
        purge_windows()


if __name__ == "__main__":
    main()
