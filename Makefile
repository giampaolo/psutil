PYTHON=python3

all: test

install:
	if [ $PYTHON = "python2.4" ];then \
		echo "This can only be used on OSX/i386" ; \
		exit 1 ;\
	else \
		sudo $(PYTHON) setup.py install; \
	fi

test: install

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
