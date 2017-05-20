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

# Remove all build files.
clean:
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


# Compile without installing.
build: _
	# make sure setuptools is installed (needed for 'develop' / edit mode)
	$(PYTHON) -c "import setuptools"
	PYTHONWARNINGS=all $(PYTHON) setup.py build
	@# copies compiled *.so files in ./psutil directory in order to allow
	@# "import psutil" when using the interactive interpreter from within
	@# this directory.
	PYTHONWARNINGS=all $(PYTHON) setup.py build_ext -i
	rm -rf tmp
	$(PYTHON) -c "import psutil"  # make sure it actually worked

# Install this package + GIT hooks. Install is done:
# - as the current user, in order to avoid permission issues
# - in development / edit mode, so that source can be modified on the fly
install:
	${MAKE} build
	PYTHONWARNINGS=all $(PYTHON) setup.py develop $(INSTALL_OPTS)
	rm -rf tmp

# Uninstall this package via pip.
uninstall:
	cd ..; $(PYTHON) -m pip uninstall -y -v psutil

# Install PIP (only if necessary).
install-pip:
	PYTHONWARNINGS=all $(PYTHON) -c \
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

# Install GIT hooks, pip, test deps (also upgrades them).
setup-dev-env:
	${MAKE} install-git-hooks
	${MAKE} install-pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade pip
	$(PYTHON) -m pip install $(INSTALL_OPTS) --upgrade $(DEPS)

# ===================================================================
# Tests
# ===================================================================

# Run all tests.
test:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) $(TSCRIPT)

# Run process-related API tests.
test-process:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v psutil.tests.test_process

# Run system-related API tests.
test-system:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v psutil.tests.test_system

# Run miscellaneous tests.
test-misc:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_misc.py

# Test APIs dealing with strings.
test-unicode:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_unicode.py

# APIs sanity tests.
test-contracts:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_contracts.py

# Test net_connections() and Process.connections().
test-connections:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_connections.py

# POSIX specific tests.
test-posix:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_posix.py

# Run specific platform tests only.
test-platform:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS") if getattr(psutil, x)][0])'`.py

# Memory leak tests.
test-memleaks:
	${MAKE} install
	PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) psutil/tests/test_memory_leaks.py

# Run a specific test by name, e.g.
# make test-by-name psutil.tests.test_system.TestSystemAPIs.test_cpu_times
test-by-name:
	${MAKE} install
	@PSUTIL_TESTING=1 PYTHONWARNINGS=all $(PYTHON) -m unittest -v $(ARGS)

# Run test coverage.
coverage:
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

pep8:
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m pep8

pyflakes:
	@export PYFLAKES_NODOCTEST=1 && \
		git ls-files | grep \\.py$ | xargs $(PYTHON) -m pyflakes

flake8:
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m flake8

# ===================================================================
# GIT
# ===================================================================

# git-tag a new release
git-tag-release:
	git tag -a release-`python -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

# Install GIT pre-commit hook.
install-git-hooks:
	ln -sf ../../.git-pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# ===================================================================
# Distribution
# ===================================================================

# Generate tar.gz source distribution.
sdist:
	${MAKE} clean
	${MAKE} generate-manifest
	PYTHONWARNINGS=all $(PYTHON) setup.py sdist

# Upload source tarball on https://pypi.python.org/pypi/psutil.
upload-src:
	${MAKE} sdist
	PYTHONWARNINGS=all $(PYTHON) setup.py sdist upload

# Download exes/wheels hosted on appveyor.
win-download-exes:
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/download_exes.py --user giampaolo --project psutil

# Upload exes/wheels in dist/* directory to PYPI.
win-upload-exes:
	PYTHONWARNINGS=all $(PYTHON) -m twine upload dist/*.exe
	PYTHONWARNINGS=all $(PYTHON) -m twine upload dist/*.whl

# All the necessary steps before making a release.
pre-release:
	@PYTHONWARNINGS=all $(PYTHON) -c "import subprocess, sys; out = subprocess.check_output('git diff-index HEAD --', shell=True).strip(); sys.exit('there are uncommitted changes') if out else sys.exit(0);"
	${MAKE} sdist
	${MAKE} install
	@PYTHONWARNINGS=all $(PYTHON) -c \
		"from psutil import __version__ as ver; \
		doc = open('docs/index.rst').read(); \
		history = open('HISTORY.rst').read(); \
		assert ver in doc, '%r not in docs/index.rst' % ver; \
		assert ver in history, '%r not in HISTORY.rst' % ver; \
		assert 'XXXX' not in history, 'XXXX in HISTORY.rst';"
	${MAKE} win-download-exes

# Create a release: creates tar.gz and exes/wheels, uploads them,
# upload doc, git tag release.
release:
	${MAKE} pre-release
	PYTHONWARNINGS=all $(PYTHON) -m twine upload dist/*  # upload tar.gz, exes, wheels on PYPI
	${MAKE} git-tag-release

# Print announce of new release.
print-announce:
	@PYTHONWARNINGS=all $(PYTHON) scripts/internal/print_announce.py

# Print releases' timeline.
print-timeline:
	@PYTHONWARNINGS=all $(PYTHON) scripts/internal/print_timeline.py

# Inspect MANIFEST.in file.
check-manifest:
	PYTHONWARNINGS=all $(PYTHON) -m check_manifest -v $(ARGS)

# Generates MANIFEST.in file.
generate-manifest:
	@PYTHONWARNINGS=all $(PYTHON) scripts/internal/generate_manifest.py > MANIFEST.in

# ===================================================================
# Misc
# ===================================================================

grep-todos:
	git grep -EIn "TODO|FIXME|XXX"

# run script which benchmarks oneshot() ctx manager (see #799)
bench-oneshot:
	${MAKE} install
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/bench_oneshot.py

# same as above but using perf module (supposed to be more precise)
bench-oneshot-2:
	${MAKE} install
	PYTHONWARNINGS=all $(PYTHON) scripts/internal/bench_oneshot_2.py

# generate a doc.zip file and manually upload it to PYPI.
doc:
	cd docs && make html && cd _build/html/ && zip doc.zip -r .
	mv docs/_build/html/doc.zip .
	@echo "done; now manually upload doc.zip from here: https://pypi.python.org/pypi?:action=pkg_edit&name=psutil"

# check whether the links mentioned in some files are valid.
check-broken-links:
		git ls-files | xargs $(PYTHON) -Wa scripts/internal/check_broken_links.py
