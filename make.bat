@echo off

rem ==========================================================================
rem Shortcuts for various tasks, emulating UNIX "make" on Windows.
rem It is primarly intended as a shortcut for compiling / installing
rem psutil ("make.bat build", "make.bat install") and running tests
rem ("make.bat test").
rem
rem This script is modeled after my Windows installation which uses:
rem - Visual studio 2008 for Python 2.6, 2.7, 3.2
rem - Visual studio 2010 for Python 3.3+
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
    set PYTHON=C:\Python27\python.exe
)
if "%TSCRIPT%" == "" (
    set TSCRIPT=psutil\tests\runner.py
)

set VSINSTALLDIR=%VS90COMNTOOLS%..\..

set PYTHON26=C:\Python26\python.exe
set PYTHON27=C:\Python27\python.exe
set PYTHON33=C:\Python33\python.exe
set PYTHON34=C:\Python34\python.exe
set PYTHON35=C:\Python35\python.exe
set PYTHON26-64=C:\Python26-64\python.exe
set PYTHON27-64=C:\Python27-64\python.exe
set PYTHON33-64=C:\Python33-64\python.exe
set PYTHON34-64=C:\Python34-64\python.exe
set PYTHON35-64=C:\Python35-64\python.exe

set ALL_PYTHONS=%PYTHON26% %PYTHON27% %PYTHON33% %PYTHON34% %PYTHON35% %PYTHON26-64% %PYTHON27-64% %PYTHON33-64% %PYTHON34-64% %PYTHON35-64%

rem Needed to locate the .pypirc file and upload exes on PYPI.
set HOME=%USERPROFILE%

rem ==========================================================================

if "%1" == "help" (
    :help
    echo Run `make ^<target^>` where ^<target^> is one of:
    echo   build         compile without installing
    echo   build-all     build exes + wheels
    echo   clean         clean build files
    echo   flake8        run flake8
    echo   install       compile and install
    echo   setup-dev-env install/upgrade pip, pywin32, wheels, etc.
    echo   setup-dev-env-all same as above, for all python versions
    echo   test          run tests
    echo   test-memleaks run memory leak tests
    echo   test-process  run process related tests
    echo   test-system   run system APIs related tests
    echo   test-platform platform-specific Windows tests
    echo   uninstall     uninstall
    echo   upload-all    upload exes + wheels
    goto :eof
)

if "%1" == "clean" (
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
    "%VSINSTALLDIR%\VC\bin\vcvars64.bat"
    %PYTHON% setup.py build
    if %errorlevel% neq 0 goto :error
	rem copies *.pyd files in ./psutil directory in order to allow
	rem "import psutil" when using the interactive interpreter from
    rem within this directory.
    %PYTHON% setup.py build_ext -i
    if %errorlevel% neq 0 goto :error
    goto :eof
)

if "%1" == "install" (
    :install
    call :build
    %PYTHON% setup.py develop
    goto :eof
)

if "%1" == "uninstall" (
    for %%A in ("%PYTHON%") do (
        set folder=%%~dpA
    )
    for /F "delims=" %%i in ('dir /b %folder%\Lib\site-packages\*psutil*') do (
        rmdir /S /Q %folder%\Lib\site-packages\%%i
    )
    goto :eof
)

if "%1" == "test" (
    call :install
    %PYTHON% %TSCRIPT%
    goto :eof
)

if "%1" == "test-process" (
    call :install
    %PYTHON% -m unittest -v psutil.tests.test_process
    goto :eof
)

if "%1" == "test-system" (
    call :install
    %PYTHON% -m unittest -v psutil.tests.test_system
    goto :eof
)

f "%1" == "test-platform" (
    call :install
    %PYTHON% psutil\tests\test_windows.py
    goto :eof
)

if "%1" == "test-by-name" (
    call :install
    %PYTHON% -m nose psutil\tests\test_process.py psutil\tests\test_system.py psutil\tests\test_windows.py psutil\tests\test_misc.py --nocapture -v -m %2
    goto :eof
)

if "%1" == "test-memleaks" (
    call :install
    %PYTHON% test\test_memory_leaks.py
    goto :eof
)

if "%1" == "build-all" (
    :build-all
    "%VSINSTALLDIR%\VC\bin\vcvars64.bat"
    for %%P in (%ALL_PYTHONS%) do (
        @echo ------------------------------------------------
        @echo building exe for %%P
        @echo ------------------------------------------------
        %%P setup.py build bdist_wininst || goto :error
        @echo ------------------------------------------------
        @echo building wheel for %%P
        @echo ------------------------------------------------
        %%P setup.py build bdist_wheel || goto :error
    )
    echo OK
    goto :eof
)

if "%1" == "upload-all" (
    :upload-exes
    "%VSINSTALLDIR%\VC\bin\vcvars64.bat"
    for %%P in (%ALL_PYTHONS%) do (
        @echo ------------------------------------------------
        @echo uploading exe for %%P
        @echo ------------------------------------------------
        %%P setup.py build bdist_wininst upload || goto :error
        @echo ------------------------------------------------
        @echo uploading wheel for %%P
        @echo ------------------------------------------------
        %%P setup.py build bdist_wheel upload || goto :error
    )
    echo OK
    goto :eof
)

if "%1" == "setup-dev-env" (
    :setup-env
    if not exist get-pip.py (
        @echo ------------------------------------------------
        @echo downloading pip installer
        @echo ------------------------------------------------
        C:\python27\python.exe -c "import urllib2; r = urllib2.urlopen('https://bootstrap.pypa.io/get-pip.py'); open('get-pip.py', 'wb').write(r.read())"
    )
    @echo ------------------------------------------------
    @echo installing pip for %PYTHON%
    @echo ------------------------------------------------
    %PYTHON% get-pip.py
    @echo ------------------------------------------------
    @echo upgrade pip for %PYTHON%
    @echo ------------------------------------------------
    %PYTHON% -m pip install pip --upgrade
    @echo ------------------------------------------------
    @echo installing deps
    @echo ------------------------------------------------
    rem mandatory / for unittests
    %PYTHON% -m pip install unittest2 ipaddress mock wmi wheel pypiwin32 --upgrade
    rem nice to have
    rem %PYTHON% -m pip install ipdb nose --upgrade
    goto :eof
)

if "%1" == "setup-dev-env-all" (
    :setup-env
    if not exist get-pip.py (
        @echo ------------------------------------------------
        @echo downloading pip installer
        @echo ------------------------------------------------
        C:\python27\python.exe -c "import urllib2; r = urllib2.urlopen('https://bootstrap.pypa.io/get-pip.py'); open('get-pip.py', 'wb').write(r.read())"
    )
    for %%P in (%ALL_PYTHONS%) do (
        @echo ------------------------------------------------
        @echo installing pip for %%P
        @echo ------------------------------------------------
        %%P get-pip.py
        @echo ------------------------------------------------
        @echo installing deps for %%P
        @echo ------------------------------------------------
        rem mandatory / for unittests
        %%P -m pip install unittest2 ipaddress mock wmi wheel pypiwin32 --upgrade
        rem nice to have
        rem %%P -m pip install ipdb nose --upgrade
    )
    goto :eof
)


if "%1" == "flake8" (
    :flake8
    %PYTHON% -c "from flake8.main import main; main()"
    goto :eof
)

goto :help

:error
    @echo ------------------------------------------------
    @echo last command exited with error code %errorlevel%
    @echo ------------------------------------------------
    @exit /b %errorlevel%
    goto :eof
