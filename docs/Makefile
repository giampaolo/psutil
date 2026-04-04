# Makefile for Sphinx documentation

PYTHON = python3
SPHINXBUILD = $(PYTHON) -m sphinx
BUILDDIR = _build
ALLSPHINXOPTS = --fail-on-warning --nitpicky --jobs=auto -d $(BUILDDIR)/doctrees .

clean:  ## Remove all build files
	rm -rf $(BUILDDIR)

html:  ## Generate doc in HTML format
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

singlehtml:  ## Generate doc as a single HTML page
	$(SPHINXBUILD) -b singlehtml $(ALLSPHINXOPTS) $(BUILDDIR)/singlehtml
	@echo "Build finished. The HTML page is in $(BUILDDIR)/singlehtml."

text:  ## Generate doc in .txt format
	$(SPHINXBUILD) -b text $(ALLSPHINXOPTS) $(BUILDDIR)/text
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

auto-build:  ## Rebuild HTML on file changes (requires inotify-tools)
	$(MAKE) clean
	$(MAKE) html
	while inotifywait -r -e modify,create,delete,move .; do $(MAKE) html; done

check-links:  ## Check links
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) $(BUILDDIR)/linkcheck
	@echo "Link check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/linkcheck/output.txt."

help: ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
