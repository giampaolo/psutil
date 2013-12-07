# Shortcuts for various tasks.

PYTHON=python
TEST_SCRIPT=test/test_psutil.py
FLAGS=

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
	$(PYTHON) $(TEST_SCRIPT)

nosetests: install
	# make nosetests FLAGS=test_name
	nosetests test/test_psutil.py -v -m $(FLAGS)

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
