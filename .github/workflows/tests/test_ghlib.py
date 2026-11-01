# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for ghlib.py. No network is used."""

import io
import urllib.error

import ghlib
import pytest


class TestRequest:
    class _Resp:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def _call(self, result, **kwargs):
        def fake_urlopen(req, timeout=None):
            if isinstance(result, Exception):
                raise result
            return self._Resp(result)

        orig_open = ghlib.urllib.request.urlopen
        ghlib.urllib.request.urlopen = fake_urlopen
        try:
            return ghlib.request("/x", **kwargs)
        finally:
            ghlib.urllib.request.urlopen = orig_open

    def test_returns_body(self):
        assert self._call(b'{"a": 1}') == {"a": 1}
        assert self._call(b"diff", accept="text/x-diff") == "diff"

    def test_error_includes_github_body(self):
        # A bare "HTTP Error 404" hides why GitHub refused.
        err = urllib.error.HTTPError(
            "http://x", 404, "err", {}, io.BytesIO(b"<html>boom</html>")
        )
        try:
            with pytest.raises(ghlib.GitHubError, match="boom"):
                self._call(err)
        finally:
            err.close()


class TestRequestAll:
    def test_follows_pages(self):
        pages = [list(range(100)), [100]]
        paths = []

        def fake_request(path):
            paths.append(path)
            return pages[len(paths) - 1]

        orig_request = ghlib.request
        ghlib.request = fake_request
        try:
            assert ghlib.request_all("/x") == list(range(101))
        finally:
            ghlib.request = orig_request
        assert paths == ["/x?per_page=100&page=1", "/x?per_page=100&page=2"]
