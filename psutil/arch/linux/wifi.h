/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <linux/wireless.h>

int ioctl_request(char *ifname, int request, struct iwreq *pwrq, int sock);
char *convert_macaddr(unsigned char *ptr);

PyObject* psutil_wifi_scan(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_essid(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_bssid(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_proto(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_mode(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_frequency(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_bitrate(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_txpower(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_ranges(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_stats(PyObject* self, PyObject* args);
PyObject* psutil_wifi_card_power_save(PyObject* self, PyObject* args);
