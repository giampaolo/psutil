// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Blog comments, backed by giscus + GitHub Discussions.

(function () {
    const container = document.querySelector(".giscus");
    if (!container) {
        return;
    }

    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    const attrs = {
        "data-repo": container.dataset.repo,
        "data-repo-id": container.dataset.repoId,
        "data-category": container.dataset.category,
        "data-category-id": container.dataset.categoryId,
        // Key threads by source file path, not URL. See comments.html.
        "data-mapping": "specific",
        "data-term": container.dataset.term,
        // Without this giscus falls back to a fuzzy title search and
        // takes the last match with no exact check. Our terms share
        // a "blog/<year>/" prefix, so that's a real collision risk.
        "data-strict": "1",
        "data-reactions-enabled": "1",
        "data-emit-metadata": "0",
        "data-input-position": "top",
        "data-theme": dark ? "dark" : "light",
        "data-lang": "en",
        "data-loading": "lazy"
    };

    const section = container.closest(".comments");
    const script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.crossOrigin = "anonymous";
    script.async = true;
    Object.keys(attrs).forEach((name) => {
        script.setAttribute(name, attrs[name]);
    });
    // A blocked script (DNS, firewall, ad blocker) fires "error", not
    // "load", so the section stays hidden instead of showing an empty
    // widget.
    script.addEventListener("load", () => {
        if (section) {
            section.removeAttribute("hidden");
        }
    });
    container.appendChild(script);
})();
