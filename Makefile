PYTHON=python

all: test

install: clean
	$(PYTHON) setup.py install --user

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
