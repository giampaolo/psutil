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
    const section = container.closest(".comments");
    const url = new URL(container.dataset.themeUrl, location.href).href;
    let sheet = null;
    let ready = false;
    let pushed = null;

    function isDark() {
        return document.documentElement.getAttribute("data-theme") === "dark";
    }

    // css/giscus.css branches on prefers-color-scheme, which inside
    // giscus' iframe follows the reader's OS rather than our toggle.
    // Swap the conditions for ones that are always (or never) true so
    // the branch we want is the one that applies.
    function themeFor(dark) {
        const yes = "(min-width: 0px)";
        const no = "(min-width: 99999px)";
        const css = sheet
            .replace(/\(prefers-color-scheme:\s*dark\)/g, dark ? yes : no)
            .replace(/\(prefers-color-scheme:\s*light\)/g, dark ? no : yes);
        return "data:text/css;base64," + btoa(css);
    }

    function inject() {
        const attrs = {
            "data-repo": container.dataset.repo,
            "data-repo-id": container.dataset.repoId,
            "data-category": container.dataset.category,
            "data-category-id": container.dataset.categoryId,
            // Thread key is the source path, not the URL.
            "data-mapping": "specific",
            "data-term": container.dataset.term,
            // Without this giscus matches by fuzzy title search,
            // and our terms all share a "blog/<year>/" prefix.
            "data-strict": "1",
            "data-reactions-enabled": "1",
            "data-emit-metadata": "0",
            "data-input-position": "top",
            "data-theme": sheet ? themeFor(isDark()) : url,
            "data-lang": "en",
            "data-loading": "lazy",
        };
        pushed = isDark();

        const script = document.createElement("script");
        script.src = ORIGIN + "/client.js";
        script.crossOrigin = "anonymous";
        script.async = true;
        Object.keys(attrs).forEach((name) => {
            script.setAttribute(name, attrs[name]);
        });
        // A blocked script fires "error", not "load", so the section
        // stays hidden rather than showing an empty widget.
        script.addEventListener("load", () => {
            if (section) {
                section.removeAttribute("hidden");
            }
        });
        container.appendChild(script);
    }

    function push() {
        if (!ready || !sheet || isDark() === pushed) {
            return;
        }
        const frame = document.querySelector("iframe.giscus-frame");
        if (!frame || !frame.contentWindow) {
            return;
        }
        const dark = isDark();
        frame.contentWindow.postMessage(
            { giscus: { setConfig: { theme: themeFor(dark) } } },
            ORIGIN,
        );
        pushed = dark;
    }

    new MutationObserver(push).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });

    // contentWindow exists well before giscus can receive messages,
    // so wait for it to talk to us first.
    window.addEventListener("message", (event) => {
        if (event.origin !== ORIGIN || !event.data || !event.data.giscus) {
            return;
        }
        ready = true;
        push();
    });

    // giscus fetches its theme with crossorigin="anonymous", which
    // needs CORS headers and is blocked outright from localhost.
    // Inlining it sidesteps both: this fetch is same-origin.
    fetch(url)
        .then((resp) => {
            if (!resp.ok) {
                throw new Error(resp.status);
            }
            return resp.text();
        })
        .then((css) => {
            sheet = css;
        })
        .catch((err) => {
            // Fall back to the URL, fine wherever CORS allows it.
            console.warn("giscus: inlining theme failed:", err);
        })
        .finally(inject);
})();
