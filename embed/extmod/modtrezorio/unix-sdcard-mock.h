/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "../../trezorhal/sdcard.h"

void sdcard_init(void) {
}

secbool sdcard_is_present(void) {
    return secfalse;
}

secbool sdcard_power_on(void) {
    return secfalse;
}

secbool sdcard_power_off(void) {
    return sectrue;
}

uint64_t sdcard_get_capacity_in_bytes(void) {
    return 0;
}

secbool sdcard_read_blocks(void *dest, uint32_t block_num, uint32_t num_blocks) {
   return secfalse;
}

secbool sdcard_write_blocks(const void *src, uint32_t block_num, uint32_t num_blocks) {
   return secfalse;
}
