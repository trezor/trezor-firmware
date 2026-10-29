/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "py/obj.h"
#define THP_VAULT_KEY_SIZE 256
bool trezorcrypto_thp_prepare(mp_obj_t seed, uint8_t key[THP_VAULT_KEY_SIZE],
                              uint8_t public_key[32]);
bool trezorcrypto_thp_dh(const uint8_t key[THP_VAULT_KEY_SIZE],
                         const uint8_t peer[32], uint8_t output[32]);
