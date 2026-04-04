// Syntax-highlight REPL inside pycon output spans (class="go").
// Pygments tokenizes >>> lines as Python, but leaves output as plain
// Generic.Output.

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".highlight-pycon .go").forEach(function (span) {
        var html = span.innerHTML;
        html = html.replace(/('[^']*'|"[^"]*")/g,
            '<span class="pycon-string">$1</span>');
        html = html.replace(/\b\d+\.?\d*\b/g,
            '<span class="pycon-number">$&</span>');
        span.innerHTML = html;
    });
});
