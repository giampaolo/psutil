// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// "Copy page" button next to the h1: copies the page's RsT source, which
// Sphinx publishes under _sources/.

(function () {
    const RESET_DELAY_MS = 2000;

    const ICONS = `
<svg class="copy-page-icon-copy" viewBox="0 0 24 24" width="12" height="12"
     fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true">
  <rect x="9" y="9" width="13" height="13" rx="2"></rect>
  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
</svg>
<svg class="copy-page-icon-check" viewBox="0 0 24 24" width="12" height="12"
     fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true">
  <path d="M4 12.5l5.5 5.5L20 6"></path>
</svg>`;

    const SKIP = ["index", "404", "blog"];

    const page = document.body.dataset.page;
    const root = document.documentElement.dataset.content_root;
    if (!page || !root || SKIP.includes(page)) {
        return;
    }
    const h1 = document.querySelector(".article h1");
    if (!h1) {
        return;
    }

    const url = root + "_sources/" + page + ".rst.txt";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-page";
    btn.title = "Copy this page as reStructuredText";
    btn.innerHTML = '<span class="copy-page-icons">' + ICONS + "</span>" +
        '<span class="copy-page-labels">' +
        '<span class="copy-page-label-copy">Copy page</span>' +
        '<span class="copy-page-label-done">Copied</span>' +
        "</span>";

    let busy = false;

    function flash(state) {
        btn.classList.add(state);
        setTimeout(() => {
            btn.classList.remove(state);
            busy = false;
        }, RESET_DELAY_MS);
    }

    btn.addEventListener("click", function () {
        if (busy) {
            return;
        }
        busy = true;
        fetch(url)
            .then((resp) => {
                if (!resp.ok) {
                    throw new Error(url + " returned " + resp.status);
                }
                return resp.text();
            })
            .then((text) => navigator.clipboard.writeText(text))
            .then(() => flash("copied"))
            .catch((err) => {
                console.warn("copy-page: " + err.message);
                flash("failed");
            });
    });

    // Only offer it when the source is actually published; generated
    // pages (genindex, search, blog archives) have none.
    fetch(url, { method: "HEAD" })
        .then((resp) => {
            if (resp.ok) {
                h1.appendChild(btn);
            }
        })
        .catch(() => {});
})();
