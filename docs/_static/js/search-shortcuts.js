// Implement keyboard shortcuts re. to search.
// - Ctrl+K: un/focus the search input (was /)
// - esc: unfocus the search input
// Search results page:
// - up/down: move selection
// - enter: open entry

document.addEventListener("DOMContentLoaded", function () {
    // No-op on touch/mobile devices.
    if (window.matchMedia("(pointer: coarse)").matches)
        return;

    var searchInput = document.querySelector(
        "#rtd-search-form input[name='q']"
    );

    // Disable Sphinx's built-in "/" search shortcut.
    function disableSphinxShortcut() {
        if (typeof DOCUMENTATION_OPTIONS !== "undefined")
            DOCUMENTATION_OPTIONS.ENABLE_SEARCH_SHORTCUTS = false;
    }

    // Focus the search input on Ctrl+K; blur it on Escape.
    function initCtrlK(input) {
        if (!input) return;
        document.addEventListener("keydown", function (e) {
            if (e.ctrlKey && e.key === "k") {
                e.preventDefault();
                if (document.activeElement === input)
                    input.blur();
                else {
                    input.focus();
                    input.select();
                }
            }
            else if (e.key === "Escape" && document.activeElement === input)
                input.blur();
        });
    }

    // Hide/show the server-rendered Ctrl+K badge on focus/blur.
    function initCtrlKBadge(input) {
        if (!input)
            return;
        var badge = input.parentNode.querySelector(".search-kbd-hint");
        if (!badge)
            return;
        input.addEventListener("focus", function () { badge.style.opacity = "0"; });
        input.addEventListener("blur",  function () { badge.style.opacity = ""; });
    }

    // Shade the rest of the page while the search input is focused
    // by overlaying a dim layer; the search container is lifted
    // above it via CSS.
    function initFocusBlur(input) {
        if (!input)
            return;
        var overlay = document.createElement("div");
        overlay.className = "search-overlay";
        document.body.appendChild(overlay);
        input.addEventListener("focus", function () {
            document.body.classList.add("search-focused");
        });
        input.addEventListener("blur", function () {
            document.body.classList.remove("search-focused");
        });
    }

    // Enable Up/Down arrow navigation and Enter to open on the
    // search results page. The first result is auto-selected once
    // results finish loading.
    function initResultsNavigation(searchInput) {
        var container = document.getElementById("search-results");
        if (!container) return;

        var activeIndex = -1;

        // Return the current list of result <li> elements.
        function getResults() {
            return Array.from(container.querySelectorAll("ul.search li"));
        }

        // Highlight the result at `index` and scroll it into view.
        function setActive(index) {
            var results = getResults();
            if (!results.length) return;
            index = Math.max(0, Math.min(index, results.length - 1));
            results.forEach(function (li) {
                li.classList.remove("search-result-active");
            });
            activeIndex = index;
            results[index].classList.add("search-result-active");
            results[index].scrollIntoView({ block: "nearest" });
        }

        // Remove highlight from all results.
        function clearActive() {
            activeIndex = -1;
            getResults().forEach(function (li) {
                li.classList.remove("search-result-active");
            });
        }

        initResultsObserver(container, getResults, clearActive, setActive);
        initNavigationKeys(searchInput, getResults, setActive, clearActive);

        // Watch for new <li> elements and auto-select the first result
        // once the batch finishes loading.
        function initResultsObserver(container, getResults, clearActive, setActive) {
            var debounceTimer;
            new MutationObserver(function (mutations) {
                var hasNewLi = mutations.some(function (m) {
                    return Array.from(m.addedNodes).some(function (n) {
                        return n.tagName === "LI";
                    });
                });
                if (!hasNewLi) return;
                clearActive();
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function () {
                    if (getResults().length) setActive(0);
                }, 80);
            }).observe(container, { childList: true, subtree: true });
        }

        // Handle arrow-key navigation and Enter to open the active
        // result. Down from the search input moves to the first result.
        function initNavigationKeys(searchInput, getResults, setActive, clearActive) {
            document.addEventListener("keydown", function (e) {
                if (!getResults().length) return;
                if (document.activeElement === searchInput) {
                    if (e.key !== "ArrowDown") return;
                    e.preventDefault();
                    searchInput.blur();
                    setActive(0);
                    return;
                }
                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setActive(activeIndex === -1 ? 0 : activeIndex + 1);
                }
                else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    if (activeIndex > 0)
                        setActive(activeIndex - 1);
                }
                else if (e.key === "Enter" && activeIndex >= 0) {
                    e.preventDefault();
                    var link = getResults()[activeIndex].querySelector("a");
                    if (link)
                        link.click();
                }
            });
        }
    }

    disableSphinxShortcut();
    initCtrlK(searchInput);
    initCtrlKBadge(searchInput);
    initFocusBlur(searchInput);
    initResultsNavigation(searchInput);
});
