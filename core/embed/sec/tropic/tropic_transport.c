/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <sec/secret.h>
#include <sec/tropic_transport.h>
#include <trezor_rtl.h>
#include <trezor_types.h>
#include "ed25519-donna/ed25519.h"
#include "libtropic.h"
#include "memzero.h"

#define PKEY_INDEX_BYTE PAIRING_KEY_SLOT_INDEX_0

STATIC lt_handle_t lt_handle = {0};

void tropic_init(void) {
  uint8_t tropic_secret_tropic_pubkey[SECRET_TROPIC_KEY_LEN] = {0};
  uint8_t tropic_secret_trezor_privkey[SECRET_TROPIC_KEY_LEN] = {0};

  ensure((lt_init(&lt_handle) == LT_OK) * sectrue, "lt_init failed");

  ensure(secret_tropic_get_tropic_pubkey(tropic_secret_tropic_pubkey),
         "secret_tropic_get_tropic_pubkey failed");
  ensure(secret_tropic_get_trezor_privkey(tropic_secret_trezor_privkey),
         "secret_tropic_get_trezor_privkey failed");

  uint8_t trezor_pubkey[SECRET_TROPIC_KEY_LEN] = {};
  curve25519_scalarmult_basepoint(trezor_pubkey, tropic_secret_trezor_privkey);

  lt_ret_t ret = LT_FAIL;
  ret =
      lt_session_start(&lt_handle, tropic_secret_tropic_pubkey, PKEY_INDEX_BYTE,
                       tropic_secret_trezor_privkey, trezor_pubkey);
  memzero(tropic_secret_trezor_privkey, sizeof(tropic_secret_trezor_privkey));

  ensure((ret == LT_OK) * sectrue, "lt_session_start failed");
}
