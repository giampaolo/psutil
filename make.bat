@echo off

rem ==========================================================================
rem Shortcuts for various tasks, emulating UNIX "make" on Windows.
rem It is primarly intended as a shortcut for compiling / installing
rem psutil and running tests (just run "make.bat test").
rem This script is modeled after my Windows installation which uses:
rem - mingw32 for Python 2.4 and 2.5
rem - Visual studio 2008 for Python 2.6, 2.7, 3.2
rem - Visual studio 2010 for Python 3.3+
rem By default C:\Python27\python.exe is used.
rem To use another Python version run:
rem     set PYTHON=C:\Python24\python.exe & make.bat test
rem ==========================================================================


if "%PYTHON%" == "" (
    set PYTHON=C:\Python27\python.exe
)
if "%TSCRIPT%" == "" (
    set TSCRIPT=test\test_psutil.py
)
set PATH=C:\MinGW\bin;%PATH%


if "%1" == "help" (
    :help
    echo Run `make ^<target^>` where ^<target^> is one of:
    echo   build         compile without installing
    echo   build-exes    create exe installers in dist directory
    echo   clean         clean build files
    echo   install       compile and install
    echo   memtest       run memory leak tests
    echo   test          run tests
    echo   test-process  run process related tests
    echo   test-system   run system APIs related tests
    echo   uninstall     uninstall
    echo   upload-exes   upload exe installers on pypi
    goto :eof
)

if "%1" == "clean" (
    :clean
    for /r %%R in (__pycache__) do if exist %%R (rmdir /S /Q %%R)
    for /r %%R in (*.pyc) do if exist %%R (del /s %%R)
    for /r %%R in (*.pyd) do if exist %%R (del /s %%R)
    for /r %%R in (*.orig) do if exist %%R (del /s %%R)
    for /r %%R in (*.bak) do if exist %%R (del /s %%R)
    for /r %%R in (*.rej) do if exist %%R (del /s %%R)
    if exist psutil.egg-info (rmdir /S /Q psutil.egg-info)
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
    if %PYTHON%==C:\Python24\python.exe (
        %PYTHON% setup.py build -c mingw32 install
    ) else if %PYTHON%==C:\Python25\python.exe (
        %PYTHON% setup.py build -c mingw32 install
    ) else (
        %PYTHON% setup.py build install
    )
    goto :eof
)

if "%1" == "uninstall" (
    :uninstall
    for %%A in ("%PYTHON%") do (
        set folder=%%~dpA
    )
    for /F "delims=" %%i in ('dir /b %folder%\Lib\site-packages\*psutil*') do (
        rmdir /S /Q %folder%\Lib\site-packages\%%i
    )
    goto :eof
)

if "%1" == "test" (
    :test
    call :install
    %PYTHON% %TSCRIPT%
    goto :eof
)

if "%1" == "test-process" (
    :test
    call :install
    %PYTHON% -m unittest -v test.test_psutil.TestProcess
    goto :eof
)

if "%1" == "test-system" (
    :test
    call :install
    %PYTHON% -m unittest -v test.test_psutil.TestSystem
    goto :eof
)

if "%1" == "memtest" (
    :memtest
    call :install
    %PYTHON% test\test_memory_leaks.py
    goto :eof
)

if "%1" == "build-exes" (
    :build-exes
    call :clean
    C:\Python26\python.exe setup.py build bdist_wininst & if %errorlevel% neq 0 goto :error
    C:\Python27\python.exe setup.py build bdist_wininst & if %errorlevel% neq 0 goto :error
    C:\Python33\python.exe setup.py build bdist_wininst & if %errorlevel% neq 0 goto :error
    goto :eof
)

if "%1" == "upload-exes" (
    :upload-exes
    C:\Python26\python.exe setup.py bdist_wininst upload  & if %errorlevel% neq 0 goto :error
    C:\Python27\python.exe setup.py bdist_wininst upload  & if %errorlevel% neq 0 goto :error
    C:\Python33\python.exe setup.py bdist_wininst upload  & if %errorlevel% neq 0 goto :error
    goto :eof
)

goto :help

:error
    echo last command returned an error; exiting
    exit /b %errorlevel%
