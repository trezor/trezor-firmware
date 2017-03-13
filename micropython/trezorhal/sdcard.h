#ifndef __TREZORHAL_SDCARD_H__
#define __TREZORHAL_SDCARD_H__

#include <stdbool.h>

// this is a fixed size and should not be changed
#define SDCARD_BLOCK_SIZE (512)

int sdcard_init(void);
bool sdcard_is_present(void);
bool sdcard_power_on(void);
void sdcard_power_off(void);
uint64_t sdcard_get_capacity_in_bytes(void);
uint32_t sdcard_read_blocks(void *dest, uint32_t block_num, uint32_t num_blocks);
uint32_t sdcard_write_blocks(const void *src, uint32_t block_num, uint32_t num_blocks);

#endif
