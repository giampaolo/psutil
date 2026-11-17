// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Syntax-highlight REPL inside pycon output spans (class="go").
// Pygments tokenizes >>> lines as Python, but leaves output as plain
// Generic.Output.

document.querySelectorAll(".highlight-pycon .go").forEach((span) => {
    let html = span.innerHTML;
    // Highlight quoted strings (must run first, before we inject spans).
    html = html.replace(
        /('[^']*'|"[^"]*")/g,
        '<span class="pycon-string">$1</span>',
    );
    // Highlight namedtuple field names (word before '=').
    // The (?!") lookahead avoids matching class= in the injected span tags.
    html = html.replace(
        /\b([a-z_]\w*)=(?!")/g,
        '<span class="pycon-field">$1</span>=',
    );
    // Highlight standalone numbers, skipping the ones inside strings.
    html = html
        .split(/(<span class="pycon-string">.*?<\/span>)/)
        .map((part, i) => {
            if (i % 2 === 1) {
                return part;
            }
            return part.replace(
                /(?<![\w.])\d+(?:\.\d+)?(?![\w.])/g,
                '<span class="pycon-number">$&</span>',
            );
        })
        .join("");
    span.innerHTML = html;
});

// Mark function calls (a name followed by "("). Pygments tokenizes
// them as plain names. codeautolink wraps dotted names in an <a>.
document.querySelectorAll(".highlight .p").forEach((p) => {
    if (!p.textContent.startsWith("(")) {
        return;
    }
    let prev = p.previousElementSibling;
    if (prev && prev.tagName === "A") {
        prev = prev.lastElementChild;
    }
    if (prev && prev.matches(".n, .nb")) {
        prev.classList.add("fn-call");
    }
});

// Disable title showing up on hover.
document.querySelectorAll("a.sphinx-codeautolink-a[title]").forEach((a) => {
    a.removeAttribute("title");
});
