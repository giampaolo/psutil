# Shortcuts for various tasks.

.PHONY: install uninstall test nosetests memtest pep8 pyflakes clean upload-src

PYTHON ?= python
TSCRIPT ?= test/test_psutil.py
FLAGS ?=

all: test

install: clean
	if test $(PYTHON) = python2.4; then \
		$(PYTHON) setup.py install; \
	elif test $(PYTHON) = python2.5; then \
		$(PYTHON) setup.py install; \
	else \
		$(PYTHON) setup.py install --user; \
	fi

uninstall:
	pip-`$(PYTHON) -c "import sys; sys.stdout.write('.'.join(map(str, sys.version_info)[:2]))"` uninstall -y -v psutil

test: install
	$(PYTHON) $(TSCRIPT)

nosetests: install
	# make nosetests FLAGS=test_name
	nosetests test/test_psutil.py -v -m $(FLAGS)

memtest: install
	$(PYTHON) test/test_memory_leaks.py

pep8:
	pep8 psutil/ test/ examples/ setup.py --ignore E302

pyflakes:
	pyflakes psutil/ test/ examples/ setup.py

clean:
	rm -rf `find . -type d -name __pycache__`
	rm -f `find . -type f -name \*.py[co]`
	rm -f `find . -type f -name \*.so`
	rm -f `find . -type f -name .\*~`
	rm -f `find . -type f -name \*.orig`
	rm -f `find . -type f -name \*.bak`
	rm -f `find . -type f -name \*.rej`
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist

upload-src: clean
	$(PYTHON) setup.py sdist upload
