// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// On @ key press, show a menu to jump to API definitions.

(function () {
    const SCROLL_MS = 150;
    const CONSECUTIVE_BONUS = 8;
    const WORD_START_BONUS = 10;

    const contentRoot = document.documentElement.dataset.content_root || "";
    let symbols = null;
    let loadState = "idle";

    // Lazy-load the symbol index (written at build time by
    // _ext/api_symbols.py) the first time the menu is opened.
    function ensureSymbols() {
        if (loadState !== "idle") {
            return;
        }
        loadState = "loading";
        const script = document.createElement("script");
        script.src = contentRoot + "_static/api-symbols.js";
        script.onload = () => {
            symbols = window.PSUTIL_API_SYMBOLS || [];
            loadState = "loaded";
            update();
        };
        script.onerror = () => {
            loadState = "error";
            console.error("api-palette: failed to load api-symbols.js");
            update();
        };
        document.head.appendChild(script);
    }

    const palette = document.createElement("div");
    palette.className = "api-palette";
    palette.setAttribute("aria-hidden", "true");
    palette.setAttribute("role", "dialog");
    palette.setAttribute("aria-modal", "true");
    palette.setAttribute("aria-label", "Go to API definition");
    palette.innerHTML = '<div class="api-palette-backdrop"></div>' +
        '<div class="api-palette-panel">' +
        '<input class="api-palette-input" type="text" ' +
        'placeholder="Go to API definition" aria-label="Go to API definition" ' +
        'role="combobox" aria-autocomplete="list" aria-expanded="false" ' +
        'aria-controls="api-palette-listbox" ' +
        'spellcheck="false" autocomplete="off">' +
        '<ul class="api-palette-results" id="api-palette-listbox" ' +
        'role="listbox"></ul>' +
        "</div>";
    document.body.appendChild(palette);

    const backdrop = palette.querySelector(".api-palette-backdrop");
    const input = palette.querySelector(".api-palette-input");
    const list = palette.querySelector(".api-palette-results");
    let lastFocused = null;
    let shown = [];
    let activeIndex = -1;
    let startScrollY = 0;
    let previewEnabled = false;
    let previewed = false;
    let settleY = null;
    // Bumped on every new scroll so the animation still running for
    // the previous target stops writing.
    let scrollAnimId = 0;

    // Query chars must appear in the name in order. Bonuses for
    // consecutive runs and word starts, small penalty for gaps. A
    // space matches the next "_" or ".", so "mem info" finds
    // memory_info.
    function fuzzy(query, text) {
        const q = query.toLowerCase();
        const t = text.toLowerCase();
        const boundary = "._";
        const positions = [];
        let score = 0;
        let from = 0;
        let prev = -2;
        for (const ch of q) {
            let idx;
            if (ch === " ") {
                const dot = t.indexOf(".", from);
                const under = t.indexOf("_", from);
                if (dot === -1 || (under !== -1 && under < dot)) {
                    idx = under;
                }
                else {
                    idx = dot;
                }
            }
            else {
                idx = t.indexOf(ch, from);
            }
            if (idx === -1) {
                return null;
            }
            if (idx === prev + 1) {
                score += CONSECUTIVE_BONUS;
            }
            if (idx === 0 || boundary.includes(t[idx - 1])) {
                score += WORD_START_BONUS;
            }
            score -= idx - from;
            positions.push(idx);
            prev = idx;
            from = idx + 1;
        }
        return { score: score, positions: positions };
    }

    function renderMessage(text) {
        const li = document.createElement("li");
        li.className = "api-palette-empty";
        li.textContent = text;
        list.appendChild(li);
    }

    function render() {
        list.innerHTML = "";
        if (loadState === "loading") {
            renderMessage("Loading…");
            return;
        }
        if (loadState === "error") {
            renderMessage("Failed to load API definitions");
            return;
        }
        if (!shown.length) {
            renderMessage("No matching definitions");
            return;
        }
        shown.forEach((entry, i) => {
            const li = document.createElement("li");
            li.setAttribute("role", "option");
            li.id = "api-palette-opt-" + i;
            li.dataset.index = i;
            const name = document.createElement("span");
            name.className = "api-palette-name";
            const hits = new Set(entry.positions);
            for (let j = 0; j < entry.sym.name.length; j++) {
                const ch = document.createTextNode(entry.sym.name[j]);
                if (hits.has(j)) {
                    const b = document.createElement("b");
                    b.appendChild(ch);
                    name.appendChild(b);
                }
                else {
                    name.appendChild(ch);
                }
            }
            const type = document.createElement("span");
            type.className = "api-palette-type";
            type.textContent = entry.sym.type;
            li.appendChild(name);
            li.appendChild(type);
            list.appendChild(li);
        });
    }

    function setActive(index) {
        const rows = list.querySelectorAll("li[role=option]");
        if (!rows.length) {
            activeIndex = -1;
            input.removeAttribute("aria-activedescendant");
            return;
        }
        index = Math.max(0, Math.min(index, rows.length - 1));
        if (
            index === activeIndex &&
            rows[index].classList.contains("is-active")
        ) {
            return;
        }
        rows.forEach((li) => {
            li.classList.remove("is-active");
            li.setAttribute("aria-selected", "false");
        });
        activeIndex = index;
        rows[index].classList.add("is-active");
        rows[index].setAttribute("aria-selected", "true");
        input.setAttribute("aria-activedescendant", rows[index].id);
        rows[index].scrollIntoView({ block: "nearest" });
        previewActive();
    }

    function update() {
        const q = input.value.trim();
        const all = symbols || [];
        if (!q) {
            shown = all.map((s) => {
                return { sym: s, positions: [], score: 0 };
            });
        }
        else {
            shown = [];
            all.forEach((s) => {
                const m = fuzzy(q, s.name);
                if (m) {
                    shown.push({
                        sym: s,
                        positions: m.positions,
                        score: m.score,
                    });
                }
            });
            shown.sort((a, b) => {
                return (
                    b.score - a.score ||
                    a.sym.name.length - b.sym.name.length
                );
            });
        }
        render();
        let start = 0;
        if (!q) {
            const idx = currentSymbolIndex(startScrollY);
            if (idx !== -1) {
                start = idx;
            }
        }
        setActive(start);
        if (!q && previewed) {
            smoothScrollToY(startScrollY);
        }
        if (start > 0) {
            centerActive();
        }
        else {
            list.scrollTop = 0;
        }
    }

    // The definition read at the given scroll position: the last one
    // above the fold, using the same offset line the anchors scroll
    // to. Measured against startScrollY, not the live viewport, which
    // the previews move around.
    function currentSymbolIndex(scrollY) {
        const pad = parseFloat(
            getComputedStyle(document.documentElement).scrollPaddingTop,
        ) || 0;
        let id = null;
        for (const dt of document.querySelectorAll("dt.sig-object.py[id]")) {
            const top = dt.getBoundingClientRect().top + window.scrollY;
            if (top <= scrollY + pad + 1) {
                id = dt.id;
            }
            else {
                break;
            }
        }
        if (id === null) {
            return -1;
        }
        return shown.findIndex((entry) => entry.sym.anchor === id);
    }

    function centerActive() {
        const row = list.querySelector("li.is-active");
        if (row) {
            list.scrollTop = row.offsetTop -
                list.offsetTop -
                (list.clientHeight - row.offsetHeight) / 2;
        }
    }

    function open() {
        scrollAnimId += 1;
        lastFocused = document.activeElement;
        const resuming = settleY !== null;
        startScrollY = resuming ? settleY : window.scrollY;
        settleY = null;
        previewEnabled = false;
        // Reopened mid-animation: the page sits displaced, so let the
        // empty-query path below finish the interrupted move.
        previewed = resuming;
        palette.classList.add("is-open");
        palette.setAttribute("aria-hidden", "false");
        input.setAttribute("aria-expanded", "true");
        input.value = "";
        ensureSymbols();
        update();
        input.focus();
    }

    // Esc / backdrop click: scroll back to where the page was before
    // the previews. Left alone if no preview moved it, so a manual
    // scroll made while the menu is open survives.
    function cancel() {
        if (previewed) {
            smoothScrollToY(startScrollY, true);
        }
        close(true);
    }

    // Scroll the page behind the menu to the selected definition, VS
    // Code style. Only after the user navigated or typed, so opening
    // the menu doesn't move the page by itself.
    function previewActive() {
        if (!previewEnabled || activeIndex === -1 || !shown[activeIndex]) {
            return;
        }
        const sym = shown[activeIndex].sym;
        const root = new URL(contentRoot, location.href);
        if (new URL(sym.uri, root).pathname !== location.pathname) {
            return;
        }
        const el = sym.anchor && document.getElementById(sym.anchor);
        if (!el) {
            return;
        }
        previewed = true;
        smoothScrollTo(el);
    }

    function close(restoreFocus) {
        input.blur();
        palette.classList.remove("is-open");
        palette.setAttribute("aria-hidden", "true");
        input.setAttribute("aria-expanded", "false");
        if (
            restoreFocus &&
            lastFocused &&
            typeof lastFocused.focus === "function"
        ) {
            lastFocused.focus({ preventScroll: true });
        }
        lastFocused = null;
    }

    function smoothScrollTo(el, isSettle) {
        const pad = parseFloat(
            getComputedStyle(document.documentElement).scrollPaddingTop,
        ) || 0;
        smoothScrollToY(
            el.getBoundingClientRect().top + window.scrollY - pad,
            isSettle,
        );
    }

    function smoothScrollToY(dest, isSettle) {
        scrollAnimId += 1;
        const animId = scrollAnimId;
        settleY = null;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            window.scrollTo(0, dest);
            return;
        }
        if (isSettle) {
            settleY = dest;
        }
        const start = window.scrollY;
        const t0 = performance.now();
        function step(now) {
            if (animId !== scrollAnimId) {
                return;
            }
            const t = Math.min((now - t0) / SCROLL_MS, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            window.scrollTo(0, start + (dest - start) * eased);
            if (t < 1) {
                requestAnimationFrame(step);
            }
            else {
                settleY = null;
            }
        }
        requestAnimationFrame(step);
    }

    function go(sym) {
        close(false);
        const root = new URL(contentRoot, location.href);
        const frag = sym.anchor ? "#" + sym.anchor : "";
        const target = new URL(sym.uri + frag, root);
        const el = sym.anchor && target.pathname === location.pathname
            ? document.getElementById(sym.anchor)
            : null;
        if (el) {
            if (location.hash !== "#" + sym.anchor) {
                // Set the hash for the :target highlight, but undo
                // the instant jump it causes so we can animate.
                const y = window.scrollY;
                location.hash = sym.anchor;
                window.scrollTo(0, y);
            }
            smoothScrollTo(el, true);
            el.tabIndex = -1;
            el.focus({ preventScroll: true });
        }
        else {
            location.href = target.href;
        }
    }

    backdrop.addEventListener("click", () => {
        cancel();
    });

    list.addEventListener("click", (e) => {
        const li = e.target.closest("li[data-index]");
        if (li && shown[li.dataset.index]) {
            go(shown[li.dataset.index].sym);
        }
    });

    // React only to real mouse movement. Chrome fires a synthetic
    // mousemove after scrollIntoView(), which would yank the
    // selection back to whatever sits under the idle cursor while
    // navigating with the arrow keys.
    let lastMouseX = -1;
    let lastMouseY = -1;
    list.addEventListener("mousemove", (e) => {
        if (e.clientX === lastMouseX && e.clientY === lastMouseY) {
            return;
        }
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        const li = e.target.closest("li[data-index]");
        if (li) {
            previewEnabled = true;
            setActive(Number(li.dataset.index));
        }
    });

    input.addEventListener("input", () => {
        previewEnabled = true;
        update();
    });

    // stopPropagation: on the search page these same keys are handled
    // by search-shortcuts.js, which would move the results behind the
    // menu and steal the focus.
    palette.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            cancel();
        }
        else if (e.key === "ArrowDown") {
            e.preventDefault();
            e.stopPropagation();
            previewEnabled = true;
            setActive(activeIndex + 1);
        }
        else if (e.key === "ArrowUp") {
            e.preventDefault();
            e.stopPropagation();
            previewEnabled = true;
            setActive(activeIndex - 1);
        }
        else if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            if (activeIndex !== -1 && shown[activeIndex]) {
                go(shown[activeIndex].sym);
            }
        }
        else if (e.key === "Tab") {
            e.preventDefault();
            input.focus();
        }
    });

    document.addEventListener("keydown", (e) => {
        // Fallback: close on Esc even if focus ended up outside the
        // menu.
        if (e.key === "Escape" && palette.classList.contains("is-open")) {
            e.stopImmediatePropagation();
            cancel();
            return;
        }
        if (e.key !== "@") {
            return;
        }
        if (palette.classList.contains("is-open")) {
            return;
        }
        const el = document.activeElement;
        if (
            el &&
            (el.tagName === "INPUT" ||
                el.tagName === "TEXTAREA" ||
                el.isContentEditable)
        ) {
            return;
        }
        e.preventDefault();
        open();
    });

    // Make the "@" key shown in the docs (e.g. the api.rst tip)
    // clickable, as a way to discover the menu.
    document.querySelectorAll("kbd").forEach((kbd) => {
        if (kbd.textContent.trim() !== "@") {
            return;
        }
        kbd.classList.add("api-palette-kbd");
        kbd.title = "Open the go-to-definition menu";
        kbd.setAttribute("role", "button");
        kbd.tabIndex = 0;
        kbd.addEventListener("click", open);
        kbd.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                open();
            }
        });
    });
})();
