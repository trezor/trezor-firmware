
#include <stdint.h>
#include "secbool.h"

#define SECRET_HEADER_MAGIC "TRZS"
#define SECRET_HEADER_LEN 16
#define SECRET_OPTIGA_KEY_OFFSET 16
#define SECRET_OPTIGA_KEY_LEN 32

#define SECRET_MONOTONIC_COUNTER_OFFSET 48
#define SECRET_MONOTONIC_COUNTER_LEN 1024

#define SECRET_BHK_OFFSET (1024 * 8)
#define SECRET_BHK_LEN 32

secbool secret_bootloader_locked(void);

void secret_write(uint8_t* data, uint32_t offset, uint32_t len);

secbool secret_read(uint8_t* data, uint32_t offset, uint32_t len);

secbool secret_wiped(void);

void secret_erase(void);

void secret_hide(void);

void secret_write_header(void);

void secret_optiga_backup(void);

void secret_optiga_hide(void);

secbool secret_optiga_extract(uint8_t* dest);

void secret_bhk_lock(void);

secbool secret_bhk_locked(void);

void secret_bhk_regenerate(void);

void secret_bhk_provision(void);

secbool secret_optiga_present(void);
