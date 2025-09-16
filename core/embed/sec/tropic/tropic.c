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

#include <sys/systick.h>

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

  // TODO: Revert
  curve25519_key trezor_privkey = {
      0x28, 0x3f, 0x5a, 0x0f, 0xfc, 0x41, 0xcf, 0x50, 0x98, 0xa8, 0xe1,
      0x7d, 0xb6, 0x37, 0x2c, 0x3c, 0xaa, 0xd1, 0xee, 0xee, 0xdf, 0x0f,
      0x75, 0xbc, 0x3f, 0xbf, 0xcd, 0x9c, 0xab, 0x3d, 0xe9, 0x72};

  curve25519_key trezor_pubkey = {0};
  curve25519_scalarmult_basepoint(trezor_pubkey, trezor_privkey);

  hal_delay(100);

  lt_ret_t ret = lt_verify_chip_and_start_secure_session(
      &drv->handle, trezor_privkey, trezor_pubkey, 0);

  drv->sec_chan_established = (ret == LT_OK);
  ensure(sectrue * drv->sec_chan_established, "lt_session_start failed");

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
                     uint16_t dig_len, uint8_t *sig) {
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
    memzero(sig, ECDSA_RAW_SIGNATURE_SIZE);
    return false;
  }

  return true;
}

bool tropic_stretch_pin(tropic_ui_progress_t ui_progress, uint8_t slot_index,
                        uint8_t stretched_pin[MAC_AND_DESTROY_DATA_SIZE]) {
  if (slot_index >= PIN_MAX_TRIES) {
    return false;
  }

  // TODO: Fix ui progress
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  return lt_mac_and_destroy(&drv->handle, slot_index, stretched_pin,
                            stretched_pin) == LT_OK;
}

bool tropic_reset_slots(tropic_ui_progress_t ui_progress, uint8_t slot_index,
                        const uint8_t reset_key[MAC_AND_DESTROY_DATA_SIZE]) {
  if (slot_index >= PIN_MAX_TRIES) {
    return false;
  }

  // TODO: Fix ui progress
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  lt_ret_t res = LT_FAIL;
  uint8_t output[MAC_AND_DESTROY_DATA_SIZE] = {0};

  for (int i = 0; i <= slot_index; i++) {
    res = lt_mac_and_destroy(&drv->handle, i, reset_key, output);
    if (res != LT_OK) {
      goto cleanup;
    }
  }

cleanup:
  memzero(output, sizeof(output));

  return res == LT_OK;
}

bool tropic_pin_set(
    tropic_ui_progress_t ui_progress,
    uint8_t stretched_pins[PIN_MAX_TRIES][MAC_AND_DESTROY_DATA_SIZE],
    uint8_t reset_key[MAC_AND_DESTROY_DATA_SIZE]) {
  // TODO: Fix ui progress
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  lt_ret_t res = LT_FAIL;
  uint8_t output[MAC_AND_DESTROY_DATA_SIZE] = {0};

  // TODO: Use entropy from Optiga and MCU
  res = lt_random_value_get(&drv->handle, reset_key, MAC_AND_DESTROY_DATA_SIZE);
  if (res != LT_OK) {
    goto cleanup;
  }

  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    res = lt_mac_and_destroy(&drv->handle, i, reset_key, output);
    if (res != LT_OK) {
      goto cleanup;
    }

    res = lt_mac_and_destroy(&drv->handle, i, stretched_pins[i],
                             stretched_pins[i]);
    if (res != LT_OK) {
      goto cleanup;
    }

    res = lt_mac_and_destroy(&drv->handle, i, reset_key, output);
    if (res != LT_OK) {
      goto cleanup;
    }
  }

cleanup:
  memzero(output, sizeof(output));

  return res == LT_OK;
}

#endif  // SECURE_MODE
