/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdint.h>
#include <stddef.h>
#include "secbool.h"
#include "py/obj.h"

void storage_init(void);
void storage_wipe(void);
secbool storage_unlock(const uint32_t pin, mp_obj_t callback);
secbool storage_has_pin(void);
uint32_t storage_pin_wait_time(void);
secbool storage_change_pin(const uint32_t pin, const uint32_t newpin, mp_obj_t callback);
secbool storage_get(uint16_t key, const void **val, uint16_t *len);
secbool storage_set(uint16_t key, const void *val, uint16_t len);
