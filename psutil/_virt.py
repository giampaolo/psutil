# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Routines & strategies to guess whether we're running inside a virtual
machine.

LINUX
=====

This implementation is a port of `systemd-detect-virt` C CLI tool
and tries to mimick it as much as possible:
https://github.com/systemd/systemd/blob/main/src/basic/virt.c
I attempted to do a literal C -> Python translation whenever possible,
including respecting the original order in which the various 'guess'
functions are being called.
Differences with `systemd-detect-virt`:
* systemd-detect-virt returns 'oracle', we return 'virtualbox'

In addition, it uses a couple of strategies of `virt-what` bash script:
* detects "ibm-systemz"

WINDOWS
=======

We simply interpret the string returned by __cpuid() syscall, if any.
Useful references:
* https://artemonsecurity.com/vmde.pdf
"""

import os
import re

from ._common import LINUX
from ._common import WINDOWS
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import cat
from ._common import debug
from ._common import get_procfs_path
from ._common import open_binary
from ._common import open_text


# virtualization strings

VIRTUALIZATION_ACRN = "acrn"
VIRTUALIZATION_AMAZON = "amazon"
VIRTUALIZATION_BHYVE = "bhyve"
VIRTUALIZATION_BOCHS = "bochs"
VIRTUALIZATION_DOCKER = "docker"
VIRTUALIZATION_IBM_SYSTEMZ = "ibm-systemz"  # detected by virt-what
VIRTUALIZATION_KVM = "kvm"
VIRTUALIZATION_LXC = "lxc"
VIRTUALIZATION_LXC_LIBVIRT = "lxc-libvirt"
VIRTUALIZATION_MICROSOFT = "microsoft"
VIRTUALIZATION_OPENVZ = "openvz"
VIRTUALIZATION_PARALLELS = "parallels"
VIRTUALIZATION_PODMAN = "podman"
VIRTUALIZATION_POWERVM = "powervm"
VIRTUALIZATION_PROOT = "proot"
VIRTUALIZATION_QEMU = "qemu"
VIRTUALIZATION_QNX = "qnx"
VIRTUALIZATION_RKT = "rkt"
VIRTUALIZATION_SYSTEMD_NSPAWN = "systemd-nspawn"
VIRTUALIZATION_UML = "uml"
VIRTUALIZATION_VIRTUALBOX = "virtualbox"
VIRTUALIZATION_VMWARE = "vmware"
VIRTUALIZATION_WSL = "wsl"
VIRTUALIZATION_XEN = "xen"
VIRTUALIZATION_ZVM = "zvm"

VIRTUALIZATION_CONTAINER_OTHER = "container-other"
VIRTUALIZATION_VM_OTHER = "vm-other"

# https://evasions.checkpoint.com/techniques/cpu.html
CPUID_VENDOR_TABLE = {
    "ACRNACRNACRN": VIRTUALIZATION_ACRN,
    "bhyve bhyve ": VIRTUALIZATION_BHYVE,
    "KVMKVMKVM": VIRTUALIZATION_KVM,
    "Microsoft Hv": VIRTUALIZATION_MICROSOFT,
    "prl hyperv": VIRTUALIZATION_PARALLELS,  # on Windows only
    "QNXQVMBSQG": VIRTUALIZATION_QNX,
    "TCGTCGTCGTCG": VIRTUALIZATION_QEMU,
    "VBoxVBoxVBox": VIRTUALIZATION_VIRTUALBOX,  # on Windows only
    "VMwareVMware": VIRTUALIZATION_VMWARE,
    "XenVMMXenVMM": VIRTUALIZATION_XEN,
}


# =====================================================================
# --- Linux
# =====================================================================

if LINUX:
    from . import _psutil_linux as cext
    from ._pslinux import Process

    class _VirtualizationBase:
        __slots__ = ["procfs_path"]

        def __init__(self):
            self.procfs_path = get_procfs_path()

    class ContainerDetector(_VirtualizationBase):
        """A "container" is typically "shared kernel virtualization",
        e.g. LXC.
        """

        def _container_from_string(self, s):
            s = s.strip()
            assert s, repr(s)
            mapping = {
                "docker": VIRTUALIZATION_DOCKER,
                "lxc": VIRTUALIZATION_LXC,
                "lxc-libvirt": VIRTUALIZATION_LXC_LIBVIRT,
                "podman": VIRTUALIZATION_PODMAN,
                "rkt": VIRTUALIZATION_RKT,
                "systemd-nspawn": VIRTUALIZATION_SYSTEMD_NSPAWN,
                "wsl": VIRTUALIZATION_WSL,
            }

            if s == "oci":
                # Some images hardcode container=oci, but OCI is not
                # a specific container manager. Try to detect one
                # based on well-known files.
                try:
                    return self.look_for_known_files() or \
                        VIRTUALIZATION_CONTAINER_OTHER
                except Exception as err:
                    debug(err)
                    return VIRTUALIZATION_CONTAINER_OTHER

            for k, v in mapping.items():
                if s.lower().startswith(k):
                    return v

            return VIRTUALIZATION_CONTAINER_OTHER

        def detect_openvz(self):
            # Check for OpenVZ / Virtuozzo.
            # /proc/vz exists in container and outside of the container,
            # /proc/bc only outside of the container.
            if os.path.exists("%s/vz" % self.procfs_path):
                if not os.path.exists("%s/bc" % self.procfs_path):
                    return VIRTUALIZATION_OPENVZ

        def detect_wsl(self):
            # "Official" way of detecting WSL:
            # https://github.com/Microsoft/WSL/issues/423#issuecomment-221627364
            data = cat('%s/sys/kernel/osrelease' % self.procfs_path)
            if "Microsoft" in data or "WSL" in data:
                return VIRTUALIZATION_WSL

        def detect_proot(self):
            data = cat('%s/self/status' % self.procfs_path)
            m = re.search(r'TracerPid:\t(\d+)', data)
            if m:
                tracer_pid = int(m.group(1))
                if tracer_pid != 0:
                    pname = Process(tracer_pid).name()
                    if pname.startswith("proot"):
                        return VIRTUALIZATION_PROOT

        def ask_run_host(self):
            # The container manager might have placed this in the /run/host/
            # hierarchy for us, which is good because it doesn't require root
            # privileges.
            data = cat("/run/host/container-manager")
            return self._container_from_string(data)

        def ask_run_systemd(self):
            # ...Otherwise PID 1 might have dropped this information into a
            # file in /run. This is better than accessing /proc/1/environ,
            # since we don't need CAP_SYS_PTRACE for that.
            data = cat("/run/systemd/container")
            return self._container_from_string(data)

        def ask_pid_1(self):
            # Only works if running as root or if we have CAP_SYS_PTRACE.
            env = Process(1).environ()
            if "container" in env:
                return self._container_from_string(env["container"])

        def look_for_known_files(self):
            # Check for existence of some well-known files. We only do this
            # after checking for other specific container managers, otherwise
            # we risk mistaking another container manager for Docker: the
            # /.dockerenv file could inadvertently end up in a file system
            # image.
            if os.path.exists("/run/.containerenv"):
                # https://github.com/containers/podman/issues/6192
                # https://github.com/containers/podman/issues/3586#issuecomment-661918679
                return VIRTUALIZATION_PODMAN
            if os.path.exists("/.dockerenv"):
                # https://github.com/moby/moby/issues/18355
                return VIRTUALIZATION_DOCKER
            # Note: virt-what also checks for `/.dockerinit`.

    class VmDetector(_VirtualizationBase):
        """A "vm" means "full hardware virtualization", e.g. VirtualBox."""

        def ask_dmi(self):
            files = [
                "/sys/class/dmi/id/product_name",
                "/sys/class/dmi/id/sys_vendor",
                "/sys/class/dmi/id/board_vendor",
                "/sys/class/dmi/id/bios_vendor",
            ]
            vendors_table = {
                "KVM": VIRTUALIZATION_KVM,
                "Amazon EC2": VIRTUALIZATION_AMAZON,
                "QEMU": VIRTUALIZATION_QEMU,
                # https://kb.vmware.com/s/article/1009458
                "VMware": VIRTUALIZATION_VMWARE,
                "VMW": VIRTUALIZATION_VMWARE,
                "innotek GmbH": VIRTUALIZATION_VIRTUALBOX,
                "Oracle Corporation": VIRTUALIZATION_VIRTUALBOX,
                "Xen": VIRTUALIZATION_XEN,
                "Bochs": VIRTUALIZATION_BOCHS,
                "Parallels": VIRTUALIZATION_PARALLELS,
                # https://wiki.freebsd.org/bhyve
                "BHYVE": VIRTUALIZATION_BHYVE,
            }
            for file in files:
                out = cat(file, fallback="").strip()
                for k, v in vendors_table.items():
                    if out.startswith(k):
                        debug("virtualization found in file %r" % file)
                        return v

        def detect_uml(self):
            with open_binary('%s/cpuinfo' % self.procfs_path) as f:
                for line in f:
                    if line.lower().startswith(b"vendor_id"):
                        value = line.partition(b":")[2].strip()
                        if value == b"User Mode Linux":
                            return VIRTUALIZATION_UML

        def ask_cpuid(self):
            vendor = cext.linux_cpuid()
            if vendor and vendor in CPUID_VENDOR_TABLE:
                return CPUID_VENDOR_TABLE[vendor]

        def detect_xen(self):
            if os.path.exists('%s/xen' % self.procfs_path):
                return VIRTUALIZATION_XEN
            data = cat("/sys/hypervisor/type").strip()
            if data == "xen":
                return VIRTUALIZATION_XEN
            else:
                return VIRTUALIZATION_VM_OTHER

        def ask_device_tree(self):
            path = "%s/device-tree/hypervisor/compatible" % self.procfs_path
            data = cat(path).strip()
            if data == "linux,kvm":
                return VIRTUALIZATION_KVM
            elif data == "xen":
                return VIRTUALIZATION_XEN
            elif data == "vmware":
                return VIRTUALIZATION_VMWARE
            else:
                return VIRTUALIZATION_VM_OTHER

        def detect_powervm(self):
            base = "%s/device-tree" % self.procfs_path
            if os.path.exists("%s/ibm,partition-name" % base):
                if os.path.exists("%s/hmc-managed?" % base):
                    if not os.path.exists(
                            "%s/chosen/qemu,graphic-width" % base):
                        return VIRTUALIZATION_POWERVM

        def detect_qemu(self):
            if "fw-cfg" in os.listdir("%s/device-tree" % self.procfs_path):
                return VIRTUALIZATION_QEMU
            # https://unix.stackexchange.com/a/89718
            for name in os.listdir("/dev/disk/by-id/"):
                if "QEMU" in name:
                    return VIRTUALIZATION_QEMU

        def detect_zvm(self):
            with open_text("%s/sysinfo" % self.procfs_path) as f:
                for line in f:
                    if line.startswith("VM00 Control Program"):
                        if "z/VM" in line.partition("VM00 Control Program")[2]:
                            return VIRTUALIZATION_ZVM
                        else:
                            return VIRTUALIZATION_KVM

    class VmDetectorOthers(_VirtualizationBase):
        """Mostly stuff took from `virt-what` bash script."""

        def ask_proc_cpuinfo(self):
            with open_binary('%s/cpuinfo' % self.procfs_path) as f:
                for line in f:
                    if line.lower().startswith(b"vendor_id"):
                        value = line.partition(b":")[2].strip()
                        if b"PowerVM Lx86" in value:
                            return VIRTUALIZATION_POWERVM
                        elif b"IBM/S390" in value:
                            return VIRTUALIZATION_IBM_SYSTEMZ

    def get_functions():
        # There is a distinction between containers and VMs.
        # A "container" is typically "shared kernel virtualization", e.g. LXC.
        # A "vm" is "full hardware virtualization", e.g. VirtualBox.
        # If multiple virtualization solutions are used, only the innermost
        # is detected and identified. E.g. if both machine and container
        # virtualization are used in conjunction, only the latter will be
        # returned.
        container = ContainerDetector()
        vm = VmDetector()
        vmothers = VmDetectorOthers()
        # order matters (FIFO), and it's the same as `systemd-detect-virt`.
        funcs = [
            # containers
            container.detect_openvz,
            container.detect_wsl,
            container.detect_proot,
            container.ask_run_host,
            container.ask_run_systemd,
            container.ask_pid_1,
            container.look_for_known_files,  # podman / docker
            # vms
            vm.ask_dmi,
            vm.detect_uml,  # uml
            vm.ask_cpuid,
            vm.detect_xen,  # xen
            vm.ask_device_tree,
            vm.detect_powervm,
            vm.detect_qemu,
            vm.detect_zvm,  # zvm
            # vms others
            vmothers.ask_proc_cpuinfo,
        ]
        return funcs

# =====================================================================
# --- Windows
# =====================================================================

elif WINDOWS:
    from . import _psutil_windows as cext
    import winreg

    def _winreg_key_exists(name, base=winreg.HKEY_LOCAL_MACHINE):
        debug("checking %r" % name)
        reg = winreg.ConnectRegistry(None, base)
        try:
            with winreg.OpenKey(reg, name, 0, winreg.KEY_READ):
                return True
        except FileNotFoundError:
            return False

    def ask_cpuid():
        vendor = cext.cpuid()
        if vendor is not None:
            if vendor in CPUID_VENDOR_TABLE:
                return CPUID_VENDOR_TABLE[vendor]
            else:
                return VIRTUALIZATION_VM_OTHER

    def detect_vbox_from_registry():
        keys = [
            r"SOFTWARE\\Oracle\\VirtualBox Guest Additions",
            r"HARDWARE\\ACPI\\DSDT\\VBOX__",
            r"HARDWARE\\ACPI\\FADT\\VBOX__",
            r"HARDWARE\\ACPI\\RSDT\\VBOX__",
            r"SYSTEM\\ControlSet001\\Services\\VBoxGuest",
            r"SYSTEM\\ControlSet001\\Services\\VBoxMouse",
            r"SYSTEM\\ControlSet001\\Services\\VBoxService",
            r"SYSTEM\\ControlSet001\\Services\\VBoxSF",
            r"SYSTEM\\ControlSet001\\Services\\VBoxVideo",
        ]
        for k in keys:
            if _winreg_key_exists(k):
                return VIRTUALIZATION_VIRTUALBOX

    def get_functions():
        return [
            ask_cpuid,
            detect_vbox_from_registry,
        ]

# ---


def detect():
    funcs = get_functions()
    retval = None
    for func in funcs:
        func_name = "%s.%s" % (
            func.__self__.__class__.__name__, func.__name__)
        debug("trying method %r" % func_name)
        try:
            retval = func()
            if retval:
                break
        except (IOError, OSError) as err:
            debug(err)
        except (AccessDenied, NoSuchProcess) as err:
            debug(err)

    return retval or ""
