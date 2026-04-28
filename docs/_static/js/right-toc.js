// Right-side per-page TOC. Modeled after pydata-sphinx-theme.

(function () {
    "use strict";

    var pageToc = document.querySelector(".right-toc");
    if (!pageToc) {
        return;
    }

    var tocLinks = Array.prototype.slice.call(
        pageToc.querySelectorAll("a[href^=\"#\"]")
    );

    if (tocLinks.length === 0) {
        return;
    }

    function getHeading(tocLink) {
        var href = tocLink.getAttribute("href");
        if (!href || !href.startsWith("#")) {
            return null;
        }

        var id = href.substring(1);
        if (!id) {
            return null;
        }

        var decodedId;
        try {
            decodedId = decodeURIComponent(id);
        }
        catch (e) {
            // Malformed %-escape in the href; ignore this entry.
            return null;
        }

        var target = document.getElementById(decodedId);
        if (!target) {
            return null;
        }

        // Prefer the heading inside; fall back to target itself for
        // <dt> autodoc anchors with no inner heading.
        var heading = target.querySelector("h1, h2, h3, h4, h5, h6");
        if (heading) {
            return heading;
        }
        return target;
    }

    var headingsToTocLinks = new Map();

    tocLinks.forEach(function (tocLink) {
        var heading = getHeading(tocLink);
        if (heading) {
            headingsToTocLinks.set(heading, tocLink);
        }
    });

    var observedHeadings = Array.from(headingsToTocLinks.keys());
    var intersectingHeadings = new Set();

    var titleHeight = 0;

    function refreshTitleHeight() {
        var title = pageToc.querySelector(".right-toc-title");
        if (title) {
            titleHeight = title.offsetHeight;
        }
        else {
            titleHeight = 0;
        }
    }

    refreshTitleHeight();

    // offsetTop / clientHeight are precomputed; getBoundingClientRect
    // would force a layout flush each call.
    function ensureVisibleInToc(link) {
        var linkTop = link.offsetTop;
        var linkBottom = linkTop + link.offsetHeight;

        var visibleTop = pageToc.scrollTop + titleHeight;
        var visibleBottom = pageToc.scrollTop + pageToc.clientHeight;

        if (linkTop < visibleTop) {
            pageToc.scrollTop = Math.max(0, linkTop - titleHeight);
        }
        else if (linkBottom > visibleBottom) {
            pageToc.scrollTop = linkBottom - pageToc.clientHeight;
        }
    }

    var activeLink = null;
    var activeLis = [];

    function activate(tocLink) {
        if (tocLink === activeLink) {
            return;
        }

        if (activeLink) {
            activeLink.classList.remove("scroll-current");
            activeLink.removeAttribute("aria-current");
        }

        activeLis.forEach(function (li) {
            li.classList.remove("scroll-current");
            li.classList.remove("scroll-current-leaf");
        });

        activeLis = [];
        activeLink = tocLink;

        if (!tocLink) {
            return;
        }

        tocLink.classList.add("scroll-current");
        tocLink.setAttribute("aria-current", "true");

        var leaf = tocLink.parentNode && tocLink.parentNode.closest("li");

        if (leaf) {
            leaf.classList.add("scroll-current");
            leaf.classList.add("scroll-current-leaf");

            activeLis.push(leaf);

            var li = leaf.parentNode && leaf.parentNode.closest("li");

            while (li) {
                li.classList.add("scroll-current");
                activeLis.push(li);
                li = li.parentNode && li.parentNode.closest("li");
            }
        }

        ensureVisibleInToc(tocLink);
    }

    var observer;

    function connectIntersectionObserver() {
        if (observer) {
            observer.disconnect();
        }

        intersectingHeadings.clear();
        refreshTitleHeight();

        var topbar = document.querySelector(".top-bar");
        var headerHeight = topbar ? topbar.offsetHeight : 0;

        // Active band: top 30% of viewport below the header.
        var options = {
            root: null,
            rootMargin: "-" + headerHeight + "px 0px -70% 0px",
            threshold: 0,
        };

        function callback(entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    intersectingHeadings.add(e.target);
                }
                else {
                    intersectingHeadings.delete(e.target);
                }
            });

            if (intersectingHeadings.size === 0) {
                return;
            }

            var top = observedHeadings.find(function (h) {
                return intersectingHeadings.has(h);
            });

            if (top) {
                var tocLink = headingsToTocLinks.get(top);
                if (tocLink) {
                    activate(tocLink);
                }
            }
        }

        observer = new IntersectionObserver(callback, options);

        observedHeadings.forEach(function (h) {
            observer.observe(h);
        });
    }

    function debounce(fun, wait) {
        var t;

        return function () {
            clearTimeout(t);
            t = setTimeout(fun, wait);
        };
    }

    window.addEventListener(
        "resize",
        debounce(connectIntersectionObserver, 300)
    );

    connectIntersectionObserver();

    // Set the first visible TOC as the default highlight.
    if (!activeLink) {
        for (var i = 0; i < tocLinks.length; i++) {
            if (getComputedStyle(tocLinks[i]).display !== "none") {
                activate(tocLinks[i]);
                break;
            }
        }
    }
})();
