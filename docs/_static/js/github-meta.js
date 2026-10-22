// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Fills in the star count from the GitHub API. Result is cached in
// sessionStorage for an hour to avoid hitting the rate limit on every
// page navigation.

(function () {
    const REPO = "giampaolo/psutil";
    const CACHE_KEY = "psutil-gh-meta";
    const CACHE_TTL_MS = 60 * 60 * 1000;

    function applyValues(stars) {
        const s = document.querySelector(".topbar-stars");
        if (s && stars) {
            s.textContent = stars;
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
        applyValues(cached.stars);
        return;
    }

    fetch("https://api.github.com/repos/" + REPO)
        .then((r) => (r.ok ? r.json() : null))
        .then((repo) => {
            // Skip caching on a rate-limit / error response so the next
            // page load retries instead of showing empty for an hour.
            if (!repo) {
                return;
            }
            const stars = formatStars(repo.stargazers_count);
            try {
                sessionStorage.setItem(
                    CACHE_KEY,
                    JSON.stringify({ t: Date.now(), stars: stars }),
                );
            }
            catch (e) {
                // private mode / storage disabled: skip caching
            }
            applyValues(stars);
        })
        .catch(() => {
            // offline / network error: leave the topbar placeholders
        });
})();
