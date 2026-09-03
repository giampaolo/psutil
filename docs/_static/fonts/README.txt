Self-hosted web fonts (latin subset), wired up in ../css/fonts.css.

All three families are licensed under the SIL Open Font License 1.1.
The full license text ships with each upstream project (linked below);
see also https://openfontlicense.org.

- Inter
  Copyright (c) The Inter Project Authors.
  https://github.com/rsms/inter

- JetBrains Mono
  Copyright (c) The JetBrains Mono Project Authors.
  https://github.com/JetBrains/JetBrainsMono

- Merriweather
  Copyright (c) The Merriweather Project Authors.
  https://github.com/SorkinType/Merriweather

Files were generated from the Google Fonts css2 API (latin unicode-range
only), then trimmed of unused OpenType features with pyftsubset:

  pyftsubset FONT.woff2 --unicodes='*' --layout-features='kern,liga,tnum' \
    --no-hinting --flavor=woff2 --output-file=FONT.woff2

The fa-*-subset.woff2 files contain only the glyphs the theme uses. To
add one, take the full font from the FontAwesome web release and re-run
pyftsubset with the current codepoints (read them from the shipped
subset with fontTools' getBestCmap()) plus the new one:

  pyftsubset fa-solid-900.woff2 --unicodes=U+F002,...,U+FNEW \
    --no-hinting --flavor=woff2 --output-file=fa-solid-subset.woff2
