/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdint.h>
#include <stddef.h>

bool storage_init(void);
bool storage_wipe(void);
bool storage_unlock(const uint8_t *pin, size_t len);
bool storage_get(uint16_t key, const void **val, uint16_t *len);
bool storage_set(uint16_t key, const void *val, uint16_t len);
