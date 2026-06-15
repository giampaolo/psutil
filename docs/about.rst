:orphan:

.. _tips:

About this site
===============

This site is built with `Sphinx <https://www.sphinx-doc.org/>`__, on top of its
built-in ``basic`` theme. From there it has been heavily customized: the
layout, navigation, search, dark mode, code blocks, mobile behavior, and many
small details were rebuilt or extended specifically for these docs.

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
      :alt: Light mode
      :class: about-shot

   .. image:: /_static/images/about/darkmode-dark.png
      :alt: Dark mode
      :class: about-shot

Clickable API references
------------------------

Identifiers in code blocks (e.g. ``p = psutil.Process()``, ``p.cpu_percent()``)
are clickable. Hover over one of those to see the highlight, then click to jump
to the corresponding API reference doc. This is powered by
`sphinx-codeautolink <https://sphinx-codeautolink.readthedocs.io/>`__.

.. image:: /_static/images/about/clickable.png
   :alt: Clickable API reference
   :class: about-shot

Copy buttons
------------

Every code block has a copy button in its top-right corner which appears on
hover. For interactive (``>>>``) examples it copies just the code, leaving out
the prompts and the output, so you can paste it straight into a shell.

.. image:: /_static/images/about/copy.png
   :alt: Copy button
   :class: about-shot

Search
------

Press :kbd:`Ctrl+K` to jump straight to the search box. Once results appear,
use the :kbd:`↑` and :kbd:`↓` arrow keys to move through them and :kbd:`Enter`
to open one.

.. image:: /_static/images/about/search.png
   :alt: Search results
   :class: about-shot

TOC / On this page
------------------

Wide screens show an "On this page" sidebar on the right, listing the current
page's sections. As you scroll it highlights the section you're in, and
clicking an entry jumps straight to it.

.. image:: /_static/images/about/toc.png
   :alt: On this page outline
   :class: about-shot

Back to top
-----------

On a long page, start scrolling back up and a small button will appear in the
bottom-right corner. Click it to go back to the top of the page.

.. image:: /_static/images/about/backtotop.png
   :alt: Back-to-top button
   :class: about-shot

Reading on mobile
-----------------

On a phone the navigation collapses behind the **☰** button in the top bar. Tap
it to open the menu, then swipe left anywhere on the page (or tap outside it)
to close it again.

.. image:: /_static/images/about/mobile.png
   :alt: Mobile sidebar
   :class: about-shot

Blog
----

New releases and deep-dives are written up on the :doc:`blog <blog>`. Blog
provides a RSS feed (the icon at the top of the blog page) so you can receive
notifications of new blog posts from your reader.

Other internal optimizations
----------------------------

- Fonts and icons are served directly from this site, not from third-party CDNs
  (e.g. Google fonts). This way docs renders the same from all countries (e.g.
  mainland China). Each font is subsetted to just the glyphs used here, so the
  download stays small.

- Links to this site shared on social medias show rich preview cards.

- Every page declares a canonical URL and is listed in a generated
  ``sitemap.xml``, so search engines can discover and index the whole site.

- Every Python code snippet is syntax-checked when the docs are built.

- Broken links and unresolved API cross-references make the build fail.

Linking from your own docs
--------------------------

Other Sphinx projects can cross-reference psutil's API directly through the
`intersphinx <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_
extension. Add psutil to ``intersphinx_mapping`` in your ``conf.py``:

.. code-block:: python

   intersphinx_mapping = {
       "psutil": ("https://psutil.readthedocs.io/latest/", None),
   }

You can then reference any psutil object and it links straight here, e.g.:

.. code-block:: rst

   See :func:`psutil.cpu_times` function.

This will automatically turn ``psutil.cpu_times`` into a link pointing to this
site.
