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

const struct smc_sensor {
    // Actual types are varied, but they can all be contained in this less efficient format
    const char key[5];
    const char name[];
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
            {"TA0P", "Ambient"},
            {"TA0S", "PCI Slot 1 Pos 1"},
            {"TA1P", "Ambient temperature"},
            {"TA1S", "PCI Slot 1 Pos 2"},
            {"TA2S", "PCI Slot 2 Pos 1"},
            {"TA3S", "PCI Slot 2 Pos 2"},
            {"TB0P", "BLC Proximity"},
            {"TB0T", "Battery TS_MAX"},
            {"TB1T", "Battery 1"},
            {"TB2T", "Battery 2"},
            {"TB3T", "Battery 3"},
            {"TCGC", "PECI GPU"},
            {"TCSA", "PECI SA"},
            {"TCSC", "PECI SA"},
            {"TCXC", "PECI CPU"},
            // For these values: appears that the hardware can only support one, but the SMC keys seem to indicate
            // support for multiple
            {"TN0D", "Northbridge Die"},
            {"TN0H", "Northbridge Heatsink"},
            {"TN0P", "Northbridge Proximity"},
            {"TS0C", "Expansion Slots"},
            {"TS0S", "Memory Bank Proximity"},
            {"TW0P", "AirPort Proximity"}
        }, false, false
    },
    {
        {
            {"TC_C", "CPU Core _"},
        }, true, true, &count_cpu_cores
    },
    {
        {
            {"TC_D", "CPU _ Die"},
            {"TC_E", "CPU _ ??"},
            {"TC_F", "CPU _ ??"},
            {"TC_G", "CPU _ ??"},
            {"TC_H", "CPU _ Heatsink"},
            {"TC_J", "CPU _ ??"},
            {"TC_P", "CPU _ Proximity"},
        }, true, true, &count_physical_cpus
    },
    {
        {
            {"TG_D", "GPU _ Die"},
            {"TG_H", "GPU _ Heatsink"},
            {"TG_P", "GPU _ Proximity"},
        }, true, true, &count_gpus
    },
    {
        {
            {"TH_H", "Heatsink _ Proximity"}
        }, true, false
    },
    {
        {
            {"TH_P", "HDD _ Proximity"},
        }, true, false
    },
    {
        {
            {"TI_P", "Thunderbolt _"},
        }, true, false
    },
    {
        {
            {"TL_P", "LCD _ Proximity"},
            {"TL_P", "LCD _"},
        }, true, false
    },
    {
        {
            {"TM_P", "Memory _ Proximity"},
            {"TM_S", "Memory Slot _"},
            {"TMA_", "DIMM A _"},
            {"TMB_", "DIMM B _"},
        }, true, true, &count_dimms
    },
    {
        {
            {"TO_P", "Optical Drive _ Proximity"},
        }, true, // ?
    },
    {
        {
            {"TP_C", "Power Supply _"},
            {"TP_P", "Power Supply _ Proximity"},
        }, true, // ?
    },
    {
        {
            {"TS_C", "Expansion Slot _"},
        }, true, // ?
    },
    {
        {
            {"TS_P", "Palm Rest _"},
        }, true, // ?
    }
};

const struct potential_smc_sensors fan_sensors[] = {

};

const struct potential_smc_sensors other_sensors[] = {
    // This includes ambient sensors
};

#endif
