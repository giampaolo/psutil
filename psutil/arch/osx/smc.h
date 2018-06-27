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

struct smc_sensor {
    // Actual types are varied, but they can all be contained in this less efficient format
    const char key[5];
    const char * name;
    double (*get_function)(char *);
    bool (*reasonable_function)(double);
    int (*count_function_pointer)();
};

#endif
