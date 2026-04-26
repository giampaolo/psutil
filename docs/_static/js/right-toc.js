// Right-side per-page TOC: scroll-spy via IntersectionObserver.
// Highlights the heading currently below the topbar by adding the
// .scroll-current class to its <li> and to all ancestor <li>s.
(function () {
    "use strict";

    var entries = Array.prototype.slice
        .call(document.querySelectorAll(".right-toc a[href^=\"#\"]"))
        .map(function (link) {
            var hash = link.getAttribute("href").slice(1);
            var target = document.getElementById(decodeURIComponent(hash));
            if (!target) return null;
            // Sphinx puts ids on <section> wrappers, which span the
            // whole subsection content. Observe the heading element
            // inside instead, since its small height plays nicely
            // with IntersectionObserver. For non-section targets
            // (e.g. <dt> for autodoc functions), use as-is.
            var heading = target;
            if (target.tagName === "SECTION") {
                var h = target.querySelector("h1, h2, h3, h4, h5, h6");
                if (h) heading = h;
            }
            return { link: link, heading: heading };
        })
        .filter(Boolean);

    if (entries.length === 0) {
        return;
    }

    var tocContainer = document.querySelector(".right-toc");

    // The currently active <li>s (leaf + ancestors).
    var activeLis = [];

    // Scroll the TOC's own overflow container so `el` is visible.
    // Only touches the container; never scrolls the page (using
    // scrollIntoView would cascade up and move the document too).
    function ensureVisibleInToc(el) {
        if (!tocContainer || !el) return;
        var c = tocContainer.getBoundingClientRect();
        var r = el.getBoundingClientRect();
        if (r.top < c.top) {
            tocContainer.scrollTop -= c.top - r.top;
        } else if (r.bottom > c.bottom) {
            tocContainer.scrollTop += r.bottom - c.bottom;
        }
    }

    function setActive(link) {
        // Clear previous.
        activeLis.forEach(function (li) {
            li.classList.remove("scroll-current");
        });
        activeLis = [];

        if (!link) return;

        // Walk up the <li> chain from the link's parent.
        var li = link.parentNode && link.parentNode.closest("li");
        while (li) {
            li.classList.add("scroll-current");
            activeLis.push(li);
            // Move to the nearest ancestor <li> (skip the <ul> in between).
            li = li.parentNode && li.parentNode.closest("li");
        }

        ensureVisibleInToc(link);
    }

    // Pick the last heading whose top is at or above the activation
    // band (64px below viewport top). If we're at the very bottom of
    // the page, force the last heading active so short final
    // sections (which never reach the band) still get highlighted.
    function pickActive() {
        var atBottom =
            window.innerHeight + window.scrollY >=
            document.documentElement.scrollHeight - 4;
        if (atBottom) {
            setActive(entries[entries.length - 1].link);
            return;
        }
        var best = null;
        for (var i = 0; i < entries.length; i++) {
            var top = entries[i].heading.getBoundingClientRect().top;
            if (top <= 64) {
                best = entries[i];
            } else {
                break;
            }
        }
        setActive(best ? best.link : null);
    }

    // The IntersectionObserver fires when a heading enters or leaves
    // the activation band, which is the cheap signal to recompute.
    var observer = new IntersectionObserver(
        function () {
            pickActive();
        },
        {
            rootMargin: "-64px 0px -70% 0px",
            threshold: 0,
        }
    );

    entries.forEach(function (e) {
        observer.observe(e.heading);
    });

    // Initial pass for deep links (page loads scrolled to a hash).
    pickActive();

    // Scroll listener (rAF-throttled) covers the cases the observer
    // misses: scrolling within a single section without crossing
    // any heading, and the at-bottom snap.
    var scrollPending = false;
    window.addEventListener(
        "scroll",
        function () {
            if (scrollPending) return;
            scrollPending = true;
            requestAnimationFrame(function () {
                scrollPending = false;
                pickActive();
            });
        },
        { passive: true }
    );
})();
