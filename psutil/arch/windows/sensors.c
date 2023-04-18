/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>


// Added in https://github.com/giampaolo/psutil/commit/109f873 in 2017.
// Moved in here in 2023.
PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    SYSTEM_POWER_STATUS sps;

    if (GetSystemPowerStatus(&sps) == 0) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    return Py_BuildValue(
        "iiiI",
        sps.ACLineStatus,  // whether AC is connected: 0=no, 1=yes, 255=unknown
        // status flag:
        // 1, 2, 4 = high, low, critical
        // 8 = charging
        // 128 = no battery
        sps.BatteryFlag,
        sps.BatteryLifePercent,  // percent
        sps.BatteryLifeTime  // remaining secs
    );
}
