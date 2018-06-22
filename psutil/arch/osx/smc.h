#ifndef __SMC_H__
#define __SMC_H__

#define KERNEL_INDEX_SMC      2

#define SMC_CMD_READ_BYTES    5
#define SMC_CMD_WRITE_BYTES   6
#define SMC_CMD_READ_INDEX    8
#define SMC_CMD_READ_KEYINFO  9
#define SMC_CMD_READ_PLIMIT   11
#define SMC_CMD_READ_VERS     12

#define DATATYPE_FPE2         "fpe2"
#define DATATYPE_UINT8        "ui8 "
#define DATATYPE_UINT16       "ui16"
#define DATATYPE_UINT32       "ui32"
#define DATATYPE_SP78         "sp78"

#define MIN_TEMP              0
#define MAX_TEMP              200

// key values
#define SMC_KEY_CPU_TEMP      "TC0F"
#define SMC_KEY_CPU_TEMP_HIGH "TC0G"
#define SMC_KEY_BATTERY_TEMP  "TB0T"
#define SMC_KEY_FAN_NUM       "FNum"
#define SMC_KEY_FAN_SPEED     "F%dAb"

typedef struct {
    char                  major;
    char                  minor;
    char                  build;
    char                  reserved[1];
    UInt16                release;
} SMCKeyData_vers_t;

typedef struct {
    UInt16                version;
    UInt16                length;
    UInt32                cpuPLimit;
    UInt32                gpuPLimit;
    UInt32                memPLimit;
} SMCKeyData_pLimitData_t;

typedef struct {
    UInt32                dataSize;
    UInt32                dataType;
    char                  dataAttributes;
} SMCKeyData_keyInfo_t;

typedef char              SMCBytes_t[32];

typedef struct {
  UInt32                  key;
  SMCKeyData_vers_t       vers;
  SMCKeyData_pLimitData_t pLimitData;
  SMCKeyData_keyInfo_t    keyInfo;
  char                    result;
  char                    status;
  char                    data8;
  UInt32                  data32;
  SMCBytes_t              bytes;
} SMCKeyData_t;

typedef char              UInt32Char_t[5];

typedef struct {
  UInt32Char_t            key;
  UInt32                  dataSize;
  UInt32Char_t            dataType;
  SMCBytes_t              bytes;
} SMCVal_t;

double SMCGetTemperature(char *key);
int SMCGetFanNumber(char *key);
float SMCGetFanSpeed(int fanNum);

int count_cpu_cores() {
    // TODO
    return 1;
}
int count_physical_cpus() {
    // TODO
    return 1;
}
int count_gpus() {
    // TODO
    return 1;
}
int count_dimms() {
    // TODO
    return 2;
}
bool temperature_reasonable(double d) {
    // TODO
    return d > 10;
}
bool fan_speed_reasonable(double d) {
    // TODO
    return d > 100;
}
bool always_true(double d) {
    return true;
}

struct smc_sensor {
    // Actual types are varied, but they can all be contained in this less efficient format
    const char key[5];
    const char * name;
    double (*get_function)(char *);
    bool (*reasonable_function)(double);
    int (*count_function_pointer)();
};

const struct smc_sensor temperature_sensors[] = {
    {"TA0P", "Ambient", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TA0S", "PCI Slot 1 Pos 1", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TA1P", "Ambient temperature", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TA1S", "PCI Slot 1 Pos 2", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TA2S", "PCI Slot 2 Pos 1", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TA3S", "PCI Slot 2 Pos 2", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TB0P", "BLC Proximity", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TB0T", "Battery TS_MAX", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TB1T", "Battery 1", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TB2T", "Battery 2", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TB3T", "Battery 3", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TCGC", "PECI GPU", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TCSA", "PECI SA", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TCSC", "PECI SA", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TCXC", "PECI CPU", &SMCGetTemperature, &temperature_reasonable, NULL},
    // For these values: appears that the hardware can only support one, but the SMC keys seem to indicate
    // support for multiple
    {"TN0D", "Northbridge Die", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TN0H", "Northbridge Heatsink", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TN0P", "Northbridge Proximity", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TS0C", "Expansion Slots", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TS0S", "Memory Bank Proximity", &SMCGetTemperature, &temperature_reasonable, NULL},
    {"TW0P", "AirPort Proximity", &SMCGetTemperature, &temperature_reasonable, NULL},

    {"TC_C", "CPU Core _", &SMCGetTemperature, &temperature_reasonable, &count_cpu_cores},

    {"TC_D", "CPU _ Die", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_E", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_F", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_G", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_H", "CPU _ Heatsink", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_J", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},
    {"TC_P", "CPU _ Proximity", &SMCGetTemperature, &temperature_reasonable, &count_physical_cpus},

    {"TG_D", "GPU _ Die", &SMCGetTemperature, &temperature_reasonable, &count_gpus},
    {"TG_H", "GPU _ Heatsink", &SMCGetTemperature, &temperature_reasonable, &count_gpus},
    {"TG_P", "GPU _ Proximity", &SMCGetTemperature, &temperature_reasonable, &count_gpus},

    {"TH_H", "Heatsink _ Proximity", &SMCGetTemperature, &temperature_reasonable},
    {"TH_P", "HDD _ Proximity", &SMCGetTemperature, &temperature_reasonable},
    {"TI_P", "Thunderbolt _", &SMCGetTemperature, &temperature_reasonable},
    {"TL_P", "LCD _ Proximity", &SMCGetTemperature, &temperature_reasonable},
    {"TL_P", "LCD _", &SMCGetTemperature, &temperature_reasonable},

    {"TM_P", "Memory _ Proximity", &SMCGetTemperature, &temperature_reasonable, &count_dimms},
    {"TM_S", "Memory Slot _", &SMCGetTemperature, &temperature_reasonable, &count_dimms},
    {"TMA_", "DIMM A _", &SMCGetTemperature, &temperature_reasonable, &count_dimms},
    {"TMB_", "DIMM B _", &SMCGetTemperature, &temperature_reasonable, &count_dimms},

    {"TO_P", "Optical Drive _ Proximity", &SMCGetTemperature, &temperature_reasonable},
    {"TP_C", "Power Supply _", &SMCGetTemperature, &temperature_reasonable},
    {"TP_P", "Power Supply _ Proximity", &SMCGetTemperature, &temperature_reasonable},
    {"TS_C", "Expansion Slot _", &SMCGetTemperature, &temperature_reasonable},
    {"TS_P", "Palm Rest _", &SMCGetTemperature, &temperature_reasonable}
};

const struct smc_sensor fan_sensors[] = {
    // TODO
};

const struct smc_sensor other_sensors[] = {
    // TODO
};

#endif
