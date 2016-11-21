#ifdef UNIX
#define NORCOW_UNIX 1
#define NORCOW_FILE "/var/tmp/trezor.config"
#endif

#ifdef STM32_HAL_H
// TODO: switch to native implementation when finished
#define NORCOW_UNIX 1
#define NORCOW_FILE "/sd/trezor.config"
#endif
