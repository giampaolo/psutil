@ECHO OFF

REM ===========================================================================
REM Shortcuts for various tasks, emulating UNIX "make".
REM Use this to script for various tasks such as runing tests, install
REM psutil, etc.
REM To run tests run "make.bat test".
REM This script is modeled after my Windows installation so it might
REM need some adjustements in order to work on your system.
REM The following assumptions are made:
REM - Python is installed in C:\PythonXY\python.exe
REM - the right Visual Studio version is installed
REM - in case of Python 2.4 and 2.5 use mingw32 compiler
REM ===========================================================================


SET PYTHON=C:\Python27\python.exe
SET PATH=%PYTHON%;%PATH%
SET PATH=C:\MinGW\bin;%PATH%


if "%1" == "" goto help

if "%1" == "help" (
    :help
    echo Please use `make ^<target^>` where ^<target^> is one of:
    echo clean build install uninstall test
    goto :EOF
)

if "%1" == "clean" (
    call :clean
    goto :EOF
)

if "%1" == "build" (
    call :build
    goto :EOF
)

if "%1" == "install" (
    call :install
    goto :EOF
)

if "%1" == "uninstall" (
    rmdir /S /Q %PYTHON%\Lib\site-packages\psutil
    del /F /S /Q %PYTHON%\Lib\site-packages\psutil*
    del /F /S /Q %PYTHON%\Lib\site-packages\_psutil*
    goto :EOF
)

if "%1" == "test" (
    call :install
    %PYTHON% test/test_psutil.py
    goto :EOF
)

if "%1" == "create-exes" (
    call :clean
    C:\Python26\python.exe setup.py build bdist_wininst
    C:\Python27\python.exe setup.py build bdist_wininst
    C:\Python33\python.exe setup.py build bdist_wininst
    goto :EOF
)


goto :help

:install
    call :build
    %PYTHON% setup.py install
    goto :EOF

:build
    if %PYTHON%==C:\Python24\python.exe (
        %PYTHON% setup.py build -c mingw32
    ) else if %PYTHON%==C:\Python25\python.exe (
        %PYTHON% setup.py build -c mingw32
    ) else (
        %PYTHON% setup.py build
    )
    goto :EOF

:clean
    for /F "tokens=*" %%G IN ('dir /B /AD /S __pycache__') DO rmdir /S /Q %%G
    for /r %%R in (*.pyc) do if exist %%R (del /s %%R)
    if exist build (rmdir /S /Q build)
    if exist dist (rmdir /S /Q dist)
    goto :EOF
