#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import textwrap

from github import Github


ROOT_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')


# --- constants


LABELS_MAP = {
    # platforms
    "linux": [
        "linux", "ubuntu", "redhat", "mint", "centos", "red hat", "archlinux",
        "debian", "alpine", "gentoo", "fedora", "slackware", "suse", "RHEL",
        "opensuse", "manylinux", "apt ", "apt-", "rpm", "yum", "kali",
        "/sys/class", "/proc/net", "/proc/disk", "/proc/smaps",
        "/proc/vmstat",
    ],
    "windows": [
        "windows", "win32", "WinError", "WindowsError", "win10", "win7",
        "win ", "mingw", "msys", "studio", "microsoft", "make.bat",
        "CloseHandle", "GetLastError", "NtQuery", "DLL", "MSVC", "TCHAR",
        "WCHAR", ".bat", "OpenProcess", "TerminateProcess", "appveyor",
        "windows error", "NtWow64", "NTSTATUS", "Visual Studio",
    ],
    "macos": [
        "macos", "mac ", "osx", "os x", "mojave", "sierra", "capitan",
        "yosemite", "catalina", "mojave", "big sur", "xcode", "darwin",
        "dylib",
    ],
    "aix": ["aix"],
    "cygwin": ["cygwin"],
    "freebsd": ["freebsd"],
    "netbsd": ["netbsd"],
    "openbsd": ["openbsd"],
    "sunos": ["sunos", "solaris"],
    "wsl": ["wsl"],
    "unix": [
        "psposix", "_psutil_posix", "waitpid", "statvfs", "/dev/tty",
        "/dev/pts",
    ],
    "pypy": ["pypy"],
    # types
    "enhancement": ["enhancement"],
    "memleak": ["memory leak", "leaks memory", "memleak", "mem leak"],
    "api": ["idea", "proposal", "api", "feature"],
    "performance": ["performance", "speedup", "speed up", "slow", "fast"],
    "wheels": ["wheel", "wheels"],
    "scripts": [
        "example script", "examples script", "example dir", "scripts/",
    ],
    # bug
    "bug": [
        "fail", "can't execute", "can't install", "cannot execute",
        "cannot install", "install error", "crash", "critical",
    ],
    # doc
    "doc": [
        "doc ", "document ", "documentation", "readthedocs", "pythonhosted",
        "HISTORY", "README", "dev guide", "devguide", "sphinx", "docfix",
        "index.rst",
    ],
    # tests
    "tests": [
        " test ", "tests", "travis", "coverage", "cirrus", "appveyor",
        "continuous integration", "unittest", "pytest", "unit test",
    ],
    # critical errors
    "priority-high": [
        "WinError", "WindowsError", "RuntimeError", "ZeroDivisionError",
        "SystemError", "MemoryError", "core dumped",
        "segfault", "segmentation fault",
    ],
}

LABELS_MAP['scripts'].extend(
    [x for x in os.listdir(SCRIPTS_DIR) if x.endswith('.py')])

OS_LABELS = [
    "linux", "windows", "macos", "freebsd", "openbsd", "netbsd", "openbsd",
    "bsd", "sunos", "unix", "wsl", "aix", "cygwin",
]

ILLOGICAL_PAIRS = [
    ('bug', 'enhancement'),
    ('doc', 'tests'),
    ('scripts', 'doc'),
    ('scripts', 'tests'),
    ('bsd', 'freebsd'),
    ('bsd', 'openbsd'),
    ('bsd', 'netbsd'),
]

# --- replies

REPLY_MISSING_PYTHON_HEADERS = """\
It looks like you're missing `Python.h` headers. This usually means you have \
to install them first, then retry psutil installation.
Please read \
[INSTALL](https://github.com/giampaolo/psutil/blob/master/INSTALL.rst) \
instructions for your platform. \
This is an auto-generated response based on the text you submitted. \
If this was a mistake or you think there's a bug with psutil installation \
process, please add a comment to reopen this issue.
"""


# --- utils


def is_pr(issue):
    return 'PullRequest' in issue.__module__


def is_issue(issue):
    return not is_pr(issue)


def is_new(issue):
    return issue.comments == 0


def has_label(issue, label):
    assigned = [x.name for x in issue.labels]
    return label in assigned


def has_os_label(issue):
    labels = set([x.name for x in issue.labels])
    for label in OS_LABELS:
        if label in labels:
            return True
    return False


def get_repo():
    repo = os.environ['GITHUB_REPOSITORY']
    token = os.environ['GITHUB_TOKEN']
    return Github(token).get_repo(repo)


def get_issue_event():
    url = os.environ.get('GITHUB_ISSUE_URL')
    if url:  # issue
        num = int(url.split('/')[-1])
    else:  # PR
        url = os.environ['GITHUB_REF']
        num = int(url.split('/')[-2])
    repo = get_repo()
    return repo.get_issue(number=num)


# --- actions


def log(msg):
    print(">>> %s <<<" % msg)


def add_label(issue, label):
    def should_add(issue, label):
        if has_label(issue, label):
            log("issue %r already has label %r" % (issue, label))
            return False

        for left, right in ILLOGICAL_PAIRS:
            if label == left and has_label(issue, right):
                log("issue %r already has label %r" % (issue, label))
                return False

        return not has_label(issue, label)

    if not should_add(issue, label):
        return

    type_ = "PR:" if is_pr(issue) else "issue:"
    assigned = ', '.join([x.name for x in issue.labels])
    log(textwrap.dedent("""\
        %-10s     %s: %s
        assigned:      %s
        new:           %s""" % (
        type_,
        issue.number,
        issue.title,
        assigned,
        label,
    )))
    issue.add_to_labels(label)


def _guess_labels_from_text(issue, text):
    for label, keywords in LABELS_MAP.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
                yield (label, keyword)


def add_labels_from_text(issue, text):
    for label, keyword in _guess_labels_from_text(issue, text):
        add_label(issue, label)


def add_labels_from_body(issue, text):
    # add os label
    print(repr(text))
    r = re.search(r"\* OS:.*?\n", text)
    if r:
        add_labels_from_text(issue, r.group(0))
    # add bug/enhancement label
    r = re.search(r"\* Bug fix:.*?\n", text)
    if is_pr(issue) and \
            r is not None and \
            not has_label(issue, "bug") and \
            not has_label(issue, "enhancement"):
        s = r.group(0).lower()
        if 'yes' in s:
            add_label(issue, 'bug')
        else:
            add_label(issue, 'enhancement')
    # add type labels
    r = re.search(r"\* Type:.*?\n", text)
    if r:
        s = r.group(0).lower()
        if 'doc' in s:
            add_label(issue, 'doc')
        if 'performance' in s:
            add_label(issue, 'performance')
        if 'scripts' in s:
            add_label(issue, 'scripts')
        if 'tests' in s:
            add_label(issue, 'tests')
        if 'wheels' in s:
            add_label(issue, 'wheels')
        if 'newapi' in s:
            add_label(issue, 'api')


# --- run


def process_both(issue):
    add_labels_from_text(issue, issue.title)
    add_labels_from_body(issue, issue.body)


def process_issue(issue):
    def has_text(text):
        return text in issue.title.lower() or text in issue.body.lower()

    if has_text("missing python.h") or \
            has_text("python.h: no such file or directory") or \
            "#include<Python.h>\n^~~~" in issue.body.replace(' ', '') or \
            "#include<Python.h>\r\n^~~~" in issue.body.replace(' ', ''):
        issue.create_comment(REPLY_MISSING_PYTHON_HEADERS)
        issue.edit(state='closed')
        return


def process_pr(pr):
    pass


def main():
    log("Running issue/PR bot.")
    issue = get_issue_event()
    process_both(issue)
    if is_issue(issue):
        process_issue(issue)
    else:
        process_pr(issue)


if __name__ == '__main__':
    main()
