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

int count_cpu_cores();
int count_physical_cpus();
int count_gpus();
int count_dimms();
bool temperature_reasonable(double d);
bool fan_speed_reasonable(double d);
bool always_true(double d);

const struct smc_sensor {
    // Actual types are varied, but they can all be contained in this less efficient format
    const char key[5];
    const char name[];
    double (*get_function)(char *);
    bool (*reasonable_function)(double);
};

const struct potential_smc_sensors {
    static const struct smc_sensor sensors[];
    static const bool multiple_support;
    static const bool use_counting_function;
    // We'll either use a predefined counting function or trial and error
    static const int (*count_function_pointer)(void);
};

const struct potential_smc_sensors temperature_sensors[] = {
    {
        {
            {"TA0P", "Ambient", &SMCGetTemperature, &temperature_reasonable},
            {"TA0S", "PCI Slot 1 Pos 1", &SMCGetTemperature, &temperature_reasonable},
            {"TA1P", "Ambient temperature", &SMCGetTemperature, &temperature_reasonable},
            {"TA1S", "PCI Slot 1 Pos 2", &SMCGetTemperature, &temperature_reasonable},
            {"TA2S", "PCI Slot 2 Pos 1", &SMCGetTemperature, &temperature_reasonable},
            {"TA3S", "PCI Slot 2 Pos 2", &SMCGetTemperature, &temperature_reasonable},
            {"TB0P", "BLC Proximity", &SMCGetTemperature, &temperature_reasonable},
            {"TB0T", "Battery TS_MAX", &SMCGetTemperature, &temperature_reasonable},
            {"TB1T", "Battery 1", &SMCGetTemperature, &temperature_reasonable},
            {"TB2T", "Battery 2", &SMCGetTemperature, &temperature_reasonable},
            {"TB3T", "Battery 3", &SMCGetTemperature, &temperature_reasonable},
            {"TCGC", "PECI GPU", &SMCGetTemperature, &temperature_reasonable},
            {"TCSA", "PECI SA", &SMCGetTemperature, &temperature_reasonable},
            {"TCSC", "PECI SA", &SMCGetTemperature, &temperature_reasonable},
            {"TCXC", "PECI CPU", &SMCGetTemperature, &temperature_reasonable},
            // For these values: appears that the hardware can only support one, but the SMC keys seem to indicate
            // support for multiple
            {"TN0D", "Northbridge Die", &SMCGetTemperature, &temperature_reasonable},
            {"TN0H", "Northbridge Heatsink", &SMCGetTemperature, &temperature_reasonable},
            {"TN0P", "Northbridge Proximity", &SMCGetTemperature, &temperature_reasonable},
            {"TS0C", "Expansion Slots", &SMCGetTemperature, &temperature_reasonable},
            {"TS0S", "Memory Bank Proximity", &SMCGetTemperature, &temperature_reasonable},
            {"TW0P", "AirPort Proximity", &SMCGetTemperature, &temperature_reasonable}
        }, false, false
    },
    {
        {
            {"TC_C", "CPU Core _", &SMCGetTemperature, &temperature_reasonable},
        }, true, true, &count_cpu_cores
    },
    {
        {
            {"TC_D", "CPU _ Die", &SMCGetTemperature, &temperature_reasonable},
            {"TC_E", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable},
            {"TC_F", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable},
            {"TC_G", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable},
            {"TC_H", "CPU _ Heatsink", &SMCGetTemperature, &temperature_reasonable},
            {"TC_J", "CPU _ ??", &SMCGetTemperature, &temperature_reasonable},
            {"TC_P", "CPU _ Proximity", &SMCGetTemperature, &temperature_reasonable},
        }, true, true, &count_physical_cpus
    },
    {
        {
            {"TG_D", "GPU _ Die", &SMCGetTemperature, &temperature_reasonable},
            {"TG_H", "GPU _ Heatsink", &SMCGetTemperature, &temperature_reasonable},
            {"TG_P", "GPU _ Proximity", &SMCGetTemperature, &temperature_reasonable},
        }, true, true, &count_gpus
    },
    {
        {
            {"TH_H", "Heatsink _ Proximity", &SMCGetTemperature, &temperature_reasonable}
        }, true, false
    },
    {
        {
            {"TH_P", "HDD _ Proximity", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TI_P", "Thunderbolt _", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TL_P", "LCD _ Proximity", &SMCGetTemperature, &temperature_reasonable},
            {"TL_P", "LCD _", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TM_P", "Memory _ Proximity", &SMCGetTemperature, &temperature_reasonable},
            {"TM_S", "Memory Slot _", &SMCGetTemperature, &temperature_reasonable},
            {"TMA_", "DIMM A _", &SMCGetTemperature, &temperature_reasonable},
            {"TMB_", "DIMM B _", &SMCGetTemperature, &temperature_reasonable},
        }, true, true, &count_dimms
    },
    {
        {
            {"TO_P", "Optical Drive _ Proximity", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TP_C", "Power Supply _", &SMCGetTemperature, &temperature_reasonable},
            {"TP_P", "Power Supply _ Proximity", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TS_C", "Expansion Slot _", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    },
    {
        {
            {"TS_P", "Palm Rest _", &SMCGetTemperature, &temperature_reasonable},
        }, true, false
    }
};

const struct potential_smc_sensors fan_sensors[] = {
    // TODO
};

const struct potential_smc_sensors other_sensors[] = {
    // TODO
};

#endif
