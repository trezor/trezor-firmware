/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdint.h>
#include <stddef.h>
#include "../../trezorhal/secbool.h"

secbool storage_init(void);
secbool storage_wipe(void);
secbool storage_unlock(const uint8_t *pin, size_t len);
secbool storage_has_pin(void);
secbool storage_change_pin(const uint8_t *pin, size_t len, const uint8_t *newpin, size_t newlen);
secbool storage_get(uint16_t key, const void **val, uint16_t *len);
secbool storage_set(uint16_t key, const void *val, uint16_t len);
