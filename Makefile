# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run: "make install PYTHON=python3.3"
# You can set the variables below from the command line.

PYTHON = python
TSCRIPT = psutil/tests/__main__.py
ARGS =
# List of nice-to-have dev libs.
DEPS = \
	argparse \
	check-manifest \
	coverage \
	flake8 \
	futures \
	ipaddress \
	mock==1.0.1 \
	pep8 \
	perf \
	pyflakes \
	requests \
	setuptools \
	sphinx \
	twine \
	unittest2 \
	requests

# In not in a virtualenv, add --user options for install commands.
INSTALL_OPTS = `$(PYTHON) -c "import sys; print('' if hasattr(sys, 'real_prefix') else '--user')"`

all: test

# ===================================================================
# Install
# ===================================================================

clean:  ## Remove all build files.
	rm -rf `find . -type d -name __pycache__ \
		-o -type f -name \*.bak \
		-o -type f -name \*.orig \
		-o -type f -name \*.pyc \
		-o -type f -name \*.pyd \
		-o -type f -name \*.pyo \
		-o -type f -name \*.rej \
		-o -type f -name \*.so \
		-o -type f -name \*.~ \
		-o -type f -name \*\$testfn`
	rm -rf \
		*.core \
		*.egg-info \
		*\$testfn* \
		.coverage \
		.tox \
		build/ \
		dist/ \
		docs/_build/ \
		htmlcov/ \
		tmp/

_:

build: _  ## Compile without installing.
	# make sure setuptools is installed (needed for 'develop' / edit mode)
	$(PYTHON) -c "import setuptools"
	PYTHONWARNINGS=all $(PYTHON) setup.py build
	@# copies compiled *.so files in ./psutil directory in order to allow
	@# "import psutil" when using the interactive interpreter from within
	@# this directory.
	PYTHONWARNINGS=all $(PYTHON) setup.py build_ext -i
	rm -rf tmp
	$(PYTHON) -c "import psutil"  # make sure it actually worked

install:  ## Install this package as current user in "edit" mode.
	${MAKE} build
	PYTHONWARNINGS=all $(PYTHON) setup.py develop $(INSTALL_OPTS)
	rm -rf tmp

uninstall:  ## Uninstall this package via pip.
	cd ..; $(PYTHON) -m pip uninstall -y -v psutil

install-pip:  ## Install pip (no-op if already installed).
	$(PYTHON) -c \
		"import sys, ssl, os, pkgutil, tempfile, atexit; \
		sys.exit(0) if pkgutil.find_loader('pip') else None; \
		pyexc = 'from urllib.request import urlopen' if sys.version_info[0] == 3 else 'from urllib2 import urlopen'; \
		exec(pyexc); \
		ctx = ssl._create_unverified_context() if hasattr(ssl, '_create_unverified_context') else None; \
		kw = dict(context=ctx) if ctx else {}; \
		req = urlopen('https://bootstrap.pypa.io/get-pip.py', **kw); \
		data = req.read(); \
		f = tempfile.NamedTemporaryFile(suffix='.py'); \
		atexit.register(f.close); \
		f.write(data); \
		f.flush(); \
		print('downloaded %s' % f.name); \
		code = os.system('%s %s --user' % (sys.executable, f.name)); \
		f.close(); \
		sys.exit(code);"

setup-dev-env:  ## Install GIT hooks, pip, test deps (also upgrades them).
	${MAKE} install-git-hooks
	${MAKE} install-pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade $(DEPS)

# ===================================================================
# Tests
# ===================================================================

test:  ## Run all tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) $(TSCRIPT)

test-process:  ## Run process-related API tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v psutil.tests.test_process

test-system:  ## Run system-related API tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v psutil.tests.test_system

test-misc:  ## Run miscellaneous tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_misc.py

test-unicode:  ## Test APIs dealing with strings.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_unicode.py

test-contracts:  ## APIs sanity tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_contracts.py

test-connections:  ## Test net_connections() and Process.connections().
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_connections.py

test-posix:  ## POSIX specific tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_posix.py

test-platform:  ## Run specific platform tests only.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS", "AIX") if getattr(psutil, x)][0])'`.py

test-memleaks:  ## Memory leak tests.
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_memory_leaks.py

test-by-name:  ## e.g. make test-by-name ARGS=psutil.tests.test_system.TestSystemAPIs
	${MAKE} install
	@PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v $(ARGS)

test-coverage:  ## Run test coverage.
	${MAKE} install
	# Note: coverage options are controlled by .coveragerc file
	rm -rf .coverage htmlcov
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m coverage run $(TSCRIPT)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

# ===================================================================
# Linters
# ===================================================================

pep8:  ## PEP8 linter.
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m pep8

pyflakes:  ## Pyflakes linter.
	@export PYFLAKES_NODOCTEST=1 && \
		git ls-files | grep \\.py$ | xargs $(PYTHON) -m pyflakes

flake8:  ## flake8 linter.
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m flake8

# ===================================================================
# GIT
# ===================================================================

git-tag-release:  ## Git-tag a new release.
	git tag -a release-`python -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

install-git-hooks:  ## Install GIT pre-commit hook.
	ln -sf ../../.git-pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# ===================================================================
# Distribution
# ===================================================================

sdist:  ## Generate tar.gz source distribution.
	${MAKE} generate-manifest
	$(PYTHON) setup.py sdist

upload-src:  ## Upload source tarball on https://pypi.python.org/pypi/psutil.
	${MAKE} sdist
	$(PYTHON) setup.py sdist upload

win-download-exes:  ## Download exes/wheels hosted on appveyor.
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/download_exes.py --user giampaolo --project psutil

win-upload-exes:  ## Upload wheels in dist/* directory on PYPI.
	$(PYTHON) -m twine upload dist/*.whl

pre-release:  ## Check if we're ready to produce a new release.
	${MAKE} install
	$(PYTHON) -c \
		"from psutil import __version__ as ver; \
		doc = open('docs/index.rst').read(); \
		history = open('HISTORY.rst').read(); \
		assert ver in doc, '%r not in docs/index.rst' % ver; \
		assert ver in history, '%r not in HISTORY.rst' % ver; \
		assert 'XXXX' not in history, 'XXXX in HISTORY.rst';"
	${MAKE} generate-manifest
	git diff MANIFEST.in > /dev/null  # ...otherwise 'git diff-index HEAD' will complain
	$(PYTHON) -c "import subprocess, sys; out = subprocess.check_output('git diff-index HEAD --', shell=True).strip(); sys.exit('there are uncommitted changes:\n%s' % out) if out else sys.exit(0);"
	${MAKE} win-download-exes
	${MAKE} sdist

release:  ## Create a release (down/uploads tar.gz, wheels, git tag release).
	${MAKE} pre-release
	$(PYTHON) -m twine upload dist/*  # upload tar.gz and Windows wheels on PYPI
	${MAKE} git-tag-release

print-announce:  ## Print announce of new release.
	@PYTHONWARNINGS=all $(PYTHON) scripts/internal/print_announce.py

print-timeline:  ## Print releases' timeline.
	@PYTHONWARNINGS=all $(PYTHON) scripts/internal/print_timeline.py

check-manifest:  ## Inspect MANIFEST.in file.
	$(PYTHON) -m check_manifest -v $(ARGS)

generate-manifest:  ## Generates MANIFEST.in file.
	$(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

# ===================================================================
# Misc
# ===================================================================

grep-todos:  ## Look for TODOs in the source files.
	git grep -EIn "TODO|FIXME|XXX"

bench-oneshot:  ## Benchmarks for oneshot() ctx manager (see #799).
	${MAKE} install
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/bench_oneshot.py

bench-oneshot-2:  ## Same as above but using perf module (supposed to be more precise)
	${MAKE} install
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/bench_oneshot_2.py

check-broken-links:  ## Look for broken links in source files.
		git ls-files | xargs $(PYTHON) -Wa scripts/internal/check_broken_links.py

help: ## Display callable targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
