#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Shortcuts for various tasks, emulating UNIX "make" command on
Windows. This script is supposed to be invoked via "make.bat" and not
used directly. Like on POSIX, you can run multiple targets serially:

    make.bat clean build test

To run a specific test:

    set ARGS=-k tests/test_system.py && make.bat test
"""

import fnmatch
import os
import shlex
import shutil
import site
import subprocess
import sys

import colorama

# configurable via CLI invocation
PYTHON = os.getenv('PYTHON', sys.executable)
ARGS = shlex.split(os.getenv("ARGS", ""))

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.realpath(os.path.join(HERE, "..", ".."))

colorama.init(autoreset=True)

# ===================================================================
# utils
# ===================================================================

_cmds = {}


def clicmd(fun):
    """Mark a function to be invoked as a make target."""
    _cmds[fun.__name__.replace("_", "-")] = fun
    return fun


def safe_print(text, file=sys.stdout):
    """Prints a (unicode) string to the console, encoded depending on
    the stdout/file encoding (eg. cp437 on Windows). This is to avoid
    encoding errors in case of funky path names.
    """
    if not isinstance(text, str):
        return print(text, file=file)
    try:
        print(text, file=file)
    except UnicodeEncodeError:
        bytes_string = text.encode(file.encoding, 'backslashreplace')
        if hasattr(file, 'buffer'):
            file.buffer.write(bytes_string)
        else:
            text = bytes_string.decode(file.encoding, 'strict')
            print(text, file=file)


def color(s, c):
    return c + s


red = lambda s: color(s, colorama.Fore.RED)  # noqa: E731
yellow = lambda s: color(s, colorama.Fore.YELLOW)  # noqa: E731
green = lambda s: color(s, colorama.Fore.GREEN)  # noqa: E731
white = lambda s: color(s, colorama.Fore.WHITE)  # noqa: E731


def sh(cmd):
    """Run a shell command, exit on failure."""
    assert isinstance(cmd, list), repr(cmd)
    safe_print(f"$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        env=os.environ,
        text=True,
        check=False,
    )

    if result.returncode:
        print(red(f"command failed with exit code {result.returncode}"))
        sys.exit(result.returncode)


def safe_remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except PermissionError as err:
        print(red(err))
    else:
        safe_print(f"rm {path}")


def safe_rmtree(path):
    def onerror(func, path, exc):
        if not issubclass(exc[0], FileNotFoundError):
            safe_print(exc[1])

    existed = os.path.isdir(path)
    shutil.rmtree(path, onerror=onerror)
    if existed and not os.path.isdir(path):
        safe_print(f"rmdir -f {path}")


def safe_rmpath(path):
    """Remove a file or directory at a given path."""
    if os.path.isdir(path):
        safe_rmtree(path)
    else:
        safe_remove(path)


def remove_recursive_patterns(*patterns):
    """Recursively remove files or directories matching the given
    patterns from root.
    """
    for root, dirs, files in os.walk('.'):
        root = os.path.normpath(root)
        if root.startswith('.git/'):
            continue
        for name in dirs + files:
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    safe_rmpath(os.path.join(root, name))


# ===================================================================
# commands
# ===================================================================


@clicmd
def build():
    """Build / compile."""
    # "build_ext -i" copies compiled *.pyd files in ./psutil directory in
    # order to allow "import psutil" when using the interactive interpreter
    # from within psutil root directory.
    cmd = [PYTHON, "setup.py", "build_ext", "-i"]
    if (os.cpu_count() or 1) > 1:
        cmd += ['--parallel', str(os.cpu_count())]
    # Print coloured warnings in real time.
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        for line in iter(p.stdout.readline, ''):
            line = line.strip()
            if 'warning' in line:
                print(yellow(line))
            elif (
                'error' in line
                and "errors.c" not in line
                and "errors.obj" not in line
                and "errors.o" not in line
            ):
                print(red(line))
            else:
                print(line)
        # retcode = p.poll()
        p.communicate()
        if p.returncode:
            print(red("failure"))
            sys.exit(p.returncode)
    finally:
        p.terminate()
        p.wait()

    # Make sure it actually worked.
    sh([PYTHON, "-c", "import psutil"])
    print(green("build + import successful"))


@clicmd
def install_pip():
    """Install pip."""
    sh([PYTHON, os.path.join(HERE, "install_pip.py")])


@clicmd
def install():
    """Install in develop / edit mode."""
    build()
    sh([PYTHON, "setup.py", "develop", "--user"])


@clicmd
def uninstall():
    """Uninstall psutil."""
    # Uninstalling psutil on Windows seems to be tricky.
    # On "import psutil" tests may import a psutil version living in
    # C:\PythonXY\Lib\site-packages which is not what we want, so
    # we try both "pip uninstall psutil" and manually remove stuff
    # from site-packages.
    clean()
    install_pip()
    here = os.getcwd()
    try:
        os.chdir('C:\\')
        while True:
            try:
                import psutil  # noqa: F401
            except ImportError:
                break
            else:
                sh([PYTHON, "-m", "pip", "uninstall", "-y", "psutil"])
    finally:
        os.chdir(here)

    for dir in site.getsitepackages():
        for name in os.listdir(dir):
            if name.startswith('psutil'):
                safe_rmpath(os.path.join(dir, name))
            elif name == 'easy-install.pth':
                # easy_install can add a line (installation path) into
                # easy-install.pth; that line alters sys.path.
                path = os.path.join(dir, name)
                with open(path) as f:
                    lines = f.readlines()
                    hasit = False
                    for line in lines:
                        if 'psutil' in line:
                            hasit = True
                            break
                if hasit:
                    with open(path, "w") as f:
                        for line in lines:
                            if 'psutil' not in line:
                                f.write(line)
                            else:
                                print(f"removed line {line!r} from {path!r}")


@clicmd
def clean():
    """Delete build files."""
    remove_recursive_patterns(
        "$testfn*",
        "*.bak",
        "*.core",
        "*.egg-info",
        "*.orig",
        "*.pyc",
        "*.pyd",
        "*.pyo",
        "*.rej",
        "*.so",
        "*.~",
        "*__pycache__",
        ".coverage",
        ".failed-tests.txt",
        "pytest-cache-files*",
    )
    for path in (
        "build",
        ".coverage",
        "dist",
        "docs/_build",
        "htmlcov",
        "tmp",
    ):
        safe_rmpath(path)


@clicmd
def install_pydeps_test():
    install_pip()
    install_git_hooks()
    sh([PYTHON, "-m", "pip", "install", "--user", "-U", "-e", ".[test]"])


@clicmd
def install_pydeps_dev():
    install_pip()
    install_git_hooks()
    sh([PYTHON, "-m", "pip", "install", "--user", "-U", "-e", ".[dev]"])


@clicmd
def test(args=ARGS):
    """Run tests."""
    # Disable pytest cache on Windows because we usually get
    # PermissionDenied on start. Related to network drives (e.g. Z:\).
    sh([
        PYTHON,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--ignore=tests/test_memleaks.py",
        *args,
    ])


@clicmd
def test_parallel():
    """Run tests in parallel."""
    test(args=["-n", "auto", "--dist", "loadgroup"])


@clicmd
def coverage():
    sh([PYTHON, "-m", "coverage", "run", "-m", "pytest"])
    sh([PYTHON, "-m", "coverage", "report"])
    sh([PYTHON, "-m", "coverage", "html"])
    sh([PYTHON, "-m", "webbrowser", "-t", "htmlcov/index.html"])


@clicmd
def test_process():
    sh([PYTHON, "-m", "pytest", "-k", "test_process.py"])


@clicmd
def test_system():
    sh([PYTHON, "-m", "pytest", "-k", "test_system.py"])


@clicmd
def test_platform():
    sh([PYTHON, "-m", "pytest", "-k", "test_windows.py"])


@clicmd
def test_last_failed():
    test(args=["--last-failed"])


@clicmd
def test_memleaks():
    sh([PYTHON, "-m", "pytest", "-k", "test_memleaks.py"])


@clicmd
def install_git_hooks():
    if os.path.isdir('.git'):
        src = os.path.join(
            ROOT_DIR, "scripts", "internal", "git_pre_commit.py"
        )
        dst = os.path.realpath(
            os.path.join(ROOT_DIR, ".git", "hooks", "pre-commit")
        )
        with open(src) as s, open(dst, "w") as d:
            d.write(s.read())


@clicmd
def generate_manifest():
    """Generate MANIFEST.in file."""
    script = "scripts\\internal\\generate_manifest.py"
    out = subprocess.check_output([PYTHON, script], text=True)
    with open("MANIFEST.in", "w", newline="\n") as f:
        f.write(out)


def parse_args():
    if len(sys.argv) <= 1:
        # print commands and exit
        for name in sorted(_cmds):
            doc = _cmds[name].__doc__ or ""
            print(f"{green(name):<30} {white(doc)}")
        return sys.exit(0)

    funcs = []
    for cmd in sys.argv[1:]:
        if cmd not in _cmds:
            return sys.exit(f"winmake: no target '{cmd}'")
        funcs.append(_cmds[cmd])

    return funcs  # the 'commands' to execute serially


def main():
    os.environ["PYTHON"] = PYTHON  # propagate it to subprocesses
    for fun in parse_args():
        fun()


if __name__ == '__main__':
    main()
