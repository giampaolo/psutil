# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run: "make install PYTHON=python3.3"
# You can set the variables below from the command line.

# Configurable
PYTHON = python3
ARGS =

PIP_INSTALL_ARGS = --trusted-host files.pythonhosted.org --trusted-host pypi.org --upgrade
PYTHON_ENV_VARS = PYTHONWARNINGS=always PYTHONUNBUFFERED=1 PSUTIL_DEBUG=1 PSUTIL_TESTING=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
SUDO = $(if $(filter $(OS),Windows_NT),,sudo -E)
DPRINT = ~/.dprint/bin/dprint

# if make is invoked with no arg, default to `make help`
.DEFAULT_GOAL := help

# install git hook
_ := $(shell mkdir -p .git/hooks/ && ln -sf ../../scripts/internal/git_pre_commit.py .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit)

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
		.tests \
		build/ \
		dist/ \
		docs/_build/ \
		htmlcov/ \
		pytest-cache-files* \
		wheelhouse

.PHONY: build
build:  ## Compile (in parallel) without installing.
	@# "build_ext -i" copies compiled *.so files in ./psutil directory in order
	@# to allow "import psutil" when using the interactive interpreter from
	@# within  this directory.
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py build_ext -i --parallel 4
	$(PYTHON_ENV_VARS) $(PYTHON) -c "import psutil"  # make sure it actually worked

install:  ## Install this package as current user in "edit" mode.
	$(MAKE) build
	# If not in a virtualenv, add --user to the install command.
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py develop $(SETUP_INSTALL_ARGS) `$(PYTHON) -c \
		"import sys; print('' if hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix else '--user')"`

uninstall:  ## Uninstall this package via pip.
	cd ..; $(PYTHON_ENV_VARS) $(PYTHON) -m pip uninstall -y -v psutil || true
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/purge_installation.py

install-pip:  ## Install pip (no-op if already installed).
	$(PYTHON) scripts/internal/install_pip.py

install-sysdeps:
	./scripts/internal/install-sysdeps.sh

install-pydeps-test:  ## Install python deps necessary to run unit tests.
	$(MAKE) install-pip
	PIP_BREAK_SYSTEM_PACKAGES=1 $(PYTHON) -m pip install $(PIP_INSTALL_ARGS) setuptools
	PIP_BREAK_SYSTEM_PACKAGES=1 $(PYTHON) -m pip install $(PIP_INSTALL_ARGS) `$(PYTHON) -c "import setup; print(' '.join(setup.TEST_DEPS))"`

install-pydeps-dev:  ## Install python deps meant for local development.
	$(MAKE) install-git-hooks
	$(MAKE) install-pip
	$(PYTHON) -m pip install $(PIP_INSTALL_ARGS) `$(PYTHON) -c "import setup; print(' '.join(setup.DEV_DEPS))"`

install-git-hooks:  ## Install GIT pre-commit hook.
	ln -sf ../../scripts/internal/git_pre_commit.py .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# ===================================================================
# Tests
# ===================================================================

RUN_TEST = $(PYTHON_ENV_VARS) $(PYTHON) -m pytest

test:  ## Run all tests (except memleak tests).
	# To run a specific test do `make test ARGS=tests/test_process.py::TestProcess::test_cmdline`
	$(RUN_TEST) --ignore=tests/test_memleaks.py $(ARGS)

test-parallel:  ## Run all tests (except memleak tests) in parallel.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -p xdist -n auto --dist loadgroup $(ARGS)

test-process:  ## Run process-related tests.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_process.py or test_proc or test_pid or Process or pids or pid_exists" $(ARGS)

test-process-all:  ## Run tests which iterate over all process PIDs.
	$(RUN_TEST) -k test_process_all.py $(ARGS)

test-system:  ## Run system-related API tests.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_system.py or test_sys or System or disk or sensors or net_io_counters or net_if_addrs or net_if_stats or users or pids or win_service_ or boot_time" $(ARGS)

test-misc:  ## Run miscellaneous tests.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_misc.py or Misc" $(ARGS)

test-scripts:  ## Run scripts tests.
	$(RUN_TEST) tests/test_scripts.py $(ARGS)

test-testutils:  ## Run test utils tests.
	$(RUN_TEST) tests/test_testutils.py $(ARGS)

test-unicode:  ## Test APIs dealing with strings.
	$(RUN_TEST) tests/test_unicode.py $(ARGS)

test-contracts:  ## APIs sanity tests.
	$(RUN_TEST) tests/test_contracts.py $(ARGS)

test-connections:  ## Test psutil.net_connections() and Process.net_connections().
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_connections.py or net_" $(ARGS)

test-heap:  ## Test psutil.heap_*() APIs.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_heap.py or heap_" $(ARGS)

test-posix:  ## POSIX specific tests.
	$(RUN_TEST) --ignore=tests/test_memleaks.py -k "test_posix.py or posix_ or Posix" $(ARGS)

test-platform:  ## Run specific platform tests only.
	$(RUN_TEST) tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS", "AIX") if getattr(psutil, x)][0])'`.py $(ARGS)

test-memleaks:  ## Memory leak tests.
	PYTHONMALLOC=malloc $(RUN_TEST) -k test_memleaks.py $(ARGS)

test-sudo:  ## Run tests requiring root privileges.
	# Use unittest runner because pytest may not be installed as root.
	$(SUDO) $(PYTHON_ENV_VARS) $(PYTHON) -m unittest -v tests.test_sudo

test-last-failed:  ## Re-run tests which failed on last run
	$(RUN_TEST) --last-failed $(ARGS)

coverage:  ## Run test coverage.
	rm -rf .coverage htmlcov
	$(PYTHON_ENV_VARS) $(PYTHON) -m coverage run -m pytest --ignore=tests/test_memleaks.py $(ARGS)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

# ===================================================================
# Linters
# ===================================================================

ruff:  ## Run ruff linter.
	@git ls-files '*.py' | xargs $(PYTHON) -m ruff check --output-format=concise

black:  ## Run black formatter.
	@git ls-files '*.py' | xargs $(PYTHON) -m black --check --safe

lint-c:  ## Run C linter.
	@git ls-files '*.c' '*.h' | xargs -P0 -I{} clang-format --dry-run --Werror {}

dprint:
	@$(DPRINT) check

lint-rst:  ## Run linter for .rst files.
	@git ls-files '*.rst' | xargs rstcheck --config=pyproject.toml

lint-toml:  ## Run linter for pyproject.toml.
	@git ls-files '*.toml' | xargs toml-sort --check

lint-all:  ## Run all linters
	$(MAKE) black
	$(MAKE) ruff
	$(MAKE) lint-c
	$(MAKE) dprint
	$(MAKE) lint-rst
	$(MAKE) lint-toml

# --- not mandatory linters (just run from time to time)

pylint:  ## Python pylint
	@git ls-files '*.py' | xargs $(PYTHON) -m pylint --rcfile=pyproject.toml --jobs=0 $(ARGS)

vulture:  ## Find unused code
	@git ls-files '*.py' | xargs $(PYTHON) -m vulture $(ARGS)

# ===================================================================
# Fixers
# ===================================================================

fix-black:
	@git ls-files '*.py' | xargs $(PYTHON) -m black

fix-ruff:
	@git ls-files '*.py' | xargs $(PYTHON) -m ruff check --fix --output-format=concise $(ARGS)

fix-c:
	@git ls-files '*.c' '*.h' | xargs -P0 -I{} clang-format -i {}  # parallel exec

fix-toml:  ## Fix pyproject.toml
	@git ls-files '*.toml' | xargs toml-sort

fix-dprint:
	@$(DPRINT) fmt

fix-all:  ## Run all code fixers.
	$(MAKE) fix-ruff
	$(MAKE) fix-black
	$(MAKE) fix-toml
	$(MAKE) fix-dprint

# ===================================================================
# CI jobs
# ===================================================================

ci-lint:  ## Run all linters on GitHub CI.
	$(PYTHON) -m pip install -U black ruff rstcheck toml-sort sphinx
	curl -fsSL https://dprint.dev/install.sh | sh
	$(DPRINT) --version
	clang-format --version
	$(MAKE) lint-all

ci-test:  ## Run tests on GitHub CI. Used by BSD runners.
	$(MAKE) install-sysdeps
	$(MAKE) install-pydeps-test
	$(MAKE) build
	$(MAKE) print-sysinfo
	$(MAKE) test
	$(MAKE) test-memleaks

ci-test-cibuildwheel:  ## Run CI tests for the built wheels.
	$(MAKE) install-sysdeps
	$(MAKE) install-pydeps-test
	$(MAKE) print-sysinfo
	# Tests must be run from a separate directory so pytest does not import
	# from the source tree and instead exercises only the installed wheel.
	rm -rf .tests tests/__pycache__
	mkdir -p .tests
	cp -r tests .tests/
	cd .tests/ && PYTHONPATH=$$(pwd) $(PYTHON_ENV_VARS) $(PYTHON) -m pytest -k "not test_memleaks.py"
	cd .tests/ && PYTHONPATH=$$(pwd) $(PYTHON_ENV_VARS) PYTHONMALLOC=malloc $(PYTHON) -m pytest -k "test_memleaks.py"

ci-check-dist:  ## Run all sanity checks re. to the package distribution.
	$(PYTHON) -m pip install -U setuptools virtualenv twine check-manifest validate-pyproject[all] abi3audit
	$(MAKE) sdist
	mv wheelhouse/* dist/
	$(MAKE) check-dist
	$(MAKE) install
	$(MAKE) print-dist

# ===================================================================
# Distribution
# ===================================================================

check-manifest:  ## Check sanity of MANIFEST.in file.
	$(PYTHON) -m check_manifest -v

check-pyproject:  ## Check sanity of pyproject.toml file.
	$(PYTHON) -m validate_pyproject -v pyproject.toml

check-sdist:  ## Check sanity of source distribution.
	$(PYTHON_ENV_VARS) $(PYTHON) -m virtualenv --clear --no-wheel --quiet build/venv
	$(PYTHON_ENV_VARS) build/venv/bin/python -m pip install -v --isolated --quiet dist/*.tar.gz
	$(PYTHON_ENV_VARS) build/venv/bin/python -c "import os; os.chdir('build/venv'); import psutil"
	$(PYTHON) -m twine check --strict dist/*.tar.gz

check-wheels:  ## Check sanity of wheels.
	$(PYTHON) -m abi3audit --verbose --strict dist/*-abi3-*.whl
	$(PYTHON) -m twine check --strict dist/*.whl

check-dist:  ## Run all sanity checks re. to the package distribution.
	$(MAKE) check-manifest
	$(MAKE) check-pyproject
	$(MAKE) check-sdist
	$(MAKE) check-wheels

generate-manifest:  ## Generates MANIFEST.in file.
	$(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

sdist:  ## Create tar.gz source distribution.
	$(MAKE) generate-manifest
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py sdist

create-wheels:  ## Create .whl files
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py bdist_wheel

pre-release:  ## Check if we're ready to produce a new release.
	$(MAKE) clean
	$(MAKE) sdist
	$(MAKE) install
	@$(PYTHON) -c \
		"import requests, sys; \
		from packaging.version import parse; \
		from psutil import __version__; \
		res = requests.get('https://pypi.org/pypi/psutil/json', timeout=5); \
		versions = sorted(res.json()['releases'], key=parse, reverse=True); \
		sys.exit('version %r already exists on PYPI' % __version__) if __version__ in versions else 0"
	@$(PYTHON) -c \
		"from psutil import __version__ as ver; \
		doc = open('docs/index.rst').read(); \
		history = open('HISTORY.rst').read(); \
		assert ver in doc, '%r not found in docs/index.rst' % ver; \
		assert ver in history, '%r not found in HISTORY.rst' % ver; \
		assert 'XXXX' not in history, 'XXXX found in HISTORY.rst';"
	$(MAKE) download-wheels
	$(MAKE) check-dist
	$(MAKE) print-hashes
	$(MAKE) print-dist

release:  ## Upload a new release.
	$(PYTHON) -m twine upload dist/*.tar.gz
	$(PYTHON) -m twine upload dist/*.whl
	$(MAKE) git-tag-release

download-wheels:  ## Download latest wheels hosted on github.
	$(PYTHON) scripts/internal/download_wheels.py --tokenfile=~/.github.token
	$(MAKE) print-dist

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
	$(PYTHON) scripts/internal/print_access_denied.py

print-api-speed:  ## Benchmark all API calls
	$(PYTHON) scripts/internal/print_api_speed.py $(ARGS)

print-downloads:  ## Print PYPI download statistics
	$(PYTHON) scripts/internal/print_downloads.py

print-hashes:  ## Prints hashes of files in dist/ directory
	$(PYTHON) scripts/internal/print_hashes.py

print-sysinfo:  ## Prints system info
	$(PYTHON) scripts/internal/print_sysinfo.py

print-dist:  ## Print downloaded wheels / tar.gz
	$(PYTHON) scripts/internal/print_dist.py

# ===================================================================
# Misc
# ===================================================================

grep-todos:  ## Look for TODOs in the source files.
	git grep -EIn "TODO|FIXME|XXX"

bench-oneshot:  ## Benchmarks for oneshot() ctx manager (see #799).
	$(PYTHON) scripts/internal/bench_oneshot.py

bench-oneshot-2:  ## Same as above but using perf module (supposed to be more precise)
	$(PYTHON) scripts/internal/bench_oneshot_2.py

find-broken-links:  ## Look for broken links in source files.
	git ls-files | xargs $(PYTHON) -Wa scripts/internal/find_broken_links.py

help: ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
