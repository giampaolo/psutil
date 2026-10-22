// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Hide TOC bar below 1280px resolution.

(function () {
    const btn = document.getElementById("toc-toggle");
    const toc = document.querySelector(".right-sidebar");
    if (!btn || !toc) {
        return;
    }
    const body = document.body;
    const wide = window.matchMedia("(min-width: 1280px)");

    function close() {
        body.classList.remove("toc-open");
        btn.setAttribute("aria-expanded", "false");
    }

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const open = body.classList.toggle("toc-open");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
    });

    toc.addEventListener("click", (e) => {
        if (e.target.closest("a")) {
            close();
        }
    });

    document.addEventListener("click", (e) => {
        if (body.classList.contains("toc-open") && !toc.contains(e.target)) {
            close();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && body.classList.contains("toc-open")) {
            close();
            btn.focus();
        }
    });

    wide.addEventListener("change", (e) => {
        if (e.matches) {
            close();
        }
    });
})();
