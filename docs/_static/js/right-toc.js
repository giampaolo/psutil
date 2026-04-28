// Right-side per-page TOC.
//
// Modeled after pydata-sphinx-theme.
//
// Pydata collapses non-active TOC branches via CSS so the visible
// TOC stays short. Our 200+ item TOC isn't collapsed, except for h4.

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

        var target = document.getElementById(decodeURIComponent(id));
        if (!target) {
            return null;
        }

        // Prefer the heading inside the section (small height plays
        // better with IO than the section wrapper). Fall back to
        // target itself for things like <dt> autodoc anchors.
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

    // Title height — cached once. The .right-toc-title is sticky at
    // top:0, so its height equals its bottom edge in container
    // coords, regardless of scrollTop. Recomputed on resize (the
    // observer rebuild path), where layout may change.
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

    // Use offsetTop / clientHeight — both precomputed by the
    // layout engine — instead of getBoundingClientRect, which
    // forces a synchronous layout flush each call.
    function ensureVisibleInToc(link) {
        var linkTop = link.offsetTop;
        var linkBottom = linkTop + link.offsetHeight;

        var visibleTop = pageToc.scrollTop + titleHeight;
        var visibleBottom =
            pageToc.scrollTop + pageToc.clientHeight;

        if (linkTop < visibleTop) {
            pageToc.scrollTop = linkTop - titleHeight;
        }
        else if (linkBottom > visibleBottom) {
            pageToc.scrollTop = linkBottom - pageToc.clientHeight;
        }
    }

    // Track the active link + ancestor <li>s so we only touch what
    // changes. Iterating all nav items per activation triggered a
    // style-recalc storm at 200+ items.
    var activeLink = null;
    var activeLis = [];

    // The leaf <li> also gets .scroll-current-leaf so CSS can target
    // the deepest item without `:has()`, which is expensive when
    // re-evaluated on every class change.
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

        var headerHeight = 0;
        if (topbar) {
            headerHeight = topbar.offsetHeight;
        }

        var options = {
            root: null,
            // Top of band: just below the header. Bottom: 70% from
            // the viewport bottom — i.e., active when heading is in
            // the top 30% of the viewport. Same numbers pydata uses.
            rootMargin: "-" + headerHeight + "px 0px -70% 0px",
            threshold: 0,
        };

        function callback(entries) {
            // Update the running set of intersecting headings.
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

        Array.from(headingsToTocLinks.keys()).forEach(
            function (h) {
                observer.observe(h);
            }
        );
    }

    function debounce(fun, wait) {
        var t;

        return function () {
            clearTimeout(t);
            t = setTimeout(fun, wait);
        };
    }

    // Header height can change on resize; rebuild observer with
    // the updated rootMargin.
    window.addEventListener(
        "resize",
        debounce(connectIntersectionObserver, 300)
    );

    connectIntersectionObserver();
})();
