# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run: "make install PYTHON=python3.3"
# You can set the variables below from the command line.

# Configurable.
PYTHON = python3
ARGS =
TSCRIPT = psutil/tests/runner.py

# Internal.
DEPS = \
	argparse \
	check-manifest \
	concurrencytest \
	coverage \
	flake8 \
	flake8-print \
	pyperf \
	pypinfo \
	requests \
	setuptools \
	twine \
	virtualenv \
	wheel
PY2_DEPS = \
	futures \
	ipaddress \
	mock==1.0.1 \
	unittest2
DEPS += `$(PYTHON) -c \
	"import sys; print('$(PY2_DEPS)' if sys.version_info[0] == 2 else '')"`
# "python3 setup.py build" can be parallelized on Python >= 3.6.
BUILD_OPTS = `$(PYTHON) -c \
	"import sys, os; \
	py36 = sys.version_info[:2] >= (3, 6); \
	cpus = os.cpu_count() or 1 if py36 else 1; \
	print('--parallel %s' % cpus if cpus > 1 else '')"`
# In not in a virtualenv, add --user options for install commands.
INSTALL_OPTS = `$(PYTHON) -c \
	"import sys; print('' if hasattr(sys, 'real_prefix') else '--user')"`
TEST_PREFIX = PYTHONWARNINGS=always PSUTIL_TESTING=1 PSUTIL_DEBUG=1

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
		*\@psutil-* \
		.coverage \
		.failed-tests.txt \
		build/ \
		dist/ \
		docs/_build/ \
		htmlcov/

_:

build: _  ## Compile (in parallel) without installing.
	@# "build_ext -i" copies compiled *.so files in ./psutil directory in order
	@# to allow "import psutil" when using the interactive interpreter from
	@# within  this directory.
	PYTHONWARNINGS=all $(PYTHON) setup.py build_ext -i $(BUILD_OPTS)

install:  ## Install this package as current user in "edit" mode.
	# make sure setuptools is installed (needed for 'develop' / edit mode)
	$(PYTHON) -c "import setuptools"
	${MAKE} build
	PYTHONWARNINGS=all $(PYTHON) setup.py develop $(INSTALL_OPTS)
	$(PYTHON) -c "import psutil"  # make sure it actually worked

uninstall:  ## Uninstall this package via pip.
	cd ..; $(PYTHON) -m pip uninstall -y -v psutil || true
	$(PYTHON) scripts/internal/purge_installation.py

install-pip:  ## Install pip (no-op if already installed).
	@$(PYTHON) -c \
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
		code = os.system('%s %s --user --upgrade' % (sys.executable, f.name)); \
		f.close(); \
		sys.exit(code);"

setup-dev-env:  ## Install GIT hooks, pip, test deps (also upgrades them).
	${MAKE} install-git-hooks
	${MAKE} install-pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade --trusted-host files.pythonhosted.org pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade --trusted-host files.pythonhosted.org $(DEPS)

# ===================================================================
# Tests
# ===================================================================

test:  ## Run all tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS)

test-parallel:  ## Run all tests in parallel.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) --parallel

test-process:  ## Run process-related API tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_process.py

test-system:  ## Run system-related API tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_system.py

test-misc:  ## Run miscellaneous tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_misc.py

test-testutils:  ## Run test utils tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_testutils.py

test-unicode:  ## Test APIs dealing with strings.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_unicode.py

test-contracts:  ## APIs sanity tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_contracts.py

test-connections:  ## Test net_connections() and Process.connections().
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_connections.py

test-posix:  ## POSIX specific tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_posix.py

test-platform:  ## Run specific platform tests only.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS", "AIX") if getattr(psutil, x)][0])'`.py

test-memleaks:  ## Memory leak tests.
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) psutil/tests/test_memleaks.py

test-by-name:  ## e.g. make test-by-name ARGS=psutil.tests.test_system.TestSystemAPIs
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS)

test-failed:  ## Re-run tests which failed on last run
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) $(TSCRIPT) $(ARGS) --last-failed

test-coverage:  ## Run test coverage.
	${MAKE} build
	# Note: coverage options are controlled by .coveragerc file
	rm -rf .coverage htmlcov
	$(TEST_PREFIX) $(PYTHON) -m coverage run $(TSCRIPT)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

# ===================================================================
# Linters
# ===================================================================

lint-py:  ## Run Python (flake8) linter.
	@git ls-files '*.py' | xargs $(PYTHON) -m flake8 --config=.flake8

lint-c:  ## Run  C linter.
	@git ls-files '*.c' '*.h' | xargs $(PYTHON) scripts/internal/clinter.py

lint:  ## Run Python (flake8) and C linters.
	${MAKE} lint-py
	${MAKE} lint-c

fix-lint:  ## Attempt to automatically fix some Python lint issues.
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m flake8 --exit-zero | $(PYTHON) scripts/internal/fix_flake8.py

# ===================================================================
# GIT
# ===================================================================

install-git-hooks:  ## Install GIT pre-commit hook.
	ln -sf ../../scripts/internal/git_pre_commit.py .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# ===================================================================
# Wheels
# ===================================================================

download-wheels-github:  ## Download latest wheels hosted on github.
	$(PYTHON) scripts/internal/download_wheels_github.py --user=giampaolo --project=psutil --tokenfile=~/.github.token

download-wheels-appveyor:  ## Download latest wheels hosted on appveyor.
	$(PYTHON) scripts/internal/download_wheels_appveyor.py --user giampaolo --project psutil

print-wheels:  ## Print downloaded wheels
	$(PYTHON) scripts/internal/print_wheels.py

# ===================================================================
# Distribution
# ===================================================================

git-tag-release:  ## Git-tag a new release.
	git tag -a release-`python -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

sdist:  ## Create tar.gz source distribution.
	${MAKE} generate-manifest
	$(PYTHON) setup.py sdist
	$(PYTHON) -m twine check dist/*.tar.gz

upload-src:  ## Upload source tarball on https://pypi.org/project/psutil/
	${MAKE} sdist
	$(PYTHON) -m twine upload dist/*.tar.gz

upload-wheels:  ## Upload wheels in dist/* directory on PyPI.
	$(PYTHON) -m twine upload dist/*.whl

# --- others

check-sdist:  ## Create source distribution and checks its sanity (MANIFEST)
	rm -rf dist
	${MAKE} clean
	$(PYTHON) -m virtualenv --clear --no-wheel --quiet build/venv
	PYTHONWARNINGS=all $(PYTHON) setup.py sdist
	build/venv/bin/python -m pip install -v --isolated --quiet dist/*.tar.gz
	build/venv/bin/python -c "import os; os.chdir('build/venv'); import psutil"

tidelift-relnotes:  ## upload release notes from HISTORY
	$(PYTHON) scripts/internal/tidelift.py

pre-release:  ## Check if we're ready to produce a new release.
	${MAKE} check-sdist
	${MAKE} install
	${MAKE} generate-manifest
	git diff MANIFEST.in > /dev/null  # ...otherwise 'git diff-index HEAD' will complain
	${MAKE} sdist
	${MAKE} download-wheels-github
	${MAKE} download-wheels-appveyor
	${MAKE} print-wheels
	$(PYTHON) -m twine check dist/*
	$(PYTHON) -c \
		"from psutil import __version__ as ver; \
		doc = open('docs/index.rst').read(); \
		history = open('HISTORY.rst').read(); \
		assert ver in doc, '%r not in docs/index.rst' % ver; \
		assert ver in history, '%r not in HISTORY.rst' % ver; \
		assert 'XXXX' not in history, 'XXXX in HISTORY.rst';"

release:  ## Create a release (down/uploads tar.gz, wheels, git tag release).
	$(PYTHON) -c "import subprocess, sys; out = subprocess.check_output('git diff --quiet && git diff --cached --quiet', shell=True).strip(); sys.exit('there are uncommitted changes:\n%s' % out) if out else 0 ;"
	$(PYTHON) -m twine upload dist/*  # upload tar.gz and Windows wheels on PyPI
	${MAKE} git-tag-release
	${MAKE} tidelift-relnotes

check-manifest:  ## Inspect MANIFEST.in file.
	$(PYTHON) -m check_manifest -v $(ARGS)

generate-manifest:  ## Generates MANIFEST.in file.
	$(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

# ===================================================================
# Printers
# ===================================================================

print-announce:  ## Print announce of new release.
	@$(PYTHON) scripts/internal/print_announce.py

print-timeline:  ## Print releases' timeline.
	@$(PYTHON) scripts/internal/print_timeline.py

print-access-denied: ## Print AD exceptions
	${MAKE} build
	@$(TEST_PREFIX) $(PYTHON) scripts/internal/print_access_denied.py

print-api-speed:  ## Benchmark all API calls
	${MAKE} build
	@$(TEST_PREFIX) $(PYTHON) scripts/internal/print_api_speed.py $(ARGS)

print-downloads:  ## Print PYPI download statistics
	$(PYTHON) scripts/internal/print_downloads.py

print-hashes:  ## Prints hashes of files in dist/ directory
	$(PYTHON) scripts/internal/print_hashes.py dist/

# ===================================================================
# Misc
# ===================================================================

grep-todos:  ## Look for TODOs in the source files.
	git grep -EIn "TODO|FIXME|XXX"

bench-oneshot:  ## Benchmarks for oneshot() ctx manager (see #799).
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) scripts/internal/bench_oneshot.py

bench-oneshot-2:  ## Same as above but using perf module (supposed to be more precise)
	${MAKE} build
	$(TEST_PREFIX) $(PYTHON) scripts/internal/bench_oneshot_2.py

check-broken-links:  ## Look for broken links in source files.
	git ls-files | xargs $(PYTHON) -Wa scripts/internal/check_broken_links.py

help: ## Display callable targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
