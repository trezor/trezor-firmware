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

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <sec/secret_keys.h>
#include <sec/tropic.h>
#include <sys/systick.h>

#include <libtropic.h>

#ifdef TREZOR_EMULATOR
#include <arpa/inet.h>
#include <libtropic/hal/port/unix/lt_port_unix_tcp.h>
#include <time.h>
#endif

#include "ed25519-donna/ed25519.h"
#include "memzero.h"

#ifdef SECURE_MODE

typedef struct {
  bool initialized;
  bool sec_chan_established;
  lt_handle_t handle;
#ifdef TREZOR_EMULATOR
  lt_dev_unix_tcp_t device;
#endif
} tropic_driver_t;

static tropic_driver_t g_tropic_driver = {0};

#if !PRODUCTION
static bool tropic_get_tropic_pubkey(lt_handle_t *handle,
                                     curve25519_key pubkey);
#endif

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

  // Note: Without the delay below Tropic01 may return LT_L1_CHIP_BUSY. The
  // length was chosen arbitrarily. A shorter delay may be sufficient.
  hal_delay(100);

#ifdef TREZOR_EMULATOR
  pkey_index_t pairing_key_slot = TROPIC_FACTORY_PAIRING_KEY_SLOT;
#else
  pkey_index_t pairing_key_slot = TROPIC_PRIVILEGED_PAIRING_KEY_SLOT;
#endif

  curve25519_key trezor_privkey = {0};
  secbool privkey_ok = secret_key_tropic_pairing_privileged(trezor_privkey);
  if (privkey_ok != sectrue) {
    pairing_key_slot = TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
    privkey_ok = secret_key_tropic_pairing_unprivileged(trezor_privkey);
  }

  curve25519_key tropic_pubkey = {0};
  secbool pubkey_ok = secret_key_tropic_public(tropic_pubkey);

#if !PRODUCTION
  // Allow running with default factory keys in non-production fw
  if (privkey_ok != sectrue) {
    static const curve25519_key factory_private = {
        0x28, 0x3f, 0x5a, 0x0f, 0xfc, 0x41, 0xcf, 0x50, 0x98, 0xa8, 0xe1,
        0x7d, 0xb6, 0x37, 0x2c, 0x3c, 0xaa, 0xd1, 0xee, 0xee, 0xdf, 0x0f,
        0x75, 0xbc, 0x3f, 0xbf, 0xcd, 0x9c, 0xab, 0x3d, 0xe9, 0x72};

    pairing_key_slot = TROPIC_FACTORY_PAIRING_KEY_SLOT;
    memcpy(trezor_privkey, factory_private, sizeof(trezor_privkey));
    privkey_ok = sectrue;
  }

  if (pubkey_ok != sectrue) {
    pubkey_ok = tropic_get_tropic_pubkey(&drv->handle, tropic_pubkey) * sectrue;
  }
#endif

  if (pubkey_ok == sectrue && privkey_ok == sectrue) {
    curve25519_key trezor_pubkey = {0};
    curve25519_scalarmult_basepoint(trezor_pubkey, trezor_privkey);

    lt_ret_t ret =
        lt_session_start(&drv->handle, tropic_pubkey, pairing_key_slot,
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

bool tropic_data_read(uint16_t udata_slot, uint8_t *data, uint16_t *size) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (udata_slot > R_MEM_DATA_SLOT_MAX) {
    return false;
  }

  lt_ret_t res = lt_r_mem_data_read(&drv->handle, udata_slot, data, size);
  return res == LT_OK;
}

#if !PRODUCTION
static bool tropic_get_tropic_pubkey(lt_handle_t *handle,
                                     curve25519_key pubkey) {
  uint8_t buffer[LT_NUM_CERTIFICATES * LT_L2_GET_INFO_REQ_CERT_SIZE_SINGLE];

  struct lt_cert_store_t cert_store = {0};
  for (size_t i = 0; i < LT_NUM_CERTIFICATES; i++) {
    cert_store.certs[i] = &buffer[i * LT_L2_GET_INFO_REQ_CERT_SIZE_SINGLE];
    cert_store.buf_len[i] = LT_L2_GET_INFO_REQ_CERT_SIZE_SINGLE;
  }

  lt_ret_t ret = LT_FAIL;

  ret = lt_get_info_cert_store(handle, &cert_store);
  if (ret != LT_OK) {
    return false;
  }

  ret = lt_get_st_pub(&cert_store, pubkey, sizeof(curve25519_key));
  if (ret != LT_OK) {
    return false;
  }

  return true;
}
#endif  // !PRODUCTION

#endif  // SECURE_MODE

bool tropic_data_multi_size(uint16_t first_slot, size_t *data_length) {
  if (first_slot > R_MEM_DATA_SLOT_MAX) {
    return false;
  }

  uint8_t prefixed_data[R_MEM_DATA_SIZE_MAX];
  uint16_t slot_length = 0;
  if (!tropic_data_read(first_slot, prefixed_data, &slot_length)) {
    return false;
  }

  const size_t prefix_length = 2;
  if (slot_length < prefix_length) {
    return false;
  }

  *data_length = prefixed_data[0] << 8 | prefixed_data[1];
  return true;
}

static size_t min(size_t x, size_t y) { return (x < y) ? x : y; }

bool tropic_data_multi_read(uint16_t first_slot, uint16_t slot_count,
                            uint8_t *data, size_t max_data_length,
                            size_t *data_length) {
  if (first_slot > R_MEM_DATA_SLOT_MAX || slot_count == 0 ||
      slot_count > R_MEM_DATA_SLOT_MAX + 1 - first_slot) {
    return false;
  }

  uint16_t slot = first_slot;
  uint8_t slot_buffer[R_MEM_DATA_SIZE_MAX] = {0};
  uint16_t slot_length = 0;
  if (!tropic_data_read(slot, slot_buffer, &slot_length)) {
    return false;
  }

  const size_t prefix_length = 2;
  if (slot_length < prefix_length) {
    return false;
  }

  size_t out_length = slot_buffer[0] << 8 | slot_buffer[1];
  uint16_t occupied_slot_count =
      (out_length + prefix_length + R_MEM_DATA_SIZE_MAX - 1) /
      R_MEM_DATA_SIZE_MAX;
  if (out_length > max_data_length || occupied_slot_count > slot_count) {
    return false;
  }

  size_t out_pos = 0;
  // Terminal slots may be padded. Make sure not to copy beyond the actual data
  // length.
  size_t copy_length = min(slot_length - prefix_length, out_length - out_pos);
  if (out_pos + copy_length > max_data_length) {
    false;
  }
  memcpy(&data[out_pos], &slot_buffer[prefix_length], copy_length);
  out_pos += copy_length;

  uint16_t last_data_slot = first_slot + occupied_slot_count - 1;
  while (slot < last_data_slot) {
    // Non-terminal slots must be used to their full capacity.
    if (slot_length != R_MEM_DATA_SIZE_MAX) {
      return false;
    }

    // Read next slot.
    slot += 1;
    if (!tropic_data_read(slot, slot_buffer, &slot_length)) {
      return false;
    }

    // Terminal slots may be padded. Make sure not to copy beyond the actual
    // data length.
    copy_length = min(slot_length, out_length - out_pos);
    memcpy(&data[out_pos], slot_buffer, copy_length);
    out_pos += copy_length;
  }

  if (out_pos != out_length) {
    // The terminal slot had less data than expected.
    return false;
  }

  *data_length = out_length;

  return true;
}
