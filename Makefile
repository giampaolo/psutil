# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run:
# $ make install PYTHON=python3.3

# You can set these variables from the command line.
PYTHON    = python
TSCRIPT   = psutil/tests/runner.py

all: test

clean:
	rm -f `find . -type f -name \*.py[co]`
	rm -f `find . -type f -name \*.so`
	rm -f `find . -type f -name \*.~`
	rm -f `find . -type f -name \*.orig`
	rm -f `find . -type f -name \*.bak`
	rm -f `find . -type f -name \*.rej`
	rm -rf `find . -type d -name __pycache__`
	rm -rf *.core
	rm -rf *.egg-info
	rm -rf *\$testfile*
	rm -rf .coverage
	rm -rf .tox
	rm -rf build
	rm -rf dist
	rm -rf docs/_build
	rm -rf htmlcov

build: clean
	$(PYTHON) setup.py build
	@# copies *.so files in ./psutil directory in order to allow
	@# "import psutil" when using the interactive interpreter from within
	@# this directory.
	$(PYTHON) setup.py build_ext -i

# useful deps which are nice to have while developing / testing
setup-dev-env: install-git-hooks
	python -c  "import urllib2, ssl; \
				context = ssl._create_unverified_context() if hasattr(ssl, '_create_unverified_context') else None; \
				kw = dict(context=context) if context else {}; \
				r = urllib2.urlopen('https://bootstrap.pypa.io/get-pip.py', **kw); \
				open('/tmp/get-pip.py', 'w').write(r.read());"
	$(PYTHON) /tmp/get-pip.py --user
	rm /tmp/get-pip.py
	$(PYTHON) -m pip install --user --upgrade pip
	$(PYTHON) -m pip install --user --upgrade \
		coverage  \
		flake8 \
		ipaddress \
		ipdb \
		mock==1.0.1 \
		nose \
		pep8 \
		pyflakes \
		requests \
		sphinx \
		sphinx-pypi-upload \
		unittest2 \

install: build
	$(PYTHON) setup.py develop --user

uninstall:
	cd ..; $(PYTHON) -m pip uninstall -y -v psutil

test: install
	$(PYTHON) $(TSCRIPT)

test-process: install
	$(PYTHON) -m unittest -v psutil.tests.test_process

test-system: install
	$(PYTHON) -m unittest -v psutil.tests.test_system

test-memleaks: install
	$(PYTHON) psutil/tests/test_memory_leaks.py

# Run a specific test by name; e.g. "make test-by-name disk_" will run
# all test methods containing "disk_" in their name.
# Requires "pip install nose".
test-by-name: install
	@$(PYTHON) -m nose psutil/tests/*.py --nocapture -v -m $(filter-out $@,$(MAKECMDGOALS))

# Run specific platform tests only.
test-platform: install
	$(PYTHON) psutil/tests/test_`$(PYTHON) -c 'import psutil; print([x.lower() for x in ("LINUX", "BSD", "OSX", "SUNOS", "WINDOWS") if getattr(psutil, x)][0])'`.py

# Same as above but for test_memory_leaks.py script.
test-memleaks-by-name: install
	@$(PYTHON) -m nose test/test_memory_leaks.py --nocapture -v -m $(filter-out $@,$(MAKECMDGOALS))

coverage: install
	# Note: coverage options are controlled by .coveragerc file
	rm -rf .coverage htmlcov
	$(PYTHON) -m coverage run $(TSCRIPT)
	$(PYTHON) -m coverage report
	@echo "writing results to htmlcov/index.html"
	$(PYTHON) -m coverage html
	$(PYTHON) -m webbrowser -t htmlcov/index.html

pep8:
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m pep8

pyflakes:
	@export PYFLAKES_NODOCTEST=1 && \
		git ls-files | grep \\.py$ | xargs $(PYTHON) -m pyflakes

flake8:
	@git ls-files | grep \\.py$ | xargs $(PYTHON) -m flake8

# Upload source tarball on https://pypi.python.org/pypi/psutil.
upload-src: clean
	$(PYTHON) setup.py sdist upload

# Build and upload doc on https://pythonhosted.org/psutil/.
# Requires "pip install sphinx-pypi-upload".
upload-doc:
	cd docs; make html
	$(PYTHON) setup.py upload_sphinx --upload-dir=docs/_build/html

# git-tag a new release
git-tag-release:
	git tag -a release-`python -c "import setup; print(setup.get_version())"` -m `git rev-list HEAD --count`:`git rev-parse --short HEAD`
	git push --follow-tags

# install GIT pre-commit hook
install-git-hooks:
	ln -sf ../../.git-pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

# download exes/wheels hosted on appveyor
win-download-exes:
	$(PYTHON) .ci/appveyor/download_exes.py --user giampaolo --project psutil

# upload exes/wheels in dist/* directory to PYPI
win-upload-exes:
	$(PYTHON) -m twine upload dist/*
