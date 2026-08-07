# Shortcuts for various development tasks.
#
# - To use this on Windows install Git For Windows first, then launch a Git
#   Bash Shell.
# - To use a specific Python version run: `make install PYTHON=python3.13`.
# - To append an argument to a command use ARGS, e.g: `make test ARGS="-k
#   some_test`.

# Configurable
PYTHON = python3
ARGS =
FILES =

PYTHON_ENV_VARS = PYTHONWARNINGS=always PYTHONUNBUFFERED=1 PSUTIL_DEBUG=1 PSUTIL_TESTING=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
SUDO = $(if $(filter $(OS),Windows_NT),,sudo -E)
DPRINT = ~/.dprint/bin/dprint
INSTALL_PYDEPS = PYTHON=$(PYTHON) ./scripts/internal/install-pydeps.sh

# `make` called with no args is like `make help`
.DEFAULT_GOAL := help

# install git hook (skipped in worktrees, where .git is a file)
_ := $(shell test -d .git && mkdir -p .git/hooks/ && ln -sf ../../scripts/internal/git_pre_commit.py .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit)

# phony all targets that have a ## docstring
_PHONY := $(shell awk -F':.*?## ' \
	'/^[a-zA-Z0-9_.-]+:.*?## / {print $$1}' $(MAKEFILE_LIST))
.PHONY: $(_PHONY)

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
		-o -name \*@psutil-\*`
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

build:  ## Compile (in parallel) without installing.
	@# "build_ext -i" copies compiled *.so files in ./psutil directory in order
	@# to allow "import psutil" when using the interactive interpreter from
	@# within  this directory.
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py build_ext --inplace
	$(PYTHON_ENV_VARS) $(PYTHON) -c "import psutil"  # make sure it actually worked

install:  ## Install this package as current user in edit / development mode.
	# --no-build-isolation: reuse setuptools installed above instead of
	# downloading another copy into a temporary build env.
	$(PYTHON_ENV_VARS) $(INSTALL_PYDEPS) --no-build-isolation --editable .
	$(PYTHON_ENV_VARS) $(PYTHON) -c "import psutil"  # make sure it actually worked

uninstall:  ## Uninstall this package via pip.
	cd ..; $(PYTHON_ENV_VARS) $(PYTHON) -m pip uninstall -y -v psutil || true
	$(PYTHON_ENV_VARS) $(PYTHON) scripts/internal/purge_installation.py

install-sysdeps:  ## Install system deps needed to compile psutil.
	./scripts/internal/install-sysdeps.sh

install-sysdeps-test:  ## Install CLI tools needed to run unit tests.
	./scripts/internal/install-sysdeps.sh --test-only

# ---

install-pydeps-build:  ## Install python deps necessary to compile psutil.
	$(INSTALL_PYDEPS) --group build

install-pydeps-test:  ## Install python deps necessary to run unit tests.
	$(INSTALL_PYDEPS) --group test

install-pydeps-lint:  ## Install python deps necessary to run linters.
	$(INSTALL_PYDEPS) --group lint

install-pydeps-docs:  ## Install python deps necessary to build the doc.
	$(INSTALL_PYDEPS) --group docs

install-pydeps-dev:  ## Install python deps meant for local development.
	$(INSTALL_PYDEPS) --group dev

# ===================================================================
# Tests
# ===================================================================

# - cache dir on Windows often causes "Permission denied" errors
# - on CI drop instafail so failures gather in one block at the end
_PYTEST_EXTRA != { if [ "$$OS" = "Windows_NT" ]; then printf '%s ' '-o cache_dir=/tmp/pytest-psutil-cache'; fi; if [ -n "$$CI" ]; then printf '%s ' '-p no:instafail'; fi; }

RUN_TEST = $(PYTHON_ENV_VARS) $(PYTHON) -m pytest --durations=5 $(_PYTEST_EXTRA)
RUN_TEST_MEMLEAKS = PYTHONMALLOC=malloc $(RUN_TEST) -k test_memleaks.py

# --- main

test:  ## Run all tests (except memleak tests).
	# To run a specific test do `make test ARGS=tests/test_process.py::TestProcess::test_cmdline`
	$(RUN_TEST) $(ARGS)

test-parallel:  ## Run all tests (except memleak tests) in parallel.
	$(RUN_TEST) -n auto --dist loadgroup -m 'not isolated' $(ARGS)
	$(RUN_TEST) -m isolated $(ARGS)

test-memleaks:  ## Run memory leak tests.
	$(RUN_TEST_MEMLEAKS) $(ARGS)

test-memleaks-parallel:  ## Run memory leak tests in parallel.
	$(RUN_TEST_MEMLEAKS) -n auto $(ARGS)

# --- individual

test-process:  ## Run process-related tests.
	$(RUN_TEST) -k "test_process.py or test_proc or test_pid or Process or pids or pid_exists" $(ARGS)

test-process-all:  ## Run tests which iterate over all process PIDs.
	$(RUN_TEST) -k test_process_all.py $(ARGS)

test-system:  ## Run system-related API tests.
	$(RUN_TEST) -k "test_system.py or test_sys or System or disk or sensors or net_io_counters or net_if_addrs or net_if_stats or users or pids or win_service_ or boot_time" $(ARGS)

test-misc:  ## Run miscellaneous tests.
	$(RUN_TEST) -k "test_misc.py or Misc" $(ARGS)

test-scripts:  ## Run scripts tests.
	$(RUN_TEST) -k test_scripts.py $(ARGS)

test-testutils:  ## Run test utils tests.
	$(RUN_TEST) -k test_testutils.py $(ARGS)

test-unicode:  ## Test APIs dealing with strings.
	$(RUN_TEST) -k test_unicode.py $(ARGS)

test-contracts:  ## APIs sanity tests.
	$(RUN_TEST) -k test_contracts.py $(ARGS)

test-docs:  ## Run doc sanity tests (outside testpaths, run on demand).
	$(MAKE) -C docs test ARGS="$(ARGS)"

test-bots:  ## Run GitHub bot tests (outside testpaths, run on demand).
	$(PYTHON) -m pytest -o addopts="" .github/workflows/tests/ $(ARGS)

test-type-hints:  ## Test type hints
	$(RUN_TEST) -k test_type_hints.py $(ARGS)

test-connections:  ## Test psutil.net_connections() and Process.net_connections().
	$(RUN_TEST) -k "test_connections.py or net_" $(ARGS)

test-heap:  ## Test psutil.heap_*() APIs.
	$(RUN_TEST) -k "test_heap.py or heap_" $(ARGS)

test-posix:  ## POSIX specific tests.
	$(RUN_TEST) -k "test_posix.py or posix_ or Posix" $(ARGS)

test-platform:  ## Run specific platform tests only.
	$(RUN_TEST) -k test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS", "AIX") if getattr(psutil, x)][0])'`.py $(ARGS)

# --- special

test-sudo:  ## Run tests requiring root privileges.
	# Use unittest runner because pytest may not be installed as root.
	$(SUDO) $(PYTHON_ENV_VARS) $(PYTHON) -m unittest -v tests.test_sudo

test-last-failed:  ## Re-run tests which failed on last run
	$(RUN_TEST) --last-failed $(ARGS)

coverage:  ## Run test coverage.
	rm -rf .coverage htmlcov
	$(PYTHON_ENV_VARS) $(PYTHON) -m coverage run -m pytest $(ARGS)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

# ===================================================================
# Linters
# ===================================================================

# Return a shell pipeline that outputs one file per line. Uses
# $(FILES) if set, else "git ls-files" with given pattern(s).
_ls = $(if $(FILES), printf '%s\n' $(FILES), git ls-files $(1))

ruff:  ## Run ruff linter.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --output-format=concise

black:  ## Run black formatter.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black --check --safe

lint-c:  ## Run C linter.
	@$(call _ls,'*.c' '*.h') | xargs -P0 -I{} clang-format --dry-run --Werror {}

dprint:  ## Run linter for .md / .json / .yml / .js / .css files.
	@$(DPRINT) check

lint-rst:  ## Run linter for .rst files.
	@$(call _ls,'*.rst') | xargs $(PYTHON) scripts/internal/rst_unused_targets.py
	@$(call _ls,'*.rst') | xargs sphinx-lint --enable all --disable line-too-long
	@$(call _ls,'*.rst') | xargs rstwrap --check

lint-toml:  ## Run linter for pyproject.toml.
	@$(call _ls,'*.toml') | xargs toml-sort --check

lint-all:  ## Run all linters in parallel
	$(MAKE) -j \
		black \
		ruff \
		lint-c \
		dprint \
		lint-rst \
		lint-toml

# --- not mandatory linters (just run from time to time)

pylint:  ## Python pylint
	@$(call _ls,'*.py') | xargs $(PYTHON) -m pylint --rcfile=pyproject.toml --jobs=0 $(ARGS)

vulture:  ## Find unused code
	@$(call _ls,'*.py') | xargs $(PYTHON) -m vulture $(ARGS)

# ===================================================================
# Fixers
# ===================================================================

fix-black:  ## Reformat python code with black.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m black

fix-ruff:  ## Fix ruff errors.
	@$(call _ls,'*.py') | xargs $(PYTHON) -m ruff check --fix --output-format=concise $(ARGS)

fix-c:  ## Reformat C code with clang-format.
	@$(call _ls,'*.c' '*.h') | xargs -P0 -I{} clang-format -i {}  # parallel exec

fix-toml:  ## Fix pyproject.toml
	@$(call _ls,'*.toml') | xargs toml-sort

fix-rst:  ## Re-wrap .rst files.
	@$(call _ls,'*.rst') | xargs rstwrap

fix-dprint:  ## Reformat .md / .json / .yml / .js / .css files.
	@$(DPRINT) fmt

fix-all:  ## Run all code fixers.
	$(MAKE) fix-ruff
	$(MAKE) fix-black
	$(MAKE) fix-c
	$(MAKE) fix-rst
	$(MAKE) fix-toml
	$(MAKE) fix-dprint

# ===================================================================
# CI jobs
# ===================================================================

ci-lint:  ## Run all linters on GitHub CI.
	$(MAKE) install-pydeps-lint
	test -x $(DPRINT) || curl -fsSL https://dprint.dev/install.sh | sh
	$(DPRINT) --version
	clang-format --version
	$(MAKE) lint-all

ci-test:  ## Run tests on GitHub CI. Used by BSD runners.
	$(MAKE) install-sysdeps
	# Install psutil before the test deps: psleak depends on psutil,
	# and a pre-installed one stops pip from pulling it from PyPI.
	$(INSTALL_PYDEPS) .
	$(MAKE) install-pydeps-test
	$(MAKE) build
	$(MAKE) print-sysinfo
	$(MAKE) test-parallel
	$(MAKE) test-memleaks-parallel

ci-test-cibuildwheel:  ## Run CI tests for the built wheels.
	$(MAKE) install-sysdeps-test  # the wheel is already built
	$(MAKE) print-sysinfo
	# Warm pywin32's gen_py cache: concurrent first imports of wmi in
	# the pytest workers corrupt it (EOFError from gencache).
	if [ "$$OS" = "Windows_NT" ]; then $(PYTHON) -c "import wmi"; fi
	# Tests must be run from a separate directory so pytest does not import
	# from the source tree and instead exercises only the installed wheel.
	rm -rf .tests tests/__pycache__
	mkdir -p .tests
	cp -r tests .tests/
	cd .tests/ && PYTHONPATH=$$(pwd) $(MAKE) -f ../Makefile test-parallel
	cd .tests/ && PYTHONPATH=$$(pwd) $(MAKE) -f ../Makefile test-memleaks-parallel

ci-check-dist:  ## Run all sanity checks re. to the package distribution.
	$(INSTALL_PYDEPS) setuptools virtualenv twine check-manifest validate-pyproject[all] abi3audit
	$(MAKE) create-sdist
	mv wheelhouse/* dist/
	$(MAKE) check-dist
	$(PYTHON) scripts/internal/print_dist.py --check

# ===================================================================
# Distribution
# ===================================================================

# --- create

generate-manifest:  ## Generates MANIFEST.in file.
	$(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

create-sdist:  ## Create tar.gz source distribution.
	$(MAKE) generate-manifest
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py sdist

create-wheels:  ## Create .whl files
	$(PYTHON_ENV_VARS) $(PYTHON) setup.py bdist_wheel

download-wheels:  ## Download latest wheels hosted on github.
	$(PYTHON) scripts/internal/download_wheels.py --tokenfile=~/.github.api.key
	$(MAKE) print-dist

create-dist:  ## Create .tar.gz + .whl distribution.
	$(MAKE) create-sdist
	$(MAKE) download-wheels

# --- check

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
	$(MAKE) -j \
		check-manifest \
		check-pyproject \
		check-sdist \
		check-wheels

# --- release

pre-release:  ## Check if we're ready to produce a new release.
	$(MAKE) clean
	$(MAKE) create-dist
	$(MAKE) check-dist
	$(MAKE) install
	@$(PYTHON) -c \
		"import requests, sys; \
		from packaging.version import parse; \
		from psutil import __version__; \
		res = requests.get('https://pypi.org/pypi/psutil/json', timeout=5); \
		versions = sorted(res.json()['releases'], key=parse, reverse=True); \
		sys.exit('version %r already exists on PYPI' % __version__) if __version__ in versions else 0"
	@ver=$$($(PYTHON) -c "from psutil import __version__; print(__version__)"); \
		grep -q "$$ver" docs/changelog.rst || { echo "ERR: version $$ver not found in docs/changelog.rst"; exit 1; }; \
		grep -q "$$ver" docs/timeline.rst || { echo "ERR: version $$ver not found in docs/timeline.rst"; exit 1; }
	$(MAKE) print-hashes
	$(MAKE) print-dist

release:  ## Upload a new release.
	$(PYTHON) -m twine upload dist/*.tar.gz
	$(PYTHON) -m twine upload dist/*.whl
	$(MAKE) git-tag-release

git-tag-release:  ## Git-tag a new release.
	git tag -a v`$(PYTHON) -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

# ===================================================================
# Printers
# ===================================================================

print-announce:  ## Print announce of new release.
	@$(PYTHON) scripts/internal/print_announce.py

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

bench-oneshot-2:  ## Same as above but using perf module (more precise).
	$(PYTHON) scripts/internal/bench_oneshot_2.py

find-broken-links:  ## Look for broken links in source files.
	git ls-files | xargs $(PYTHON) -Wa scripts/internal/find_broken_links.py

_CI_JOBS = $(patsubst .github/workflows/%.yml,%,$(shell grep -l workflow_dispatch .github/workflows/*.yml))

ci-run:  ## Manually run a CI workflow, e.g. `make ci-run JOB=bsd`
	@echo "$(_CI_JOBS)" | tr ' ' '\n' | grep -qx "$(JOB)" || { echo "Usage: make ci-run JOB=<$$(echo $(_CI_JOBS) | tr ' ' '|')>"; exit 1; }
	gh workflow run $(JOB).yml --ref $$(git rev-parse --abbrev-ref HEAD)

help: ## Display callable targets.
	@awk -F':.*?## ' '/^[a-zA-Z0-9_.-]+:.*?## / {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
