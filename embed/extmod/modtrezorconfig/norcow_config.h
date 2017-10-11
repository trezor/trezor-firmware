#if defined TREZOR_STM32

#define NORCOW_STM32 1

#define NORCOW_SECTORS   {4, 16}
#define NORCOW_ADDRESSES {0x08010000, 0x08110000}

#elif defined TREZOR_UNIX

#define NORCOW_UNIX 1

#define NORCOW_FILE "/var/tmp/trezor.config"

#else

#error Unsupported TREZOR port. Only STM32 and UNIX ports are supported.

#endif
