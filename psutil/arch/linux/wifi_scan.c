/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Routines to scan Wi-Fi networks.

#include <sys/ioctl.h>
#include <linux/wireless.h>

#include "../../_psutil_common.h"
#include "wifi.h"


#define SCAN_INTERVAL 100000  // 0.1 secs
#define SSID_MAX_LEN 32


typedef uint8_t u8;
typedef uint16_t u16;

struct wpa_scan_results {
    struct wpa_scan_res **res;
    size_t num;
};

struct wext_scan_data {
    struct wpa_scan_results res;
    u8 *ie;
    size_t ie_len;
    u8 ssid[SSID_MAX_LEN];
    size_t ssid_len;
    int maxrate;
};


static int
get_we_version(char *ifname, int sock) {
    struct iwreq wrq;
    char buffer[sizeof(struct iw_range) * 2];  // large enough
    struct iw_range *range;

    memset(buffer, 0, sizeof(buffer));
    wrq.u.data.pointer = (caddr_t) buffer;
    wrq.u.data.length = sizeof(buffer);
    wrq.u.data.flags = 0;

    if (ioctl_request(ifname, SIOCGIWRANGE, &wrq, sock) != 0)
        return -1;

    range = (struct iw_range *)buffer;
    return range->we_version_compiled;
}


static int
wext_19_iw_point(u16 cmd, int we_version) {
    return we_version > 18 &&
        (cmd == SIOCGIWESSID || cmd == SIOCGIWENCODE ||
         cmd == IWEVGENIE || cmd == IWEVCUSTOM);
}


static void
wext_get_scan_ssid(struct iw_event *iwe,
                   struct wext_scan_data *res,
                   char *custom,
                   char *end)
{
    int ssid_len = iwe->u.essid.length;
    if (custom + ssid_len > end)
        return;
    if (iwe->u.essid.flags && ssid_len > 0 && ssid_len <= IW_ESSID_MAX_SIZE) {
        memcpy(res->ssid, custom, ssid_len);
        res->ssid_len = ssid_len;
    }
}


static PyObject*
parse_scan(char *res_buf, int len, char *ifname, int skfd) {
    char *pos, *end, *custom;
    char *bssid;
    struct iw_event iwe_buf, *iwe = &iwe_buf;
    struct wext_scan_data data;
    struct wpa_scan_results *res;
    int we_version;

    we_version = get_we_version(ifname, skfd);
    if (we_version == -1)
        return NULL;

    res = malloc(sizeof(*res));
    if (res == NULL) {
        free(res_buf);
        return NULL;
    }

    pos = (char *) res_buf;
    end = (char *) res_buf + len;
    memset(&data, 0, sizeof(data));

    while (pos + IW_EV_LCP_LEN <= end) {
        memcpy(&iwe_buf, pos, IW_EV_LCP_LEN);
        if (iwe->len <= IW_EV_LCP_LEN)
            break;

        custom = pos + IW_EV_POINT_LEN;
        if (wext_19_iw_point(iwe->cmd, we_version)) {
            char *dpos = (char *) &iwe_buf.u.data.length;
            int dlen = dpos - (char *) &iwe_buf;
            memcpy(dpos, pos + IW_EV_LCP_LEN,
                  sizeof(struct iw_event) - dlen);
        }
        else {
            memcpy(&iwe_buf, pos, sizeof(struct iw_event));
            custom += IW_EV_POINT_OFF;
        }

        // BSSID (AP mac address) is always supposed to be the first
        // element in the stream.
        if (iwe->cmd == SIOCGIWAP) {
            bssid = convert_macaddr((unsigned char*) &iwe->u.ap_addr.sa_data);
            printf("\n");
            printf("bssid: %s\n", bssid);
        }
        else if (iwe->cmd == SIOCGIWESSID) {
            wext_get_scan_ssid(iwe, &data, custom, end);
            printf("ssid: %s\n", data.ssid);
        }
        else if (iwe->cmd == IWEVQUAL) {
            printf("quality: %i\n", iwe->u.qual.qual);
            printf("level: %i\n", iwe->u.qual.level - 256);
        }

        // go to next
        pos += iwe->len;
    }

    return Py_BuildValue("i", 33);
}


/*
 * Public API.
 */
PyObject*
psutil_wifi_scan(PyObject* self, PyObject* args) {
    int skfd = -1;
    int ret;
    char *ifname;
    struct iwreq wrq;
    char *buffer = NULL;
    char *newbuf;
    int buflen = IW_SCAN_MAX_DATA;
    PyObject *py_ret;

    if (! PyArg_ParseTuple(args, "s", &ifname))
        return NULL;

    // setup iwreq struct
    wrq.u.data.pointer = NULL;
    wrq.u.data.flags = 0;
    wrq.u.data.length = 0;
    strncpy(wrq.ifr_name, ifname, IFNAMSIZ);

    // create socket
    skfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (skfd == -1) {
        PyErr_SetFromOSErrnoWithSyscall("socket()");
        goto error;
    }

    // set scan
    ret = ioctl(skfd, SIOCSIWSCAN, &wrq);
    if (ret == -1) {
        PyErr_SetFromOSErrnoWithSyscall("ioctl(SIOCSIWSCAN)");
        goto error;
    }

    // get scan
    while (1) {
        // (Re)allocate the buffer - realloc(NULL, len) == malloc(len).
        newbuf = realloc(buffer, buflen);
        if (newbuf == NULL) {
            // man says: if realloc() fails the original block is left
            // untouched.
            if (buffer) {
                free(buffer);
                buffer = NULL;
            }
            PyErr_NoMemory();
            goto error;
        }
        buffer = newbuf;

        wrq.u.data.pointer = buffer;
        wrq.u.data.flags = 0;
        wrq.u.data.length = buflen;

        ret = ioctl(skfd, SIOCGIWSCAN, &wrq);
        if (ret < 0) {
            if (errno == E2BIG) {
                // Some driver may return very large scan results, either
                // because there are many cells, or because they have many
                // large elements in cells (like IWEVCUSTOM). Most will
                // only need the regular sized buffer. We now use a dynamic
                // allocation of the buffer to satisfy everybody. Of course,
                // as we don't know in advance the size of the array, we try
                // various increasing sizes. Jean II

                // Check if the driver gave us any hints.
                psutil_debug("ioctl(SIOCGIWSCAN) -> E2BIG");
                if (wrq.u.data.length > buflen)
                    buflen = wrq.u.data.length;
                else
                    buflen *= 2;
                usleep(SCAN_INTERVAL);
                continue;
            }
            else if (errno == EAGAIN) {
                psutil_debug("ioctl(SIOCGIWSCAN) -> EAGAIN");
                usleep(SCAN_INTERVAL);
                continue;
            }
            else {
                PyErr_SetFromOSErrnoWithSyscall("ioctl(SIOCGIWSCAN)");
                goto error;
            }
        }
        break;
    }

    py_ret = parse_scan(buffer, wrq.u.data.length, ifname, skfd);
    close(skfd);
    free(buffer);
    return py_ret;

error:
    if (skfd != -1)
        close(skfd);
    if (buffer != NULL)
        free(buffer);
    return NULL;
}
