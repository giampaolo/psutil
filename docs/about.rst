:orphan:

.. _tips:

About this site
===============

This site is built with `Sphinx <https://www.sphinx-doc.org/>`__ on top of its
built-in ``basic`` theme, with a custom layout and a number of additions:

- Dark mode
- Keyboard shortcuts
- Top bar
- On-this-page navigation
- Improved search navigation
- Clickable API references in code blocks
- A "back to top" button

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
   * - ↑ / ↓
     - Navigate search results
   * - Enter
     - Open highlighted search result
   * - Escape
     - Close search / dialog
   * - ?
     - Show this help

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
are clickable. Hover over one of those to see the highlight, then click to jump
to the corresponding API reference doc. This is powered by
`sphinx-codeautolink <https://sphinx-codeautolink.readthedocs.io/>`__.
