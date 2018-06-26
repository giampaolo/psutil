/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Interface to SMC API, needed in order to collect sensors stats.
 */

#include <stdio.h>
#include <string.h>
#include <IOKit/IOKitLib.h>

#include "smc.h"

UInt32 _strtoul(char *str, int size, int base)
{
    UInt32 total = 0;
    int i;

    for (i = 0; i < size; i++) {
        if (base == 16)
            total += str[i] << (size - 1 - i) * 8;
        else
            total += (unsigned char) (str[i] << (size - 1 - i) * 8);
    }
    return total;
}


float _strtof(unsigned char *str, int size, int e)
{
    float total = 0;
    int i;

    for (i = 0; i < size; i++) {
        if (i == (size - 1))
            total += (str[i] & 0xff) >> e;
        else
            total += str[i] << (size - 1 - i) * (8 - e);
    }

    total += (str[size-1] & 0x03) * 0.25;

    return total;
}


void _ultostr(char *str, UInt32 val)
{
    str[0] = '\0';
    sprintf(str, "%c%c%c%c",
        (unsigned int) val >> 24,
        (unsigned int) val >> 16,
        (unsigned int) val >> 8,
        (unsigned int) val);
}


kern_return_t SMCOpen(io_connect_t * pconn)
{
    kern_return_t result;
    io_iterator_t iterator;
    io_object_t   device;

    CFMutableDictionaryRef matchingDictionary = IOServiceMatching("AppleSMC");
    result = IOServiceGetMatchingServices(
        kIOMasterPortDefault,
        matchingDictionary,
        &iterator
    );
    if (result != kIOReturnSuccess) {
        return 1;
    }

    device = IOIteratorNext(iterator);
    IOObjectRelease(iterator);
    if (device == 0) {
        return 1;
    }

    result = IOServiceOpen(device, mach_task_self(), 0, pconn);
    IOObjectRelease(device);
    if (result != kIOReturnSuccess) {
        return 1;
    }

    return kIOReturnSuccess;
}


kern_return_t SMCClose(io_connect_t conn)
{
    return IOServiceClose(conn);
}


kern_return_t SMCCall(io_connect_t conn,
    int index, SMCKeyData_t *inputStructure, SMCKeyData_t *outputStructure)
{
    size_t   structureInputSize;
    size_t   structureOutputSize;

    structureInputSize = sizeof(SMCKeyData_t);
    structureOutputSize = sizeof(SMCKeyData_t);

#if MAC_OS_X_VERSION_10_5
    return IOConnectCallStructMethod(
        conn,
        index,
        inputStructure,
        structureInputSize,
        outputStructure,
        &structureOutputSize);
#else
    return IOConnectMethodStructureIStructureO(
        conn,
        index,
        structureInputSize,
        &structureOutputSize,
        inputStructure,
        outputStructure);
#endif
}


kern_return_t SMCReadKey(io_connect_t conn, UInt32Char_t key, SMCVal_t *val) {
    kern_return_t result;
    SMCKeyData_t  inputStructure;
    SMCKeyData_t  outputStructure;

    memset(&inputStructure, 0, sizeof(SMCKeyData_t));
    memset(&outputStructure, 0, sizeof(SMCKeyData_t));
    memset(val, 0, sizeof(SMCVal_t));

    inputStructure.key = _strtoul(key, 4, 16);
    inputStructure.data8 = SMC_CMD_READ_KEYINFO;

    result = SMCCall(
        conn,
        KERNEL_INDEX_SMC,
        &inputStructure,
        &outputStructure
    );
    if (result != kIOReturnSuccess)
        return result;

    val->dataSize = outputStructure.keyInfo.dataSize;
    _ultostr(val->dataType, outputStructure.keyInfo.dataType);
    inputStructure.keyInfo.dataSize = val->dataSize;
    inputStructure.data8 = SMC_CMD_READ_BYTES;

    result = SMCCall(
        conn,
        KERNEL_INDEX_SMC,
        &inputStructure,
        &outputStructure
    );
    if (result != kIOReturnSuccess)
        return result;

    memcpy(val->bytes, outputStructure.bytes, sizeof(outputStructure.bytes));

    return kIOReturnSuccess;
}


double SMCGetTemperature(char *key) {
    io_connect_t conn;
    SMCVal_t val;
    kern_return_t result;
    int intValue;

    result = SMCOpen(&conn);
    if (result != kIOReturnSuccess) {
        return 0.0;
    }

    result = SMCReadKey(conn, key, &val);
    if (result == kIOReturnSuccess) {
        // read succeeded - check returned value
        if (val.dataSize > 0) {
            if (strcmp(val.dataType, DATATYPE_SP78) == 0) {
                // convert sp78 value to temperature
                intValue = val.bytes[0] * 256 + (unsigned char)val.bytes[1];
                SMCClose(conn);
                return intValue / 256.0;
            }
        }
    }
    // read failed
    SMCClose(conn);
    return 0.0;
}


float SMCGetFanSpeed(int fanNum)
{
    SMCVal_t val;
    kern_return_t result;
    UInt32Char_t  key;
    io_connect_t conn;

    result = SMCOpen(&conn);
    if (result != kIOReturnSuccess) {
        return -1;
    }

    sprintf(key, SMC_KEY_FAN_SPEED, fanNum);
    result = SMCReadKey(conn, key, &val);
     if (result != kIOReturnSuccess) {
        SMCClose(conn);
        return -1;
    }
    SMCClose(conn);
    return _strtof((unsigned char *)val.bytes, val.dataSize, 2);
}



int SMCGetFanNumber(char *key)
{
    SMCVal_t val;
    kern_return_t result;
    io_connect_t conn;

    result = SMCOpen(&conn);
    if (result != kIOReturnSuccess) {
        return 0;
    }

    result = SMCReadKey(conn, key, &val);
     if (result != kIOReturnSuccess) {
        SMCClose(conn);
        return 0;
    }
    SMCClose(conn);
    return _strtoul((char *)val.bytes, val.dataSize, 10);
}
