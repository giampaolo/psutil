// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// On @ key press, show a go-to symbol menu, to jump to API symbols /
// definitions.

(function () {
    if (window.matchMedia("(pointer: coarse)").matches) {
        return;
    }

    const symbols = Array.from(
        document.querySelectorAll("dt.sig-object.py[id]"),
    ).map((dt) => {
        const dl = dt.closest("dl");
        let type = "";
        if (dl) {
            type = Array.from(dl.classList).find((c) => {
                return c !== "py";
            }) || "";
        }
        const name = dt.id.startsWith("psutil.")
            ? dt.id.slice("psutil.".length)
            : dt.id;
        return { id: dt.id, name: name, type: type };
    });

    if (!symbols.length) {
        return;
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
        'placeholder="Jump to symbol" aria-label="Jump to API symbol" ' +
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
            if (idx === 0 || t[idx - 1] === "." || t[idx - 1] === "_") {
                score += 10;
            }
            score -= idx - from;
            positions.push(idx);
            prev = idx;
            from = idx + 1;
        }
        return { score: score, positions: positions };
    }

    function render() {
        list.innerHTML = "";
        if (!shown.length) {
            const li = document.createElement("li");
            li.className = "api-palette-empty";
            li.textContent = "No matching symbols";
            list.appendChild(li);
            return;
        }
        shown.forEach((entry) => {
            const li = document.createElement("li");
            li.setAttribute("role", "option");
            li.dataset.id = entry.sym.id;
            const name = document.createElement("span");
            name.className = "api-palette-name";
            const hits = new Set(entry.positions);
            for (let i = 0; i < entry.sym.name.length; i++) {
                const ch = document.createTextNode(entry.sym.name[i]);
                if (hits.has(i)) {
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
        if (!q) {
            shown = symbols.map((s) => {
                return { sym: s, positions: [], score: 0 };
            });
        }
        else {
            shown = [];
            symbols.forEach((s) => {
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

    function go(id) {
        close();
        if (location.hash === "#" + id) {
            const el = document.getElementById(id);
            if (el) {
                el.scrollIntoView();
            }
        }
        else {
            location.hash = id;
        }
    }

    backdrop.addEventListener("click", close);

    list.addEventListener("click", (e) => {
        const li = e.target.closest("li[data-id]");
        if (li) {
            go(li.dataset.id);
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
                go(shown[activeIndex].sym.id);
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
