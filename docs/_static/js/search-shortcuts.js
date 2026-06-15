// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Sidebar input:
//   `CTRL+K` / `CMD+K`: focus / select the search input
//   `ESC`: exit search
//
// Search results page:
//   `Arrow Up` / `Arrow down`: navigate results
//   `ENTER`: open result

(function () {
    // Disable Sphinx's built-in "/" shortcut so it doesn't compete.
    // Done before the touch-device early return so it applies there too.
    if (typeof DOCUMENTATION_OPTIONS !== "undefined") {
        DOCUMENTATION_OPTIONS.ENABLE_SEARCH_SHORTCUTS = false;
    }

    if (window.matchMedia("(pointer: coarse)").matches) {
        return;
    }

    function getInput() {
        return document.getElementById("search-input");
    }

    // Re-submitting the same query on the search page is a browser
    // no-op (URL doesn't change). Force a reload only in that case;
    // for a real navigation, let the browser do its thing.
    getInput()?.form?.addEventListener("submit", (e) => {
        const form = e.currentTarget;
        const action = new URL(form.action, location.href);
        action.search = "?" + new URLSearchParams(new FormData(form));
        if (action.pathname === location.pathname
            && action.search === location.search) {
            e.preventDefault();
            location.reload();
        }
    });

    // ---- Ctrl+K + Esc on the sidebar input -------------------------

    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            const input = getInput();
            if (input) {
                e.preventDefault();
                if (document.activeElement === input) {
                    input.blur();
                } else {
                    input.focus();
                    input.select();
                }
            }
            return;
        }
        if (e.key === "Escape") {
            const input = getInput();
            if (input && document.activeElement === input) {
                input.value = "";
                input.blur();
            }
        }
    });

    // ---- Arrow-key navigation on the search results page -----------
    (function () {
        const container = document.getElementById("search-results");
        if (!container) {
            return;
        }

        const pageInput = document.querySelector(".search-page-input");
        const sidebarInput = getInput();
        let activeIndex = -1;

        function getResults() {
            return Array.from(container.querySelectorAll("ul.search > li"));
        }

        function setActive(index) {
            const results = getResults();
            if (!results.length) {
                return;
            }
            index = Math.max(0, Math.min(index, results.length - 1));
            results.forEach((li) => {
                li.classList.remove("search-result-active");
            });
            activeIndex = index;
            results[index].classList.add("search-result-active");
            results[index].scrollIntoView({ block: "nearest" });
        }

        function clearActive() {
            activeIndex = -1;
            getResults().forEach((li) => {
                li.classList.remove("search-result-active");
            });
        }

        // When Sphinx adds new <li>s, drop any prior selection.
        new MutationObserver((mutations) => {
            const hasNewLi = mutations.some((m) => {
                return Array.from(m.addedNodes).some((n) => {
                    return n.tagName === "LI";
                });
            });
            if (hasNewLi) {
                clearActive();
            }
        }).observe(container, { childList: true, subtree: true });

        function isSearchInput(el) {
            return el && (el === sidebarInput || el === pageInput);
        }

        document.addEventListener("keydown", (e) => {
            if (!getResults().length) {
                return;
            }
            if (isSearchInput(document.activeElement)) {
                if (e.key !== "ArrowDown") {
                    return;
                }
                e.preventDefault();
                document.activeElement.blur();
                setActive(0);
                return;
            }
            if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive(activeIndex === -1 ? 0 : activeIndex + 1);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (activeIndex > 0) {
                    setActive(activeIndex - 1);
                }
            } else if (e.key === "Enter" && activeIndex >= 0) {
                e.preventDefault();
                const link = getResults()[activeIndex].querySelector("a");
                if (link) {
                    link.click();
                }
            }
        });
    })();
})();
