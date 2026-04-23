:orphan:

.. _tips:

About this site
===============

This site is built with `Sphinx <https://www.sphinx-doc.org/>`__ and the
`Read the Docs theme <https://sphinx-rtd-theme.readthedocs.io/>`__, with a
number of custom additions: a dark mode, keyboard shortcuts, a top bar, an
improved search navigation, and clickable API references in code blocks.

Keyboard shortcuts
------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Key
     - Action
   * - Ctrl+K
     - Open search
   * - Shift+D
     - Toggle dark / light mode
   * - ↓ / ↑
     - Navigate search results
   * - Enter
     - Open highlighted search result
   * - Escape
     - Close search

Dark mode
---------

Click the moon icon in the top-right corner, or press **Shift+D** anywhere on
the page. Your preference is saved and restored on your next visit.

Search
------

Press **Ctrl+K** to jump straight to the search box. Once results appear, use
the **arrow keys** to move through them and **Enter** to open one — no mouse
needed.

Clickable API references
------------------------

Identifiers in code blocks (e.g. ``p = psutil.Process()``, ``p.cpu_percent()``)
are links to their API reference entry. Hover over one to see the highlight,
then click to jump. This is powered by
`sphinx-codeautolink <https://sphinx-codeautolink.readthedocs.io/>`__.
