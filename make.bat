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
rem This script is modeled after my Windows installation which uses:
rem - Visual studio 2008 for Python 2.7
rem - Visual studio 2010 for Python 3.4+
rem ...therefore it might not work on your Windows installation.
rem
rem To compile for a specific Python version run:
rem     set PYTHON=C:\Python34\python.exe & make.bat build
rem ==========================================================================

if "%PYTHON%" == "" (
    set PYTHON=python
)

rem Needed to locate the .pypirc file and upload exes on PyPI.
set HOME=%USERPROFILE%
set PSUTIL_DEBUG=1

%PYTHON% scripts\internal\winmake.py %1 %2 %3 %4 %5 %6
