# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Monkey patches that make the docs build faster."""

import gc


class GCTuner:
    THRESHOLD = 50_000

    def __init__(self):
        # The default (700, or 2000 on 3.14+) is too low, the GC ends
        # up eating ~20% of the build. See
        # https://github.com/sphinx-doc/sphinx/pull/14816
        gc.set_threshold(self.THRESHOLD, *gc.get_threshold()[1:])
        self.parallel_read = True

    def on_doctree_read(self, app, doctree):
        # With -j this only gets called in the workers.
        self.parallel_read = False

    def on_env_updated(self, app, env):
        # The env stays around till the end, no point in the GC scanning
        # it over and over. Without -j all the doctrees are still in
        # memory too, and if we froze them they'd never be freed.
        if self.parallel_read:
            gc.collect()
            gc.freeze()


def tune_gc(app):
    gc_tuner = GCTuner()
    app.connect("doctree-read", gc_tuner.on_doctree_read)
    app.connect("env-updated", gc_tuner.on_env_updated)


def setup(app):
    tune_gc(app)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
