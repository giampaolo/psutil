@ECHO OFF

REM ==========================================================================
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
REM ==========================================================================


SET PYTHON=C:\Python27\python.exe
SET PATH=%PYTHON%;%PATH%
SET PATH=C:\MinGW\bin;%PATH%


if "%1" == "help" (
    :help
    echo Run `make ^<target^>` where ^<target^> is one of:
    echo   clean         clean build files
    echo   build         compile without installing
    echo   install       compile and install
    echo   uninstall     uninstall
    echo   test          run tests
    echo   create-exes   create exe installers in dist directory
    goto :eof
)

if "%1" == "clean" (
    :clean
    for /r %%R in (__pycache__) do if exist %%R (rmdir /S /Q %%R)
    for /r %%R in (*.pyc) do if exist %%R (del /s %%R)
    if exist build (rmdir /S /Q build)
    if exist dist (rmdir /S /Q dist)
    goto :eof
)

if "%1" == "build" (
    :build
    if %PYTHON%==C:\Python24\python.exe (
        %PYTHON% setup.py build -c mingw32
    ) else if %PYTHON%==C:\Python25\python.exe (
        %PYTHON% setup.py build -c mingw32
    ) else (
        %PYTHON% setup.py build
    )
    if %errorlevel% neq 0 goto :error
    goto :eof
)

if "%1" == "install" (
    :install
    call :build
    %PYTHON% setup.py install
    goto :eof
)

if "%1" == "uninstall" (
    :uninstall
    rmdir /S /Q %PYTHON%\Lib\site-packages\psutil
    del /F /S /Q %PYTHON%\Lib\site-packages\psutil*
    del /F /S /Q %PYTHON%\Lib\site-packages\_psutil*
    goto :eof
)

if "%1" == "test" (
    :test
    call :install
    %PYTHON% test/test_psutil.py
    goto :eof
)

if "%1" == "create-exes" (
    :create-exes
    call :clean
    C:\Python26\python.exe setup.py build bdist_wininst
    if %errorlevel% neq 0 goto :error
    C:\Python27\python.exe setup.py build bdist_wininst
    if %errorlevel% neq 0 goto :error
    C:\Python33\python.exe setup.py build bdist_wininst
    if %errorlevel% neq 0 goto :error
    goto :eof
)

:error
    echo last command returned an error; exiting
    exit /b %errorlevel%

goto :help