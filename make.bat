@echo off

:: ==========================================================================
:: Shortcuts for various tasks, emulating UNIX "make" on Windows.
:: It is primary intended as a shortcut for compiling / installing
:: psutil ("make.bat build", "make.bat install") and running tests
:: ("make.bat test").
::
:: This script is modeled after my Windows installation which uses:
:: - Visual studio 2008 for Python 2.6, 2.7
:: - Visual studio 20?? for Python 3.8+
:: ...therefore it might not work on your Windows installation.
::
:: By default C:\Python27\python.exe is used.
:: To compile for a specific Python version run:
::     set PYTHON=C:\Python34\python.exe & make.bat build
::
:: To use a different test script:
::      set PYTHON=C:\Python38-64\python.exe & set TSCRIPT=foo.py & make.bat test
:: ==========================================================================


if "%PYTHON%" == "" (
    if exist "C:\Python38-64\python.exe" (
        set PYTHON=C:\Python38-64\python.exe
    ) else (
        set PYTHON=C:\Python27\python.exe
    )
)

if NOT exist "%PYTHON%" (
    echo Python Interpreter "%PYTHON%" not found, You need to set the PYTHON environment variable accordingly
    pause
	exit /b 1
    )


if "%TSCRIPT%" == "" (
    set TSCRIPT=psutil\tests\runner.py
)

"%PYTHON%" scripts\internal\winmake.py %1 %2 %3 %4 %5 %6
