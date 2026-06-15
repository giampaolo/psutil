:orphan:

.. _tips:

About this site
===============

This site is built with `Sphinx <https://www.sphinx-doc.org/>`__ on top of its
built-in ``basic`` theme, with a custom layout and a number of additions.

Keyboard shortcuts
------------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Key
     - Action
   * - :kbd:`Shift+D`
     - Toggle dark / light mode
   * - :kbd:`Ctrl+K`
     - Open search
   * - :kbd:`↑` / :kbd:`↓`
     - Navigate search results
   * - :kbd:`Enter`
     - Open highlighted search result
   * - :kbd:`Escape`
     - Close search / dialog
   * - :kbd:`?`
     - Show this help

Dark mode
---------

.. |moon| raw:: html

   <i class="fa-regular fa-moon" aria-hidden="true"></i>

By default the site matches your operating system's light or dark setting.
Click the |moon| icon in the top-right corner, or press :kbd:`Shift+D`
anywhere, to override it. Your choice is saved and restored on your next visit.

.. container:: about-shot-pair

   .. image:: /_static/images/about/darkmode-light.png
      :alt: A docs page in light mode
      :class: about-shot

   .. image:: /_static/images/about/darkmode-dark.png
      :alt: The same page in dark mode
      :class: about-shot

Clickable API references
------------------------

Identifiers in code blocks (e.g. ``p = psutil.Process()``, ``p.cpu_percent()``)
are clickable. Hover over one of those to see the highlight, then click to jump
to the corresponding API reference doc. This is powered by
`sphinx-codeautolink <https://sphinx-codeautolink.readthedocs.io/>`__.

.. image:: /_static/images/about/clickable.png
   :alt: A hovered identifier in a code block, highlighted and linking to the API reference
   :class: about-shot

Copy buttons
------------

Every code block has a copy button in its top-right corner which appears on
hover. For interactive (``>>>``) examples it copies just the code, leaving out
the prompts and the output, so you can paste it straight into a shell.

.. image:: /_static/images/about/copy.png
   :alt: A code block with its copy button in the top-right corner
   :class: about-shot

Search
------

Press :kbd:`Ctrl+K` to jump straight to the search box. Once results appear,
use the :kbd:`↑` and :kbd:`↓` arrow keys to move through them and :kbd:`Enter`
to open one.

.. image:: /_static/images/about/search.png
   :alt: The search results page, with matches and context snippets
   :class: about-shot

Permalink anchors
-----------------

Hover over any heading and a small link icon appears next to it. Click it to
jump there, or copy it to share a link that points straight to that section.

.. image:: /_static/images/about/permalink.png
   :alt: Permalink icon on hover
   :class: about-shot

Reading on mobile
-----------------

On a phone the navigation collapses behind the **☰** button in the top bar. Tap
it to open the menu, then swipe left anywhere on the page (or tap outside it)
to close it again.

.. image:: /_static/images/about/mobile.png
   :alt: Left sidebar on mobile
   :class: about-shot

Blog
----

New releases and deep-dives are written up on the :doc:`blog <blog>`. Blog
provides a **RSS feed** (the icon at the top of the blog page) so you can
receive notifications of new blog posts from your reader.

Other internal optimizations
----------------------------

A few things under the hood: the fonts and icons are self-hosted, so there are
no third-party CDN requests, and the docs render fully even on restrictive
networks. The pages target WCAG AA contrast, are fully keyboard-navigable, and
honor your "reduce motion" setting.
