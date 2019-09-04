/*
 * Apple System Management Control (SMC) Tool
 * Copyright (C) 2006 devnull 
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.

 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.

 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

#ifndef __SMC_H__
#define __SMC_H__
#endif

#include <IOKit/IOKitLib.h>
#include <stdio.h>
#include <string.h>
#include "specific.h"

#define VERSION "0.01"

#define KERNEL_INDEX_SMC 2

#define SMC_CMD_READ_BYTES 5
#define SMC_CMD_WRITE_BYTES 6
#define SMC_CMD_READ_INDEX 8
#define SMC_CMD_READ_KEYINFO 9
#define SMC_CMD_READ_PLIMIT 11
#define SMC_CMD_READ_VERS 12

#define DATATYPE_FPE2 "fpe2"
#define DATATYPE_UINT8 "ui8 "
#define DATATYPE_UINT16 "ui16"
#define DATATYPE_UINT32 "ui32"
#define DATATYPE_SP78 "sp78"


// key values; all use sp78 datatype
#define SMC_KEY_CPU_TEMP_PROXIMITY_KEY "TC0P"
/* Key names are of the form TCxP, where is the the CPU core, starting from 1 */
#define SMC_KEY_CPU_TEMP_CORE_PREFIX "TC"
#define SMC_KEY_CPU_TEMP_CORE_POSTFIX "C"

typedef struct {
    char major;
    char minor;
    char build;
    char reserved[1];
    UInt16 release;
} SMCKeyData_vers_t;

typedef struct {
    UInt16 version;
    UInt16 length;
    UInt32 cpuPLimit;
    UInt32 gpuPLimit;
    UInt32 memPLimit;
} SMCKeyData_pLimitData_t;

typedef struct {
    UInt32 dataSize;
    UInt32 dataType;
    char dataAttributes;
} SMCKeyData_keyInfo_t;

typedef char SMCBytes_t[32];

typedef struct {
    UInt32 key;
    SMCKeyData_vers_t vers;
    SMCKeyData_pLimitData_t pLimitData;
    SMCKeyData_keyInfo_t keyInfo;
    char result;
    char status;
    char data8;
    UInt32 data32;
    SMCBytes_t bytes;
} SMCKeyData_t;

typedef char UInt32Char_t[5];

typedef struct {
    UInt32Char_t key;
    UInt32 dataSize;
    UInt32Char_t dataType;
    SMCBytes_t bytes;
} SMCVal_t;


static io_connect_t conn;

UInt32 _strtoul(char* str, int size, int base)
{
    UInt32 total = 0;
    int i;

    for (i = 0; i < size; i++) {
        if (base == 16)
            total += str[i] << (size - 1 - i) * 8;
        else
            total += (unsigned char)(str[i] << (size - 1 - i) * 8);
    }
    return total;
}

void _ultostr(char* str, UInt32 val)
{
    str[0] = '\0';
    sprintf(str, "%c%c%c%c",
        (unsigned int)val >> 24,
        (unsigned int)val >> 16,
        (unsigned int)val >> 8,
        (unsigned int)val);
}

kern_return_t SMCOpen(void)
{
    kern_return_t result;
    io_iterator_t iterator;
    io_object_t device;

    CFMutableDictionaryRef matchingDictionary = IOServiceMatching("AppleSMC");
    result = IOServiceGetMatchingServices(kIOMasterPortDefault, matchingDictionary, &iterator);
    if (result != kIOReturnSuccess) {
        printf("Error: IOServiceGetMatchingServices() = %08x\n", result);
        return 1;
    }

    device = IOIteratorNext(iterator);
    IOObjectRelease(iterator);
    if (device == 0) {
        printf("Error: no SMC found\n");
        return 1;
    }

    result = IOServiceOpen(device, mach_task_self(), 0, &conn);
    IOObjectRelease(device);
    if (result != kIOReturnSuccess) {
        printf("Error: IOServiceOpen() = %08x\n", result);
        return 1;
    }

    return kIOReturnSuccess;
}

kern_return_t SMCClose()
{
    return IOServiceClose(conn);
}

kern_return_t SMCCall(int index, SMCKeyData_t* inputStructure, SMCKeyData_t* outputStructure)
{
    size_t structureInputSize;
    size_t structureOutputSize;

    structureInputSize = sizeof(SMCKeyData_t);
    structureOutputSize = sizeof(SMCKeyData_t);

#if MAC_OS_X_VERSION_10_5
    return IOConnectCallStructMethod(conn, index,
        // inputStructure
        inputStructure, structureInputSize,
        // ouputStructure
        outputStructure, &structureOutputSize);
#else
    return IOConnectMethodStructureIStructureO(conn, index,
        structureInputSize, /* structureInputSize */
        &structureOutputSize, /* structureOutputSize */
        inputStructure, /* inputStructure */
        outputStructure); /* ouputStructure */
#endif
}

kern_return_t SMCReadKey(UInt32Char_t key, SMCVal_t* val)
{
    kern_return_t result;
    SMCKeyData_t inputStructure;
    SMCKeyData_t outputStructure;

    memset(&inputStructure, 0, sizeof(SMCKeyData_t));
    memset(&outputStructure, 0, sizeof(SMCKeyData_t));
    memset(val, 0, sizeof(SMCVal_t));

    inputStructure.key = _strtoul(key, 4, 16);
    inputStructure.data8 = SMC_CMD_READ_KEYINFO;

    result = SMCCall(KERNEL_INDEX_SMC, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess)
        return result;

    val->dataSize = outputStructure.keyInfo.dataSize;
    _ultostr(val->dataType, outputStructure.keyInfo.dataType);
    inputStructure.keyInfo.dataSize = val->dataSize;
    inputStructure.data8 = SMC_CMD_READ_BYTES;

    result = SMCCall(KERNEL_INDEX_SMC, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess)
        return result;

    memcpy(val->bytes, outputStructure.bytes, sizeof(outputStructure.bytes));

    return kIOReturnSuccess;
}

/* Extension for psutil */
/* Read temp for each core, as well as ancillaries */

#define SP78_TO_DOUBLE(x) ((double)(((int)((x)[0]) << 8) + ((int)(x)[1]))/256.0)

PyObject* psutil_sensors_cpu_temperature(PyObject* self, PyObject* args){
    /* Should be large enough. Will allow for 96 digits of CPU count, which is highly unlikely */
    #define CORE_KEY_STR_LEN 100
    char core_key[CORE_KEY_STR_LEN] = {0};
    int count = 0, index = 0;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    SMCVal_t val;

    if (py_retlist == NULL)
        return NULL;

    SMCOpen();

    if (SMCReadKey(SMC_KEY_CPU_TEMP_PROXIMITY_KEY, &val) != kIOReturnSuccess){
        return NULL;
    }

    double cpu_prox = SP78_TO_DOUBLE(val.bytes);
    /* Proximity CPU sensor seems to always exists */

    py_tuple = Py_BuildValue("sd", "Proximity", cpu_prox);
    if (py_tuple == NULL){
        goto error_label;
    }
    if (PyList_Append(py_retlist, py_tuple) != 0){
        goto error_label;
    }
    /* Free memory alloced for tuple originally */
    Py_XDECREF(py_tuple);


    /* Sometimes OS X reports CPU cores starting from index 0 (seen on MacBook Pro), and other times from 1 (seen on Mac Mini) */
    /* A solution is to try to read value 0, and if it does not exist, try index 1 */
    /* Traverse the sensors, starting from core 0, till there is nothing to read */
    /* Even when the core reporting starts from index 1, report as Core 0 to be consistent with Linux reporting */
    while (1){
        double core_temp = 0.0;
        char core_str[CORE_KEY_STR_LEN] = {0};

        /* Key names are of the form TCxC, where x is the the CPU core, starting from 0 or 1 */
        int res = snprintf(core_key, CORE_KEY_STR_LEN, "%s%d%s",
                    SMC_KEY_CPU_TEMP_CORE_PREFIX, count, SMC_KEY_CPU_TEMP_CORE_POSTFIX);

        if ( (res < 0) || (res >= CORE_KEY_STR_LEN)){
            /* Somehow you have a ton of CPUs... */
            break;
        }

        if ((SMCReadKey(core_key, &val) != kIOReturnSuccess) || (val.dataSize <= 0)){
            /* Could not read for index 0. Index reporting probably starts at 1 */
            if (count == 0){
                count++;
                continue;
            }
            /* No more cores to read */
            break;
        }

        core_temp = SP78_TO_DOUBLE(val.bytes);
        

        res = snprintf(core_str, CORE_KEY_STR_LEN, "Core %d", index);
        if ( (res < 0) || (res >= CORE_KEY_STR_LEN)){
            /* Somehow you have a ton of CPUs... */
            break;
        }

        /* Build a tuple with result */
        py_tuple = Py_BuildValue("sd", core_str, core_temp);
        if (py_tuple == NULL){
            goto error_label;
        }
        if (PyList_Append(py_retlist, py_tuple) != 0){
            goto error_label;
        }

        count++;
        index++;
        /* Free memory alloced for tuple originally */
        Py_XDECREF(py_tuple);
    }
    SMCClose();
    return py_retlist;

    /* Cleanup */
    error_label:
        SMCClose();
        Py_XDECREF(py_tuple);
        Py_XDECREF(py_retlist);
        return NULL;
}
