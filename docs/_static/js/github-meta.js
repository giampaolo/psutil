// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Add GitHub stars count + latest version/tag. Both are cached in
// localStorage so we don't hit the API on every page load.

(function () {
    "use strict";

    var CACHE_TTL_MS = 6 * 60 * 60 * 1000;  // 6 hours

    function readCache(key) {
        try {
            var raw = localStorage.getItem(key);
            if (!raw) {
                return null;
            }
            var parsed = JSON.parse(raw);
            if ("value" in parsed
                    && Date.now() - parsed.ts < CACHE_TTL_MS) {
                return parsed.value;
            }
        } catch (e) {
            // fall through and refetch
        }
        return null;
    }

    function writeCache(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify({
                value: value,
                ts: Date.now(),
            }));
        } catch (e) {
            // localStorage disabled / quota: skip silently
        }
    }

    function fetchJson(url) {
        return fetch(url).then(function (r) {
            return r.ok ? r.json() : null;
        });
    }

    function formatStars(n) {
        if (n >= 10000) {
            return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
        }
        if (n >= 1000) {
            return (n / 1000).toFixed(1) + "k";
        }
        return String(n);
    }

    function loadStars(el) {
        var repo = el.getAttribute("data-repo");
        if (!repo) {
            return;
        }
        var key = "gh-stars:" + repo;
        var cached = readCache(key);
        if (cached !== null) {
            el.textContent = formatStars(cached);
            return;
        }
        fetchJson("https://api.github.com/repos/" + repo)
            .then(function (data) {
                if (!data || typeof data.stargazers_count !== "number") {
                    return;
                }
                el.textContent = formatStars(data.stargazers_count);
                writeCache(key, data.stargazers_count);
            })
            .catch(function () {});
    }

    function pickVersion(tags) {
        if (!Array.isArray(tags)) {
            return null;
        }
        for (var i = 0; i < tags.length; i++) {
            var name = tags[i].name;
            if (name && name[0] === "v") {
                return name.slice(1);  // remove "v" prefix
            }
        }
        return null;
    }

    function loadVersion(el) {
        var repo = el.getAttribute("data-repo");
        if (!repo) {
            return;
        }
        var key = "gh-version:" + repo;
        var cached = readCache(key);
        if (cached !== null) {
            el.textContent = cached;
            return;
        }
        fetchJson("https://api.github.com/repos/" + repo + "/tags?per_page=10")
            .then(function (tags) {
                var v = pickVersion(tags);
                if (!v) {
                    return;
                }
                el.textContent = v;
                writeCache(key, v);
            })
            .catch(function () {});
    }

    function init() {
        var stars = document.getElementById("github-stars");
        if (stars) {
            loadStars(stars);
        }
        var version = document.getElementById("github-version");
        if (version) {
            loadVersion(version);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    }
    else {
        init();
    }
})();
