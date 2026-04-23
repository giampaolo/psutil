# Makefile for Sphinx documentation

PYTHON = python3
SPHINXBUILD = PYTHONWARNINGS="always,ignore:::sphinx_sitemap" $(PYTHON) -m sphinx
BUILDDIR = _build
ALLSPHINXOPTS = --fail-on-warning --nitpicky --jobs=auto -d $(BUILDDIR)/doctrees .

clean:  ## Remove all build files
	rm -rf $(BUILDDIR)

html:  ## Generate doc in HTML format. Warnings are turned into failures.
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

autoreload:  ## Rebuild HTML + live-reload browser on file changes (requires sphinx-autobuild)
	sphinx-autobuild --nitpicky -d $(BUILDDIR)/doctrees . $(BUILDDIR)/html

autoreload-hard:  ## Same as above but re-writes all files on every refresh
	make clean
	sphinx-autobuild -a --nitpick -d $(BUILDDIR)/doctrees . $(BUILDDIR)/html

check-links:  ## Check links
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) $(BUILDDIR)/linkcheck
	@echo "Link check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/linkcheck/output.txt."

blog-post:  ## Create a new blog post skeleton
	@test -n "$(SLUG)" || { echo "Usage: make blog-post SLUG=<slug> [TITLE=<text>] [TAGS=<csv>]"; exit 1; }
	$(PYTHON) ../scripts/internal/new_blog_post.py "$(SLUG)"$(if $(TITLE), --title "$(TITLE)")$(if $(TAGS), --tags "$(TAGS)")

help: ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
