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

#include <sec/rng.h>
#include <sec/secret_keys.h>
#include <sec/tropic.h>
#include <sys/systick.h>

#include "hmac.h"

#include <libtropic.h>

#ifdef TREZOR_EMULATOR
#include <arpa/inet.h>
#include <libtropic/hal/port/unix/lt_port_unix_tcp.h>
#include <time.h>
#endif

#include "ed25519-donna/ed25519.h"
#include "memzero.h"

#ifdef SECURE_MODE

// Maximum time to wait for Tropic to boot. Chosen arbitrarily.
#define TROPIC_BOOT_TIMEOUT_MS 1000

typedef struct {
  bool initialized;
  bool session_started;
  bool chip_ready;
  pkey_index_t pairing_key_index;
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

bool tropic_wait_for_ready(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (drv->chip_ready) {
    return true;
  }

  // Wait for Tropic to boot before issuing any session commands.
  uint32_t boot_start_ms = hal_ticks_ms();
  while (hal_ticks_ms() - boot_start_ms < TROPIC_BOOT_TIMEOUT_MS) {
    uint8_t ver[LT_L2_GET_INFO_RISCV_FW_SIZE] = {0};
    if (lt_get_info_riscv_fw_ver(&drv->handle, ver) != LT_L1_CHIP_BUSY) {
      drv->chip_ready = true;
      return true;
    }
  }

  return false;
}

lt_ret_t tropic_start_custom_session(const uint8_t *stpub,
                                     const pkey_index_t pkey_index,
                                     const uint8_t *shipriv,
                                     const uint8_t *shipub) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return LT_FAIL;
  }

  tropic_wait_for_ready();

  lt_ret_t ret =
      lt_session_start(&drv->handle, stpub, pkey_index, shipriv, shipub);

  drv->pairing_key_index = pkey_index;
  drv->session_started = (ret == LT_OK);

  return ret;
}

static bool session_start(tropic_driver_t *drv,
                          pkey_index_t pairing_key_index) {
  bool ret = false;

  curve25519_key trezor_private = {0};
  switch (pairing_key_index) {
    case TROPIC_FACTORY_PAIRING_KEY_SLOT:
      tropic_get_factory_privkey(trezor_private);
      break;
    case TROPIC_PRIVILEGED_PAIRING_KEY_SLOT:
      if (secret_key_tropic_pairing_privileged(trezor_private) != sectrue) {
        goto cleanup;
      }
      break;
    case TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT:
      if (secret_key_tropic_pairing_unprivileged(trezor_private) != sectrue) {
        goto cleanup;
      }
      break;
    default:
      goto cleanup;
  }

  curve25519_key trezor_public = {0};
  curve25519_scalarmult_basepoint(trezor_public, trezor_private);

  curve25519_key tropic_public = {0};
  if (secret_key_tropic_public(tropic_public) != sectrue) {
#if !PRODUCTION
    if (!tropic_get_tropic_pubkey(&drv->handle, tropic_public))
#endif
    {
      goto cleanup;
    }
  }

  if (tropic_start_custom_session(tropic_public, pairing_key_index,
                                  trezor_private, trezor_public) != LT_OK) {
    goto cleanup;
  }

  ret = true;

cleanup:
  memzero(trezor_private, sizeof(trezor_private));

  return ret;
}

bool tropic_session_start(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (drv->session_started) {
    return true;
  }

  tropic_wait_for_ready();

#ifndef TREZOR_EMULATOR
  if (session_start(drv, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT)) {
    return true;
  }
  if (session_start(drv, TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT)) {
    return true;
  }
#endif
#if !PRODUCTION
  if (session_start(drv, TROPIC_FACTORY_PAIRING_KEY_SLOT)) {
    return true;
  }
#endif

  return false;
}

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
    return false;
  }
  drv->initialized = true;

  return true;
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

  if (!tropic_session_start()) {
    return false;
  }

  lt_ret_t res = lt_ping(&drv->handle, msg_out, msg_in, msg_len);
  return res == LT_OK;
}

bool tropic_ecc_key_generate(uint16_t slot_index) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
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

  if (!tropic_session_start()) {
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

  if (!tropic_session_start()) {
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

void tropic_get_factory_privkey(curve25519_key privkey) {
#ifdef TREZOR_EMULATOR
  curve25519_key factory_private = {
      0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0, 0x96, 0x84, 0xdf,
      0x05, 0xe8, 0xa2, 0x2e, 0xf7, 0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9,
      0x43, 0x12, 0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};
#else
#ifdef TROPIC_TESTING_KEYS
  // Testing keys (used in TROPIC01-P2S-P001)
  curve25519_key factory_private = {
      0xd0, 0x99, 0x92, 0xb1, 0xf1, 0x7a, 0xbc, 0x4d, 0xb9, 0x37, 0x17,
      0x68, 0xa2, 0x7d, 0xa0, 0x5b, 0x18, 0xfa, 0xb8, 0x56, 0x13, 0xa7,
      0x84, 0x2c, 0xa6, 0x4c, 0x79, 0x10, 0xf2, 0x2e, 0x71, 0x6b};
#else
  // Production keys
  curve25519_key factory_private = {
      0x28, 0x3f, 0x5a, 0x0f, 0xfc, 0x41, 0xcf, 0x50, 0x98, 0xa8, 0xe1,
      0x7d, 0xb6, 0x37, 0x2c, 0x3c, 0xaa, 0xd1, 0xee, 0xee, 0xdf, 0x0f,
      0x75, 0xbc, 0x3f, 0xbf, 0xcd, 0x9c, 0xab, 0x3d, 0xe9, 0x72};
#endif
#endif
  memcpy(privkey, factory_private, sizeof(curve25519_key));
}

bool tropic_random_buffer(void *buffer, size_t length) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (LT_OK != lt_random_value_get(&drv->handle, buffer, length)) {
    return false;
  }

  return true;
}

#ifdef USE_STORAGE

static mac_and_destroy_slot_t get_first_mac_and_destroy_slot(
    tropic_driver_t *drv) {
  return drv->pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT
             ? TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED
             : TROPIC_FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED;
}

static uint16_t get_kek_masks_slot(tropic_driver_t *drv) {
  return drv->pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT
             ? TROPIC_KEK_MASKS_UNPRIVILEGED_SLOT
             : TROPIC_KEK_MASKS_PRIVILEGED_SLOT;
}

bool tropic_pin_stretch(tropic_ui_progress_t ui_progress, uint16_t pin_index,
                        uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE]) {
  // Time: 50 ms

  if (pin_index >= PIN_MAX_TRIES) {
    return false;
  }

  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  mac_and_destroy_slot_t first_slot_index = get_first_mac_and_destroy_slot(drv);

  uint8_t digest[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  hmac_sha256(stretched_pin, TROPIC_MAC_AND_DESTROY_SIZE, NULL, 0, digest);

  ui_progress();

  lt_ret_t res = lt_mac_and_destroy(&drv->handle, first_slot_index + pin_index,
                                    digest, digest);

  ui_progress();

  hmac_sha256(stretched_pin, TROPIC_MAC_AND_DESTROY_SIZE, digest,
              sizeof(digest), stretched_pin);

  memzero(digest, sizeof(digest));
  return res == LT_OK;
}

bool tropic_pin_reset_slots(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]) {
  // Time: (pin_index + 1) * 50 ms

  if (pin_index >= PIN_MAX_TRIES) {
    return false;
  }

  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  lt_ret_t res = LT_FAIL;
  uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  mac_and_destroy_slot_t first_slot_index = get_first_mac_and_destroy_slot(drv);

  ui_progress();

  for (int i = 0; i <= pin_index; i++) {
    res = lt_mac_and_destroy(&drv->handle, first_slot_index + i, reset_key,
                             output);
    if (res != LT_OK) {
      goto cleanup;
    }

    ui_progress();
  }

cleanup:
  memzero(output, sizeof(output));

  return res == LT_OK;
}

bool tropic_pin_set(
    tropic_ui_progress_t ui_progress,
    uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]) {
  // Time: 65 ms + PIN_MAX_TRIES * 155 ms

  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (!rng_fill_buffer_strong(reset_key, TROPIC_MAC_AND_DESTROY_SIZE)) {
    return false;
  }

  lt_ret_t res = LT_FAIL;
  uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  uint8_t digest[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  mac_and_destroy_slot_t first_slot_index = get_first_mac_and_destroy_slot(drv);

  ui_progress();

  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    res = lt_mac_and_destroy(&drv->handle, first_slot_index + i, reset_key,
                             output);
    if (res != LT_OK) {
      goto cleanup;
    }

    hmac_sha256(stretched_pins[i], TROPIC_MAC_AND_DESTROY_SIZE, NULL, 0,
                digest);

    ui_progress();

    res =
        lt_mac_and_destroy(&drv->handle, first_slot_index + i, digest, digest);
    if (res != LT_OK) {
      goto cleanup;
    }

    ui_progress();

    hmac_sha256(stretched_pins[i], TROPIC_MAC_AND_DESTROY_SIZE, digest,
                sizeof(digest), stretched_pins[i]);

    res = lt_mac_and_destroy(&drv->handle, first_slot_index + i, reset_key,
                             output);
    if (res != LT_OK) {
      goto cleanup;
    }

    ui_progress();
  }

cleanup:
  memzero(output, sizeof(output));
  memzero(digest, sizeof(digest));

  return res == LT_OK;
}

bool tropic_pin_set_kek_masks(
    tropic_ui_progress_t ui_progress,
    const uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE],
    const uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE]) {
  // Time: 130 ms

  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  lt_ret_t ret = LT_FAIL;

  uint8_t masks[PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    for (int j = 0; j < TROPIC_MAC_AND_DESTROY_SIZE; j++) {
      masks[i * TROPIC_MAC_AND_DESTROY_SIZE + j] =
          kek[j] ^ stretched_pins[i][j];
    }
  }

  ui_progress();

  uint16_t masked_kek_slot = get_kek_masks_slot(drv);

  ret = lt_r_mem_data_erase(&drv->handle, masked_kek_slot);
  if (ret != LT_OK) {
    goto cleanup;
  }

  ui_progress();

  ret =
      lt_r_mem_data_write(&drv->handle, masked_kek_slot, masks, sizeof(masks));
  if (ret != LT_OK) {
    goto cleanup;
  }

  ui_progress();

cleanup:
  memzero(masks, sizeof(masks));

  return ret == LT_OK;
}

bool tropic_pin_unmask_kek(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE]) {
  // Time: 100 ms

  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  uint8_t masks[R_MEM_DATA_SIZE_MAX] = {0};
  _Static_assert(
      R_MEM_DATA_SIZE_MAX >= PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE,
      "R_MEM_DATA_SIZE_MAX too small");
  uint16_t length = 0;

  uint16_t masked_kek_slot = get_kek_masks_slot(drv);

  ui_progress();

  if (lt_r_mem_data_read(&drv->handle, masked_kek_slot, masks, &length) !=
      LT_OK) {
    return false;
  }

  if (length != PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE) {
    return false;
  }

  ui_progress();

  for (int i = 0; i < TROPIC_MAC_AND_DESTROY_SIZE; i++) {
    kek[i] =
        masks[pin_index * TROPIC_MAC_AND_DESTROY_SIZE + i] ^ stretched_pin[i];
  }
  return true;
}

uint32_t tropic_estimate_time_ms(storage_pin_op_t op, uint16_t pin_index) {
  const int set_time = 65 + PIN_MAX_TRIES * 155;
  const int set_kek_masks_time = 130;
  const int stretch_time = 50;
  const int unmask_kek_time = 100;
  const int reset_slots_time = (pin_index + 1) * 50;

  const int pin_verify_time = stretch_time + unmask_kek_time + reset_slots_time;
  const int pin_set_time = set_time + set_kek_masks_time;

  switch (op) {
    case STORAGE_PIN_OP_SET:
      return pin_set_time;
    case STORAGE_PIN_OP_VERIFY:
      return pin_verify_time;
    case STORAGE_PIN_OP_CHANGE:
      return pin_set_time + pin_verify_time;
    default:
      return 0;
  }
}

#endif  // USE_STORAGE

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
