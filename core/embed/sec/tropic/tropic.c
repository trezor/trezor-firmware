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

#ifdef SECURE_MODE

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <sec/secret_keys.h>
#include <sec/tropic.h>

#include <libtropic.h>

#ifdef TREZOR_EMULATOR
#include <arpa/inet.h>
#include <libtropic/hal/port/unix/lt_port_unix_tcp.h>
#include <time.h>
#endif

#include "ed25519-donna/ed25519.h"
#include "memzero.h"

#define PKEY_INDEX_BYTE PAIRING_KEY_SLOT_INDEX_0

typedef struct {
  bool initialized;
  bool sec_chan_established;
  lt_handle_t handle;
#ifdef TREZOR_EMULATOR
  lt_dev_unix_tcp_t device;
#endif
} tropic_driver_t;

static tropic_driver_t g_tropic_driver = {0};

bool tropic_init(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (drv->initialized) {
    return true;
  }

#ifdef TREZOR_EMULATOR
  drv->device.addr = inet_addr("127.0.0.1");
  drv->device.port = 28992;
  drv->handle.l2.device = &drv->device;
#endif

  if (lt_init(&drv->handle) != LT_OK) {
    goto cleanup;
  }

  curve25519_key tropic_pubkey = {0};
  curve25519_key trezor_privkey = {0};

  secbool pubkey_ok = secret_key_tropic_public(tropic_pubkey);
  secbool privkey_ok = secret_key_tropic_pairing_privileged(trezor_privkey);

  if (pubkey_ok == sectrue && privkey_ok == sectrue) {
    curve25519_key trezor_pubkey = {0};
    curve25519_scalarmult_basepoint(trezor_pubkey, trezor_privkey);

    lt_ret_t ret =
        lt_session_start(&drv->handle, tropic_pubkey, PKEY_INDEX_BYTE,
                         trezor_privkey, trezor_pubkey);

    drv->sec_chan_established = (ret == LT_OK);
  }

  memzero(trezor_privkey, sizeof(trezor_privkey));

  drv->initialized = true;

  return true;

cleanup:
  tropic_deinit();
  return false;
}

void tropic_deinit(void) {
  tropic_driver_t *drv = &g_tropic_driver;
  lt_deinit(&drv->handle);
  memset(drv, 0, sizeof(*drv));
}

lt_handle_t *tropic_get_handle(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return NULL;
  }

  return &drv->handle;
}

bool tropic_ping(const uint8_t *msg_out, uint8_t *msg_in, uint16_t msg_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  lt_ret_t res = lt_ping(&drv->handle, msg_out, msg_in, msg_len);
  return res == LT_OK;
}

bool tropic_get_cert(uint8_t *buf, uint16_t buf_size) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  // TODO what is the new function
  // lt_ret_t res = lt_get_info_cert(&drv->handle, buf, buf_size);
  return LT_OK;
}

bool tropic_ecc_key_generate(uint16_t slot_index) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (slot_index > ECC_SLOT_31) {
    return false;
  }

  lt_ret_t ret = lt_ecc_key_generate(&drv->handle, slot_index, CURVE_ED25519);
  return ret == LT_OK;
}

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t *dig,
                     uint16_t dig_len, uint8_t *sig, uint16_t sig_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (key_slot_index > ECC_SLOT_31) {
    return false;
  }

  lt_ret_t res =
      lt_ecc_eddsa_sign(&drv->handle, key_slot_index, dig, dig_len, sig);
  if (res != LT_OK) {
    memzero(sig, sig_len);
    return false;
  }

  return true;
}

#endif  // SECURE_MODE
