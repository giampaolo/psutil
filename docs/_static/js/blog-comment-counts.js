// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Comment counts on the blog listing.

(function () {
    const list = document.querySelector(".blog-cards[data-comments-repo]");
    if (!list) {
        return;
    }

    const repo = list.dataset.commentsRepo;
    const url = "https://api.github.com/repos/" + repo +
        "/discussions?per_page=100";

    function render(discussions) {
        const counts = new Map();
        for (const disc of discussions) {
            counts.set(disc.title, disc.comments);
        }
        for (const card of list.querySelectorAll(".blog-card[data-docname]")) {
            const num = counts.get(card.dataset.docname);
            if (!num) {
                continue;
            }
            const meta = card.querySelector(".blog-card-meta");
            if (!meta) {
                continue;
            }
            const span = document.createElement("span");
            span.className = "blog-card-comments";
            span.textContent = "\u{1F4AC} " + num;
            span.setAttribute(
                "aria-label",
                num === 1 ? "1 comment" : num + " comments",
            );
            meta.appendChild(span);
        }
    }

    fetch(url, { headers: { Accept: "application/vnd.github+json" } })
        .then((resp) => {
            if (!resp.ok) {
                throw new Error("HTTP " + resp.status);
            }
            return resp.json();
        })
        .then(render)
        .catch((err) => {
            console.warn("could not load blog comment counts:", err);
        });
})();
