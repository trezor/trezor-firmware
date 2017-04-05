#ifdef UNIX
#define NORCOW_UNIX 1
#define NORCOW_FILE "/var/tmp/trezor.config"
#endif

#ifdef STM32_HAL_H
#define NORCOW_STM32 1
#define NORCOW_START_SECTOR 2
#define NORCOW_START_ADDRESS 0x08008000
#endif
