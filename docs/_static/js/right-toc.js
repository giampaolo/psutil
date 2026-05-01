// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Right-side per-page TOC. Modeled after pydata-sphinx-theme.

(function () {
    "use strict";

    var pageToc = document.querySelector(".right-toc");
    if (!pageToc) {
        return;
    }

    // Strip trailing "()" from function-name entries (just visual noise).
    pageToc.querySelectorAll("a code .pre").forEach(function (el) {
        if (el.textContent.endsWith("()")) {
            el.textContent = el.textContent.slice(0, -2);
        }
    });

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
    var disableObserver = false;

    function temporarilyDisableObserver(ms) {
        disableObserver = true;
        setTimeout(function () {
            disableObserver = false;
        }, ms);
    }

    function connectIntersectionObserver() {
        if (observer) {
            observer.disconnect();
        }

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
            if (disableObserver) {
                return;
            }
            var entry = entries.filter(function (e) {
                return e.isIntersecting;
            }).pop();
            if (!entry) {
                return;
            }
            var tocLink = headingsToTocLinks.get(entry.target);
            if (tocLink) {
                activate(tocLink);
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

    // Highlight the TOC entry whose href matches the URL hash. Used on
    // page load and when navigating between headings on the same page.
    function syncTocHash(hash) {
        if (!hash || hash.length <= 1) {
            return;
        }
        var link = tocLinks.find(function (l) {
            return l.hash === hash;
        });
        if (link) {
            temporarilyDisableObserver(1000);
            activate(link);
        }
    }

    window.addEventListener(
        "resize",
        debounce(connectIntersectionObserver, 300)
    );

    connectIntersectionObserver();

    // Initial sync (in case the URL has a hash).
    syncTocHash(location.hash);

    // Hash changes via in-page anchor clicks.
    window.addEventListener("hashchange", function () {
        syncTocHash(location.hash);
    });

    // Edge case: clicking a same-hash link doesn't fire hashchange,
    // but we still want the TOC to re-sync (the user may have scrolled
    // away from that section in between).
    window.addEventListener("click", function (e) {
        var link = e.target.closest("a");
        if (link
            && link.hash
            && link.hash === location.hash
            && link.origin === location.origin) {
            syncTocHash(link.hash);
        }
    });
})();
