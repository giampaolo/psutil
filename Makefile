# Shortcuts for various tasks.

PYTHON=python

all: test

install: clean
	if test $(PYTHON) = python2.4; then \
		$(PYTHON) setup.py install; \
	elif test $(PYTHON) = python2.5; then \
		$(PYTHON) setup.py install; \
	else \
		$(PYTHON) setup.py install --user; \
	fi

test: install
	$(PYTHON) test/test_psutil.py

memtest: install
	$(PYTHON) test/test_memory_leaks.py

pep8:
	pep8 psutil/ test/ examples/ setup.py --ignore E501

pyflakes:
	pyflakes psutil/ test/ examples/ setup.py

clean:
	rm -v -rf `find . -name __pycache__`
	rm -v -rf `find . -name '*.egg-info' `
	rm -v -f `find . -type f -name '*.py[co]' `
	rm -v -f `find . -type f -name '*.so' `
	rm -v -f `find . -type f -name '.*~' `
	rm -v -f `find . -type f -name '*.orig' `
	rm -v -f `find . -type f -name '*.bak' `
	rm -v -f `find . -type f -name '*.rej' `
	rm -rf build
	rm -rf dist
