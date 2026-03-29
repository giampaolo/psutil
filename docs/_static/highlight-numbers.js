// Syntax-highlight numbers and strings inside pycon output spans (class="go").
// Pygments tokenizes >>> lines as Python, but leaves output as plain
// Generic.Output.

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".highlight-pycon .go").forEach(function (span) {
        span.innerHTML = span.innerHTML.replace(
            /('[^']*'|"[^"]*"|\b[a-z]\w*(?=\()|\b\d+\.?\d*\b)/g,
            function (match) {
                var cls;
                if (match[0] === "'" || match[0] === '"')
                    cls = "pycon-string";
                else if (/^[a-z]/.test(match))
                    cls = "pycon-name";
                else
                    cls = "pycon-number";
                return '<span class="' + cls + '">' + match + '</span>';
            }
        );
    });
});
