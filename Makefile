# Shortcuts for various tasks (UNIX only).
# To use a specific Python version run:
# $ make install PYTHON=python3.3

# You can set these variables from the command line.
PYTHON    = python
TSCRIPT   = test/test_psutil.py

all: test

clean:
	rm -f `find . -type f -name \*.py[co]`
	rm -f `find . -type f -name \*.so`
	rm -f `find . -type f -name .\*~`
	rm -f `find . -type f -name \*.orig`
	rm -f `find . -type f -name \*.bak`
	rm -f `find . -type f -name \*.rej`
	rm -rf `find . -type d -name __pycache__`
	rm -rf *.egg-info
	rm -rf *\$testfile*
	rm -rf build
	rm -rf dist
	rm -rf docs/_build

build: clean
	$(PYTHON) setup.py build

install: build
	if test $(PYTHON) = python2.4; then \
		$(PYTHON) setup.py install; \
	elif test $(PYTHON) = python2.5; then \
		$(PYTHON) setup.py install; \
	else \
		$(PYTHON) setup.py install --user; \
	fi

uninstall:
	if test $(PYTHON) = python2.4; then \
		pip-2.4 uninstall -y -v psutil; \
	else \
		cd ..; $(PYTHON) -m pip uninstall -y -v psutil; \
	fi

test: install
	$(PYTHON) $(TSCRIPT)

test-process: install
	$(PYTHON) -m unittest -v test.test_psutil.TestProcess

test-system: install
	$(PYTHON) -m unittest -v test.test_psutil.TestSystemAPIs

# Run a specific test by name; e.g. "make test-by-name disk_" will run
# all test methods containing "disk_" in their name.
# Requires "pip install nose".
test-by-name:
	@$(PYTHON) -m nose test/test_psutil.py --nocapture -v -m $(filter-out $@,$(MAKECMDGOALS))

memtest: install
	$(PYTHON) test/test_memory_leaks.py

pep8:
	@hg locate '*py' | xargs pep8

pyflakes:
	@export PYFLAKES_NODOCTEST=1 && \
		hg locate '*py' | xargs pyflakes

# Upload source tarball on https://pypi.python.org/pypi/psutil.
upload-src: clean
	$(PYTHON) setup.py sdist upload

# Build and upload doc on https://pythonhosted.org/psutil/.
# Requires "pip install sphinx-pypi-upload".
upload-doc:
	cd docs; make html
	$(PYTHON) setup.py upload_sphinx --upload-dir=docs/_build/html
