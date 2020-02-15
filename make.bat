@echo off

rem ==========================================================================
rem Shortcuts for various tasks, emulating UNIX "make" on Windows.
rem It is primarly intended as a shortcut for compiling / installing
rem psutil ("make.bat build", "make.bat install") and running tests
rem ("make.bat test").
rem
rem This script is modeled after my Windows installation which uses:
rem - Visual studio 2008 for Python 2.6, 2.7
rem - Visual studio 2010 for Python 3.4+
rem ...therefore it might not work on your Windows installation.
rem
rem By default C:\Python27\python.exe is used.
rem To compile for a specific Python version run:
rem     set PYTHON=C:\Python34\python.exe & make.bat build
rem
rem To use a different test script:
rem      set PYTHON=C:\Python34\python.exe & set TSCRIPT=foo.py & make.bat test
rem ==========================================================================

if "%PYTHON%" == "" (
    if exist "C:\Python38-64\python.exe" (
        set PYTHON=C:\Python38-64\python.exe
    ) else (
        set PYTHON=C:\Python27\python.exe
    )
)

if "%TSCRIPT%" == "" (
    set TSCRIPT=psutil\tests\runner.py
)

rem Needed to locate the .pypirc file and upload exes on PyPI.
set HOME=%USERPROFILE%

%PYTHON% scripts\internal\winmake.py %1 %2 %3 %4 %5 %6
