/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
Original code was refactored and moved from psutil/arch/freebsd/specific.c
For reference, here's the git history with original(ish) implementations:
- sensors_battery(): 022cf0a05d34f4274269d4f8002ee95b9f3e32d2
- sensors_cpu_temperature(): bb5d032be76980a9e110f03f1203bd35fa85a793
  (patch by Alex Manuskin)
*/


#include <Python.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"


#define DECIKELVIN_2_CELSIUS(t) (t - 2731) / 10


PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    int percent;
    int minsleft;
    int power_plugged;
    size_t size = sizeof(percent);

    if (psutil_sysctlbyname("hw.acpi.battery.life", &percent, size) != 0)
        goto error;
    if (psutil_sysctlbyname("hw.acpi.battery.time", &minsleft, size) != 0)
        goto error;
    if (psutil_sysctlbyname("hw.acpi.acline", &power_plugged, size) != 0)
        goto error;
    return Py_BuildValue("iii", percent, minsleft, power_plugged);

error:
    // see: https://github.com/giampaolo/psutil/issues/1074
    if (errno == ENOENT)
        PyErr_SetString(PyExc_NotImplementedError, "no battery");
    else
        psutil_oserror();
    return NULL;
}


// Return temperature information for a given CPU core number.
PyObject *
psutil_sensors_cpu_temperature(PyObject *self, PyObject *args) {
    int current;
    int tjmax;
    int core;
    char sensor[26];
    size_t size = sizeof(current);

    if (!PyArg_ParseTuple(args, "i", &core))
        return NULL;
    str_format(sensor, sizeof(sensor), "dev.cpu.%d.temperature", core);
    if (psutil_sysctlbyname(sensor, &current, size) != 0)
        goto error;
    current = DECIKELVIN_2_CELSIUS(current);

    // Return -273 in case of failure.
    str_format(sensor, sizeof(sensor), "dev.cpu.%d.coretemp.tjmax", core);
    if (psutil_sysctlbyname(sensor, &tjmax, size) != 0)
        tjmax = 0;
    tjmax = DECIKELVIN_2_CELSIUS(tjmax);

    return Py_BuildValue("ii", current, tjmax);

error:
    if (errno == ENOENT)
        PyErr_SetString(PyExc_NotImplementedError, "no temperature sensors");
    else
        psutil_oserror();
    return NULL;
}
