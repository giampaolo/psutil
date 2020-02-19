#!/usr/bin/env python3
# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Update news entry of Tidelift with latest HISTORY.rst section.
Put your Tidelift API token in a file first:
~/.tidelift.token
"""

import os
import requests
import psutil
from psutil.tests import import_module_by_path


def upload_relnotes(package, version, text, token):
    url = f"https://api.tidelift.com/external-api/" + \
          f"lifting/pypi/{package}/release-notes/{version}"
    res = requests.put(
        url=url,
        data=text.encode('utf8'),
        headers={"Authorization": f"Bearer: {token}"})
    print(f"{version}: {res.status_code} {res.text}")
    res.raise_for_status()


def main():
    here = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(here, "print_announce.py")
    get_changes = import_module_by_path(path).get_changes
    with open(os.path.expanduser("~/.tidelift.token")) as f:
        token = f.read().strip()
    upload_relnotes('psutil', psutil.__version__, get_changes(), token)


if __name__ == "__main__":
    main()
