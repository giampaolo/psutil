# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run: "make install PYTHON=python3.3"
# You can set the variables below from the command line.

PYTHON = python3
PYTHON_ENV_VARS = PYTHONWARNINGS=always PYTHONUNBUFFERED=1 PSUTIL_DEBUG=1
PYTEST_ARGS = -v -s --tb=short
ARGS =

# mandatory deps for running tests
PY3_DEPS = \
	setuptools \
	pytest \
	pytest-xdist

# deps for local development
ifndef CIBUILDWHEEL
	PY3_DEPS += \
		black \
		check-manifest \
		coverage \
		packaging \
		pylint \
		pyperf \
		pypinfo \
		pytest-cov \
		requests \
		rstcheck \
		ruff \
		setuptools \
		sphinx_rtd_theme \
		toml-sort \
		twine \
		virtualenv \
		wheel
endif

# python 2 deps
PY2_DEPS = \
	futures \
	ipaddress \
	mock==1.0.1 \
	pytest==4.6.11 \
	pytest-xdist \
	setuptools

PY_DEPS = `$(PYTHON) -c \
	"import sys; \
	py3 = sys.version_info[0] == 3; \
	py38 = sys.version_info[:2] >= (3, 8); \
	py3_extra = ' abi3audit' if py38 else ''; \
	print('$(PY3_DEPS)' + py3_extra if py3 else '$(PY2_DEPS)')"`

NUM_WORKERS = `$(PYTHON) -c "import os; print(os.cpu_count() or 1)"`

# "python3 setup.py build" can be parallelized on Python >= 3.6.
BUILD_OPTS = `$(PYTHON) -c \
	"import sys, os; \
	py36 = sys.version_info[:2] >= (3, 6); \
	cpus = os.cpu_count() or 1 if py36 else 1; \
	print('--parallel %s' % cpus if cpus > 1 else '')"`

# In not in a virtualenv, add --user options for install commands.
INSTALL_OPTS = `$(PYTHON) -c \
	"import sys; print('' if hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix else '--user')"`

# if make is invoked with no arg, default to `make help`
.DEFAULT_GOAL := help

# ===================================================================
# Install
# ===================================================================

clean:  ## Remove all build files.
	@rm -rfv `find . \
		-type d -name __pycache__ \
		-o -type f -name \*.bak \
		-o -type f -name \*.orig \
		-o -type f -name \*.pyc \
		-o -type f -name \*.pyd \
		-o -type f -name \*.pyo \
		-o -type f -name \*.rej \
		-o -type f -name \*.so \
		-o -type f -name \*.~ \
		-o -type f -name \*\$testfn`
	@rm -rfv \
		*.core \
		*.egg-info \
		*\@psutil-* \
		.coverage \
		.failed-tests.txt \
		.pytest_cache \
		.ruff_cache/ \
		build/ \
		dist/ \
		docs/_build/ \
		htmlcov/ \
		wheelhouse

.PHONY: build
build:  ## Compile (in parallel) without installing.
	@# "build_ext -i" copies compiled *.so files in ./psutil directory in order
	@# to allow "import psutil" when using the interactive interpreter from
	@# within  this directory.
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py build_ext -i $(BUILD_OPTS)
	$(PYTHON_ENV_VARS) $(PYTHON) -c "import psutil"  # make sure it actually worked

install:  ## Install this package as current user in "edit" mode.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py develop $(INSTALL_OPTS)
	$(PYTHON_ENV_VARS) $(PYTHON) -c "import psutil"  # make sure it actually worked

uninstall:  ## Uninstall this package via pip.
	cd ..; $(PYTHON_ENV_VARS) $(PYTHON) -m pip uninstall -y -v psutil || true
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/purge_installation.py

install-pip:  ## Install pip (no-op if already installed).
	@$(PYTHON) -c \
		"import sys, ssl, os, pkgutil, tempfile, atexit; \
		sys.exit(0) if pkgutil.find_loader('pip') else None; \
		PY3 = sys.version_info[0] == 3; \
		pyexc = 'from urllib.request import urlopen' if PY3 else 'from urllib2 import urlopen'; \
		exec(pyexc); \
		ctx = ssl._create_unverified_context() if hasattr(ssl, '_create_unverified_context') else None; \
		url = 'https://bootstrap.pypa.io/pip/2.7/get-pip.py' if not PY3 else 'https://bootstrap.pypa.io/get-pip.py'; \
		kw = dict(context=ctx) if ctx else {}; \
		req = urlopen(url, **kw); \
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
	$(PYTHON) -m pip install $(INSTALL_OPTS) --trusted-host files.pythonhosted.org --trusted-host pypi.org --upgrade pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --trusted-host files.pythonhosted.org --trusted-host pypi.org --upgrade $(PY_DEPS)

# ===================================================================
# Tests
# ===================================================================

test:  ## Run all tests. To run a specific test do "make test ARGS=psutil.tests.test_system.TestDiskAPIs"
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) --ignore=psutil/tests/test_memleaks.py $(ARGS)

test-parallel:  ## Run all tests in parallel.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) --ignore=psutil/tests/test_memleaks.py -n auto --dist loadgroup $(ARGS)

test-process:  ## Run process-related API tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_process.py

test-process-all:  ## Run tests which iterate over all process PIDs.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_process_all.py

test-system:  ## Run system-related API tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_system.py

test-misc:  ## Run miscellaneous tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_misc.py

test-testutils:  ## Run test utils tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_testutils.py

test-unicode:  ## Test APIs dealing with strings.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_unicode.py

test-contracts:  ## APIs sanity tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_contracts.py

test-connections:  ## Test psutil.net_connections() and Process.net_connections().
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_connections.py

test-posix:  ## POSIX specific tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_posix.py

test-platform:  ## Run specific platform tests only.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS", "AIX") if getattr(psutil, x)][0])'`.py

test-memleaks:  ## Memory leak tests.
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) $(ARGS) psutil/tests/test_memleaks.py

test-last-failed:  ## Re-run tests which failed on last run
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) -m pytest $(PYTEST_ARGS) --last-failed $(ARGS)

test-coverage:  ## Run test coverage.
	${MAKE} build
	# Note: coverage options are controlled by .coveragerc file
	rm -rf .coverage htmlcov
	$(PYTHON_ENV_VARS) $(PYTHON) -m coverage run -m pytest $(PYTEST_ARGS) --ignore=psutil/tests/test_memleaks.py $(ARGS)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

# ===================================================================
# Linters
# ===================================================================

ruff:  ## Run ruff linter.
	@git ls-files '*.py' | xargs $(PYTHON) -m ruff check --no-cache --output-format=concise

black:  ## Python files linting (via black)
	@git ls-files '*.py' | xargs $(PYTHON) -m black --check --safe

_pylint:  ## Python pylint (not mandatory, just run it from time to time)
	@git ls-files '*.py' | xargs $(PYTHON) -m pylint --rcfile=pyproject.toml --jobs=${NUM_WORKERS}

lint-c:  ## Run C linter.
	@git ls-files '*.c' '*.h' | xargs $(PYTHON) scripts/internal/clinter.py

lint-rst:  ## Run C linter.
	@git ls-files '*.rst' | xargs rstcheck --config=pyproject.toml

lint-toml:  ## Linter for pyproject.toml
	@git ls-files '*.toml' | xargs toml-sort --check

lint-all:  ## Run all linters
	${MAKE} black
	${MAKE} ruff
	${MAKE} lint-c
	${MAKE} lint-rst
	${MAKE} lint-toml

# ===================================================================
# Fixers
# ===================================================================

fix-black:
	@git ls-files '*.py' | xargs $(PYTHON) -m black

fix-ruff:
	@git ls-files '*.py' | xargs $(PYTHON) -m ruff check --no-cache --fix $(ARGS)

fix-toml:  ## Fix pyproject.toml
	@git ls-files '*.toml' | xargs toml-sort

fix-all:  ## Run all code fixers.
	${MAKE} fix-ruff
	${MAKE} fix-black
	${MAKE} fix-toml

# ===================================================================
# GIT
# ===================================================================

install-git-hooks:  ## Install GIT pre-commit hook.
	ln -sf ../../scripts/internal/git_pre_commit.py .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# ===================================================================
# Distribution
# ===================================================================

sdist:  ## Create tar.gz source distribution.
	${MAKE} generate-manifest
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py sdist

download-wheels-github:  ## Download latest wheels hosted on github.
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/download_wheels_github.py --tokenfile=~/.github.token
	${MAKE} print-dist

download-wheels-appveyor:  ## Download latest wheels hosted on appveyor.
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/download_wheels_appveyor.py
	${MAKE} print-dist

create-wheels:  ## Create .whl files
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py bdist_wheel
	${MAKE} check-wheels

check-sdist:  ## Check sanity of source distribution.
	$(PYTHON_ENV_VARS) $(PYTHON) -m virtualenv --clear --no-wheel --quiet build/venv
	$(PYTHON_ENV_VARS) build/venv/bin/python -m pip install -v --isolated --quiet dist/*.tar.gz
	$(PYTHON_ENV_VARS) build/venv/bin/python -c "import os; os.chdir('build/venv'); import psutil"
	$(PYTHON) -m twine check --strict dist/*.tar.gz

check-wheels:  ## Check sanity of wheels.
	$(PYTHON) -m abi3audit --verbose --strict dist/*-abi3-*.whl
	$(PYTHON) -m twine check --strict dist/*.whl

pre-release:  ## Check if we're ready to produce a new release.
	${MAKE} clean
	${MAKE} sdist
	${MAKE} check-sdist
	${MAKE} install
	$(PYTHON) -c \
		"import requests, sys; \
		from packaging.version import parse; \
		from psutil import __version__; \
		res = requests.get('https://pypi.org/pypi/psutil/json', timeout=5); \
		versions = sorted(res.json()['releases'], key=parse, reverse=True); \
		sys.exit('version %r already exists on PYPI' % __version__) if __version__ in versions else 0"
	$(PYTHON) -c \
		"from psutil import __version__ as ver; \
		doc = open('docs/index.rst').read(); \
		history = open('HISTORY.rst').read(); \
		assert ver in doc, '%r not in docs/index.rst' % ver; \
		assert ver in history, '%r not in HISTORY.rst' % ver; \
		assert 'XXXX' not in history, 'XXXX in HISTORY.rst';"
	${MAKE} download-wheels-github
	${MAKE} download-wheels-appveyor
	${MAKE} check-wheels
	${MAKE} print-hashes
	${MAKE} print-dist

release:  ## Upload a new release.
	${MAKE} check-sdist
	${MAKE} check-wheels
	$(PYTHON) -m twine upload dist/*.tar.gz
	$(PYTHON) -m twine upload dist/*.whl
	${MAKE} git-tag-release

generate-manifest:  ## Generates MANIFEST.in file.
	$(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

print-dist:  ## Print downloaded wheels / tar.gs
	$(PYTHON) scripts/internal/print_dist.py

git-tag-release:  ## Git-tag a new release.
	git tag -a release-`python3 -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

# ===================================================================
# Printers
# ===================================================================

print-announce:  ## Print announce of new release.
	@$(PYTHON) scripts/internal/print_announce.py

print-timeline:  ## Print releases' timeline.
	@$(PYTHON) scripts/internal/print_timeline.py

print-access-denied: ## Print AD exceptions
	${MAKE} build
	@$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/print_access_denied.py

print-api-speed:  ## Benchmark all API calls
	${MAKE} build
	@$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/print_api_speed.py $(ARGS)

print-downloads:  ## Print PYPI download statistics
	$(PYTHON) scripts/internal/print_downloads.py

print-hashes:  ## Prints hashes of files in dist/ directory
	$(PYTHON) scripts/internal/print_hashes.py dist/

print-sysinfo:  ## Prints system info
	$(PYTHON) -c "from psutil.tests import print_sysinfo; print_sysinfo()"

# ===================================================================
# Misc
# ===================================================================

grep-todos:  ## Look for TODOs in the source files.
	git grep -EIn "TODO|FIXME|XXX"

bench-oneshot:  ## Benchmarks for oneshot() ctx manager (see #799).
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/bench_oneshot.py

bench-oneshot-2:  ## Same as above but using perf module (supposed to be more precise)
	${MAKE} build
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/bench_oneshot_2.py

check-broken-links:  ## Look for broken links in source files.
	git ls-files | xargs $(PYTHON) -Wa scripts/internal/check_broken_links.py

check-manifest:  ## Inspect MANIFEST.in file.
	$(PYTHON) -m check_manifest -v $(ARGS)

help: ## Display callable targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
