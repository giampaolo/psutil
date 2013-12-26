@ECHO OFF

REM ==========================================================================
REM Shortcuts for various tasks, emulating UNIX "make" on Windows.
REM Use this script for various tasks such as installing psutil or
REM running tests ("make.bat test").
REM This script is modeled after my Windows installation so it might
REM need some adjustements in order to work on your system.
REM By default C:\Python27\python.exe is used.
REM To run another Python version run:
REM set PYTHON=C:\Python33\python.exe & make test
REM In case of Python 2.4 and 2.5 mingw32 compiler is used.
REM ==========================================================================


if "%PYTHON%" == "" (
    SET PYTHON=C:\Python27\python.exe
)
if "%TSCRIPT%" == "" (
    SET TSCRIPT=test\test_psutil.py
)
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
    echo   memtest       run memory leak tests
    echo   build-exes    create exe installers in dist directory
    echo   upload-exes   upload exe installers on pypi
    goto :eof
)

if "%1" == "clean" (
    :clean
    for /r %%R in (__pycache__) do if exist %%R (rmdir /S /Q %%R)
    for /r %%R in (*.pyc) do if exist %%R (del /s %%R)
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
    %PYTHON% %TSCRIPT%
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
