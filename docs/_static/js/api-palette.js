// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// On @ key press, show a go-to symbol menu, to jump to API symbols /
// definitions.

(function () {
    if (window.matchMedia("(pointer: coarse)").matches) {
        return;
    }

    const contentRoot = document.documentElement.dataset.content_root || "";
    let symbols = null;
    let loadState = "idle";

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
    palette.setAttribute("aria-label", "Jump to API symbol");
    palette.innerHTML = '<div class="api-palette-backdrop"></div>' +
        '<div class="api-palette-panel">' +
        '<input class="api-palette-input" type="text" ' +
        'placeholder="Jump to API symbol" aria-label="Jump to API symbol" ' +
        'spellcheck="false" autocomplete="off">' +
        '<ul class="api-palette-results" role="listbox"></ul>' +
        "</div>";
    document.body.appendChild(palette);

    const backdrop = palette.querySelector(".api-palette-backdrop");
    const input = palette.querySelector(".api-palette-input");
    const list = palette.querySelector(".api-palette-results");
    let lastFocused = null;
    let shown = [];
    let activeIndex = -1;

    function fuzzy(query, text) {
        const q = query.toLowerCase();
        const t = text.toLowerCase();
        const boundary = "._";
        const positions = [];
        let score = 0;
        let from = 0;
        let prev = -2;
        for (const ch of q) {
            const idx = t.indexOf(ch, from);
            if (idx === -1) {
                return null;
            }
            if (idx === prev + 1) {
                score += 8;
            }
            if (idx === 0 || boundary.includes(t[idx - 1])) {
                score += 10;
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
            renderMessage("Failed to load the symbol index");
            return;
        }
        if (!shown.length) {
            renderMessage("No matching symbols");
            return;
        }
        shown.forEach((entry, i) => {
            const li = document.createElement("li");
            li.setAttribute("role", "option");
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
            return;
        }
        index = Math.max(0, Math.min(index, rows.length - 1));
        rows.forEach((li) => {
            li.classList.remove("is-active");
            li.setAttribute("aria-selected", "false");
        });
        activeIndex = index;
        rows[index].classList.add("is-active");
        rows[index].setAttribute("aria-selected", "true");
        rows[index].scrollIntoView({ block: "nearest" });
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
        setActive(0);
        list.scrollTop = 0;
    }

    function open() {
        lastFocused = document.activeElement;
        palette.classList.add("is-open");
        palette.setAttribute("aria-hidden", "false");
        input.value = "";
        ensureSymbols();
        update();
        input.focus();
    }

    function close() {
        palette.classList.remove("is-open");
        palette.setAttribute("aria-hidden", "true");
        if (lastFocused && typeof lastFocused.focus === "function") {
            lastFocused.focus();
        }
        lastFocused = null;
    }

    function go(sym) {
        close();
        const root = new URL(contentRoot, location.href);
        const frag = sym.anchor ? "#" + sym.anchor : "";
        const target = new URL(sym.uri + frag, root);
        if (target.pathname === location.pathname && sym.anchor) {
            if (location.hash === "#" + sym.anchor) {
                const el = document.getElementById(sym.anchor);
                if (el) {
                    el.scrollIntoView();
                }
            }
            else {
                location.hash = sym.anchor;
            }
        }
        else {
            location.href = target.href;
        }
    }

    backdrop.addEventListener("click", close);

    list.addEventListener("click", (e) => {
        const li = e.target.closest("li[data-index]");
        if (li && shown[li.dataset.index]) {
            go(shown[li.dataset.index].sym);
        }
    });

    input.addEventListener("input", update);

    palette.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            e.preventDefault();
            close();
        }
        else if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive(activeIndex + 1);
        }
        else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive(activeIndex - 1);
        }
        else if (e.key === "Enter") {
            e.preventDefault();
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
})();
