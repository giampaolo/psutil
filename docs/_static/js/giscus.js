// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Blog comments, backed by giscus + GitHub Discussions.

(function () {
    const container = document.querySelector(".giscus");
    if (!container) {
        return;
    }

    const ORIGIN = "https://giscus.app";

    function currentTheme() {
        const theme = document.documentElement.getAttribute("data-theme");
        return theme === "dark" ? "dark" : "light";
    }

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
        "data-theme": currentTheme(),
        "data-lang": "en",
        "data-loading": "lazy",
    };

    const section = container.closest(".comments");
    const script = document.createElement("script");
    script.src = ORIGIN + "/client.js";
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

    // frame.contentWindow exists before giscus is ready to receive
    // messages, so track readiness explicitly instead.
    let ready = false;
    let lastPushed = attrs["data-theme"];

    function pushTheme() {
        if (!ready) {
            return;
        }
        const theme = currentTheme();
        if (theme === lastPushed) {
            return;
        }
        const frame = document.querySelector("iframe.giscus-frame");
        if (!frame || !frame.contentWindow) {
            return;
        }
        frame.contentWindow.postMessage(
            { giscus: { setConfig: { theme } } },
            ORIGIN,
        );
        lastPushed = theme;
    }

    const observer = new MutationObserver(pushTheme);
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });

    window.addEventListener("message", (event) => {
        if (event.origin !== ORIGIN) {
            return;
        }
        if (
            !event.data || typeof event.data !== "object" ||
            !event.data.giscus
        ) {
            return;
        }
        if (!ready) {
            ready = true;
            // giscus re-sets iframe.src on sign-out, which re-renders
            // with the theme baked into the script tag.
            const frame = document.querySelector("iframe.giscus-frame");
            if (frame) {
                frame.addEventListener("load", () => {
                    lastPushed = attrs["data-theme"];
                    pushTheme();
                });
            }
        }
        pushTheme();
    });
})();
