@echo off

rem ==========================================================================
rem Shortcuts for various tasks, emulating UNIX "make" on Windows.
rem It is primarily intended as a shortcut for compiling / installing
rem psutil and running tests. E.g.:
rem
rem   make build
rem   make install
rem   make test
rem
rem To compile for a specific Python version run:
rem     set PYTHON=C:\Python34\python.exe & make.bat build
rem
rem To run a specific test:
rem     set ARGS=psutil/tests/test_system.py::TestMemoryAPIs::test_virtual_memory && make.bat test
rem ==========================================================================

if "%PYTHON%" == "" (
    set PYTHON=python
)

set PYTHONWARNINGS=always
set PSUTIL_DEBUG=1
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

%PYTHON% scripts\internal\winmake.py %1 %2 %3 %4 %5 %6 %7 %8 %9
