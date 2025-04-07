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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <sec/secret.h>
#include <sec/tropic.h>

#include <libtropic.h>

#include "ed25519-donna/ed25519.h"
#include "memzero.h"
#include "tropic_internal.h"

#define PKEY_INDEX_BYTE PAIRING_KEY_SLOT_INDEX_0

typedef struct {
  bool initialized;
  bool sec_chan_established;
  lt_handle_t handle;
} tropic_driver_t;

static tropic_driver_t g_tropic_driver = {0};

bool tropic_init(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (drv->initialized) {
    return true;
  }

  uint8_t tropic_secret_tropic_pubkey[SECRET_TROPIC_KEY_LEN] = {0};
  uint8_t tropic_secret_trezor_privkey[SECRET_TROPIC_KEY_LEN] = {0};

  if (!tropic_hal_init()) {
    goto cleanup;
  }

  if (lt_init(&drv->handle) != LT_OK) {
    tropic_hal_deinit();
    goto cleanup;
  }

  secbool pubkey_ok =
      secret_tropic_get_tropic_pubkey(tropic_secret_tropic_pubkey);
  secbool privkey_ok =
      secret_tropic_get_trezor_privkey(tropic_secret_trezor_privkey);

  if (pubkey_ok == sectrue && privkey_ok == sectrue) {
    uint8_t trezor_pubkey[SECRET_TROPIC_KEY_LEN] = {0};
    curve25519_scalarmult_basepoint(trezor_pubkey,
                                    tropic_secret_trezor_privkey);

    lt_ret_t ret = lt_session_start(
        &drv->handle, tropic_secret_tropic_pubkey, PKEY_INDEX_BYTE,
        tropic_secret_trezor_privkey, trezor_pubkey);

    // todo delete the ensure
    ensure((ret == LT_OK) * sectrue, "lt_session_start failed");
    drv->sec_chan_established = (ret == LT_OK);
  }

  memzero(tropic_secret_trezor_privkey, sizeof(tropic_secret_trezor_privkey));
  memzero(tropic_secret_trezor_privkey, sizeof(tropic_secret_tropic_pubkey));

  drv->initialized = true;

  return true;

cleanup:
  tropic_deinit();
  return false;
}

void tropic_deinit(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (drv->handle.device != NULL) {
    lt_deinit(&drv->handle);
  }

  tropic_hal_deinit();

  memset(drv, 0, sizeof(*drv));
}

bool tropic_get_spect_fw_version(uint8_t *version_buffer, uint16_t max_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (LT_OK != lt_get_info_spect_fw_ver(&drv->handle, (uint8_t *)version_buffer,
                                        max_len)) {
    return false;
  }

  return true;
}

bool tropic_get_riscv_fw_version(uint8_t *version_buffer, uint16_t max_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (LT_OK != lt_get_info_riscv_fw_ver(&drv->handle, (uint8_t *)version_buffer,
                                        max_len)) {
    return false;
  }

  return true;
}

bool tropic_get_chip_id(uint8_t *chip_id, uint16_t max_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (LT_OK != lt_get_info_chip_id(&drv->handle, (uint8_t *)chip_id, max_len)) {
    return false;
  }

  return true;
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

  lt_ret_t res = lt_get_info_cert(&drv->handle, buf, buf_size);
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
                     uint16_t dig_len, uint8_t *sig, uint16_t sig_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (key_slot_index > ECC_SLOT_31) {
    return false;
  }

  lt_ret_t res = lt_ecc_eddsa_sign(&drv->handle, key_slot_index, dig, dig_len,
                                   sig, sig_len);
  if (res != LT_OK) {
    memzero(sig, sig_len);
    return false;
  }

  return true;
}

#endif
