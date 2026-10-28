// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// "Copy page" button next to the h1: copies the page's RsT source, which
// Sphinx publishes under _sources/.

(function () {
    const RESET_DELAY_MS = 2000;

    const page = document.body.dataset.page;
    const root = document.documentElement.dataset.content_root;
    // rendered by layout.html
    const btn = document.querySelector(".article button.copy-page");
    if (!page || !root || !btn) {
        return;
    }
    const url = root + "_sources/" + page + ".rst.txt";

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
})();
