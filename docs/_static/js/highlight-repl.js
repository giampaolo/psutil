// Syntax-highlight REPL inside pycon output spans (class="go").
// Pygments tokenizes >>> lines as Python, but leaves output as plain
// Generic.Output.

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".highlight-pycon .go").forEach(function (span) {
        var html = span.innerHTML;
        // Highlight quoted strings (must run first, before we inject spans).
        html = html.replace(/('[^']*'|"[^"]*")/g,
            '<span class="pycon-string">$1</span>');
        // Highlight namedtuple field names (word before '=').
        // The (?!") lookahead avoids matching class= in the injected span tags.
        html = html.replace(/\b([a-z_]\w*)=(?!")/g,
            '<span class="pycon-field">$1</span>=');
        // Highlight numbers.
        html = html.replace(/\b\d+\.?\d*\b/g,
            '<span class="pycon-number">$&</span>');
        span.innerHTML = html;
    });
});
