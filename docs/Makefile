# Makefile for Sphinx documentation

PYTHON = python3
PYTHONWARNINGS = always,ignore:::sphinx_sitemap,ignore:importing 'Const',ignore:::matplotlib.projections,ignore:::notfound.extension
# sphinx and sphinx-autobuild, both with the same warning filter.
SPHINXBUILD = PYTHONWARNINGS="$(PYTHONWARNINGS)" $(PYTHON) -m sphinx
SPHINXAUTOBUILD = PYTHONWARNINGS="$(PYTHONWARNINGS)" sphinx-autobuild
# Warnings as errors, parallel. Shared by html and autoreload so the
# live preview matches what CI builds.
SPHINXOPTS = --fail-on-warning --jobs=auto
BUILDDIR = _build
DOCTREES = $(BUILDDIR)/doctrees
OUTDIR = $(BUILDDIR)/html
# Builder + source + output shared by html and the autoreload targets.
DIRHTML = -b dirhtml -d $(DOCTREES) . $(OUTDIR)

# --- sphinx

clean:  ## Remove all build files
	rm -rf $(BUILDDIR)

html:  ## Generate doc in HTML format. Warnings are turned into failures.
	$(SPHINXBUILD) $(SPHINXOPTS) $(DIRHTML)
	@echo "Build finished. The HTML pages are in $(OUTDIR)."

autoreload:  ## Rebuild HTML + live-reload browser on file changes (requires sphinx-autobuild)
	$(SPHINXAUTOBUILD) $(SPHINXOPTS) $(DIRHTML)

autoreload-hard:  ## Same as above but re-writes all files on every refresh
	make clean
	$(SPHINXAUTOBUILD) $(SPHINXOPTS) -a $(DIRHTML)

# --- checkers

check-links:  ## Check links
	$(SPHINXBUILD) $(SPHINXOPTS) -b linkcheck -d $(DOCTREES) . $(BUILDDIR)/linkcheck
	@echo "Link check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/linkcheck/output.txt."

check-codeautolink:  ## Report sphinx-codeautolink resolution failures (non-fatal).
	$(MAKE) clean
	$(PYTHON) -m sphinx --jobs=auto \
		-D codeautolink_warn_on_failed_resolve=1 \
		-D codeautolink_warn_on_missing_inventory=1 \
		-b html -d $(DOCTREES) . $(OUTDIR) 2>&1

# --- tests

test:  ## Run doc sanity tests.
	$(PYTHON) -m pytest test_docs.py $(ARGS)

test-online-doc:  ## Smoke tests against the live docs site.
	PSUTIL_DOCS_ONLINE=1 $(PYTHON) -m pytest test_docs_online.py -v

# --- tools

blog-post:  ## Create a new blog post skeleton
	@test -n "$(SLUG)" || { echo "Usage: make blog-post SLUG=<slug> [TITLE=<text>] [TAGS=<csv>]"; exit 1; }
	$(PYTHON) ../scripts/internal/new_blog_post.py "$(SLUG)"$(if $(TITLE), --title "$(TITLE)")$(if $(TAGS), --tags "$(TAGS)")

refresh-adoption-stats:  ## Refresh PyPI/GitHub stats in adoption.rst and README.rst
	$(PYTHON) ../scripts/internal/refresh_adoption_stats.py
	$(MAKE) -C .. fix-rst

help: ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
