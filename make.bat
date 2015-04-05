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
    echo   build-wheels  create wheel installers in dist directory
    echo   build-all     build exes + wheels
    echo   clean         clean build files
    echo   install       compile and install
    echo   setup-env     install pip, unittest2, wheels for all python versions
    echo   test          run tests
    echo   test-memleaks run memory leak tests
    echo   test-process  run process related tests
    echo   test-system   run system APIs related tests
    echo   uninstall     uninstall
    echo   upload-exes   upload exe installers on pypi
    echo   upload-wheels upload wheel installers on pypi
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
    %PYTHON% setup.py install
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
    %PYTHON% -m unittest -v test.test_psutil.TestProcess
    goto :eof
)

if "%1" == "test-system" (
    call :install
    %PYTHON% -m unittest -v test.test_psutil.TestSystem
    goto :eof
)

if "%1" == "test-memleaks" (
    call :install
    %PYTHON% test\test_memory_leaks.py
    goto :eof
)

if "%1" == "build-exes" (
    :build-exes
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

if "%1" == "build-wheels" (
    :build-wheels
    C:\Python26\python.exe setup.py build bdist_wheel || goto :error
    C:\Python27\python.exe setup.py build bdist_wheel || goto :error
    C:\Python33\python.exe setup.py build bdist_wheel || goto :error
    C:\Python34\python.exe setup.py build bdist_wheel || goto :error
    rem 64 bit versions
    rem Python 2.7 + VS 2008 requires vcvars64.bat to be run first:
    rem http://stackoverflow.com/questions/11072521/
    rem Windows SDK and .NET Framework 3.5 SP1 also need to be installed (sigh)
    "C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\bin\vcvars64.bat"
    C:\Python27-64\python.exe setup.py build bdist_wheel || goto :error
    C:\Python33-64\python.exe setup.py build bdist_wheel || goto :error
    C:\Python34-64\python.exe setup.py build bdist_wheel || goto :error
    echo OK
    goto :eof
)

if "%1" == "build-all" (
    rem for some reason this needs to be called twice (f**king windows...)
    call :build-exes
    call :build-exes
    echo OK
    goto :eof
)

if "%1" == "upload-exes" (
    :upload-exes
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

if "%1" == "upload-wheels" (
    :build-wheels
    C:\Python26\python.exe setup.py build bdist_wheel upload || goto :error
    C:\Python27\python.exe setup.py build bdist_wheel upload || goto :error
    C:\Python33\python.exe setup.py build bdist_wheel upload || goto :error
    C:\Python34\python.exe setup.py build bdist_wheel upload || goto :error
    rem 64 bit versions
    rem Python 2.7 + VS 2008 requires vcvars64.bat to be run first:
    rem http://stackoverflow.com/questions/11072521/
    rem Windows SDK and .NET Framework 3.5 SP1 also need to be installed (sigh)
    "C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\bin\vcvars64.bat"
    C:\Python27-64\python.exe setup.py build bdist_wheel upload || goto :error
    C:\Python33-64\python.exe setup.py build bdist_wheel upload || goto :error
    C:\Python34-64\python.exe setup.py build bdist_wheel upload || goto :error
    echo OK
    goto :eof
)

if "%1" == "upload-all" (
    call :upload-exes
    call :upload-wheels
    echo OK
    goto :eof
)

if "%1" == "setup-env" (
    echo downloading pip installer
    C:\python27\python.exe -c "import urllib2; url = urllib2.urlopen('https://raw.github.com/pypa/pip/master/contrib/get-pip.py'); data = url.read(); f = open('get-pip.py', 'w'); f.write(data)"
    C:\python26\python.exe get-pip.py & C:\python26\scripts\pip install unittest2 wheel ipaddress --upgrade
    C:\python27\python.exe get-pip.py & C:\python27\scripts\pip install wheel ipaddress --upgrade
    C:\python33\python.exe get-pip.py & C:\python33\scripts\pip install wheel ipaddress --upgrade
    C:\python34\scripts\easy_install.exe wheel
    rem 64-bit versions
    C:\python27-64\python.exe get-pip.py & C:\python27-64\scripts\pip install wheel ipaddress --upgrade
    C:\python33-64\python.exe get-pip.py & C:\python33-64\scripts\pip install wheel ipaddress --upgrade
    C:\python34-64\scripts\easy_install.exe wheel
    rem install ipdb only for py 2.7 and 3.4
    C:\python27\scripts\pip install ipdb --upgrade
    C:\python34\scripts\easy_install.exe ipdb
    goto :eof
)

goto :help

:error
    echo ------------------------------------------------
    echo last command exited with error code %errorlevel%
    echo ------------------------------------------------
    exit /b %errorlevel%
    goto :eof
