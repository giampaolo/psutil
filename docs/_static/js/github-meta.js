// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Fills in star count and latest version from the GitHub API. Results
// are cached in sessionStorage for an hour to avoid hitting the rate
// limit on every page navigation.

(function () {
    const REPO = "giampaolo/psutil";
    const CACHE_KEY = "psutil-gh-meta";
    const CACHE_TTL_MS = 60 * 60 * 1000;

    function applyValues(stars, version) {
        const s = document.querySelector(".topbar-stars");
        const v = document.querySelector(".topbar-version");
        if (s && stars) {
            s.textContent = stars;
        }
        if (v && version) {
            v.textContent = version;
        }
    }

    function formatStars(n) {
        if (typeof n !== "number") {
            return "";
        }
        if (n >= 1000) {
            return (n / 1000).toFixed(1) + "k";
        }
        return String(n);
    }

    let cached;
    try {
        cached = JSON.parse(sessionStorage.getItem(CACHE_KEY) || "null");
    }
    catch (e) {
        cached = null;
    }
    if (cached && Date.now() - cached.t < CACHE_TTL_MS) {
        applyValues(cached.stars, cached.version);
        return;
    }

    Promise.all([
        fetch("https://api.github.com/repos/" + REPO).then((
            r,
        ) => (r.ok ? r.json() : null)),
        // /releases/latest only works if a release is explicitly
        // marked as latest. /tags is more reliable.
        fetch("https://api.github.com/repos/" + REPO + "/tags").then((
            r,
        ) => (r.ok ? r.json() : null)),
    ])
        .then((results) => {
            const repo = results[0];
            const tags = results[1];
            // Skip caching on a rate-limit / error response so the next
            // page load retries instead of showing empty for an hour.
            if (!repo || !Array.isArray(tags)) {
                return;
            }
            const stars = formatStars(repo.stargazers_count);
            const rawTag = (tags[0] && tags[0].name) || "";
            // GitHub returns tags like "v7.2.2"; drop the leading "v"
            // so the topbar shows the bare version number.
            const version = rawTag.replace(/^v/, "");
            try {
                sessionStorage.setItem(
                    CACHE_KEY,
                    JSON.stringify({
                        t: Date.now(),
                        stars: stars,
                        version: version,
                    }),
                );
            }
            catch (e) {
                // private mode / storage disabled: skip caching
            }
            applyValues(stars, version);
        })
        .catch(() => {
            // offline / network error: leave the topbar placeholders
        });
})();
