# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dump the documented API symbols (functions, classes, methods, ...)
to _static/api-symbols.js at the end of the build. The go-to-symbol
menu (js/api-palette.js) loads it to jump to definitions from any
page.
"""

import json
import pathlib


def dump_symbols(app, exception):
    if exception is not None:
        return
    if app.builder.name not in {"html", "dirhtml"}:
        return
    env = app.env
    entries = []
    for fullname, obj in env.domaindata["py"]["objects"].items():
        if (
            not fullname.startswith("psutil.")
            or obj.objtype == "module"
            or obj.aliased
        ):
            continue
        entries.append({
            "name": fullname.removeprefix("psutil."),
            "type": obj.objtype,
            "uri": app.builder.get_target_uri(obj.docname),
            "anchor": obj.node_id,
        })
    outdir = pathlib.Path(app.outdir) / "_static"
    outdir.mkdir(parents=True, exist_ok=True)
    js = "window.PSUTIL_API_SYMBOLS = " + json.dumps(entries) + ";\n"
    (outdir / "api-symbols.js").write_text(js, encoding="utf-8")


def setup(app):
    app.connect("build-finished", dump_symbols)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
