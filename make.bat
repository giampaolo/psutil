@echo off

rem ==========================================================================
rem Shortcuts for various tasks, emulating UNIX "make" on Windows.
rem It is primarly intended as a shortcut for compiling / installing
rem psutil ("make.bat build", "make.bat install") and running tests
rem ("make.bat test").
rem
rem This script is modeled after my Windows installation which uses:
rem - mingw32 for Python 2.4 and 2.5
rem - Visual studio 2008 for Python 2.6, 2.7, 3.2
rem - Visual studio 2010 for Python 3.3+
rem
rem By default C:\Python27\python.exe is used.
rem To compile for a specific Python version run:
rem
rem     set PYTHON=C:\Python24\python.exe & make.bat build
rem
rem If you compile by using mingw on Python 2.4 and 2.5 you need to patch
rem distutils first: http://stackoverflow.com/questions/13592192
rem ==========================================================================

if "%PYTHON%" == "" (
    set PYTHON=C:\Python27\python.exe
)
if "%TSCRIPT%" == "" (
    set TSCRIPT=test\test_psutil.py
)

rem Needed to compile using Mingw.
set PATH=C:\MinGW\bin;%PATH%

rem Needed to locate the .pypirc file and upload exes on PYPI.
set HOME=%USERPROFILE%

rem ==========================================================================

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
    rem mingw 32 versions
    C:\Python24\python.exe setup.py build -c mingw32 bdist_wininst || goto :error
    C:\Python25\python.exe setup.py build -c mingw32 bdist_wininst || goto :error
    rem "standard" 32 bit versions, using VS 2008 (2.6, 2.7) or VS 2010 (3.3+)
    C:\Python26\python.exe setup.py build bdist_wininst || goto :error
    C:\Python27\python.exe setup.py build bdist_wininst || goto :error
    C:\Python33\python.exe setup.py build bdist_wininst || goto :error
    C:\Python34\python.exe setup.py build bdist_wininst || goto :error
    rem 64 bit versions
    rem Python 2.7 + VS 2008 requires vcvars64.bat to be run first:
    rem http://stackoverflow.com/questions/11072521/
    rem Windows SDK and .NET Framework 3.5 SP1 also need to be installed (sigh)
    "C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\bin\vcvars64.bat"
    C:\Python27-64\python.exe setup.py build bdist_wininst || goto :error
    C:\Python33-64\python.exe setup.py build bdist_wininst || goto :error
    C:\Python34-64\python.exe setup.py build bdist_wininst || goto :error
    echo OK
    goto :eof
)

if "%1" == "upload-exes" (
    :upload-exes
    rem mingw 32 versions
    C:\Python25\python.exe setup.py build -c mingw32 bdist_wininst upload || goto :error
    rem "standard" 32 bit versions, using VS 2008 (2.6, 2.7) or VS 2010 (3.3+)
    C:\Python26\python.exe setup.py bdist_wininst upload || goto :error
    C:\Python27\python.exe setup.py bdist_wininst upload || goto :error
    C:\Python33\python.exe setup.py bdist_wininst upload || goto :error
    C:\Python34\python.exe setup.py bdist_wininst upload || goto :error
    rem 64 bit versions
    C:\Python27-64\python.exe setup.py build bdist_wininst upload || goto :error
    C:\Python33-64\python.exe setup.py build bdist_wininst upload || goto :error
    C:\Python34-64\python.exe setup.py build bdist_wininst upload || goto :error
    echo OK
    goto :eof
)

goto :help

:error
    echo last command exited with error code %errorlevel%
    exit /b %errorlevel%
    goto :eof
