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

#include <string.h>

#include <pb.h>
#include <pb_decode.h>
#include <pb_encode.h>
#include "messages.pb.h"

#include "boot_internal.h"
#include TREZOR_BOARD

#ifdef USE_BLE
#include "ble/ble.h"
#include "ble_hal.h"
#endif
#include "common.h"
#include "flash.h"
#include "image.h"
#include "secbool.h"
#include "secret.h"
#include "unit_variant.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "protob_helpers.h"
#include "rust_ui.h"

#include "memzero.h"
#include "model.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

#if USE_OPTIGA
#include "secret.h"
#endif

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _write(pb_ostream_t *stream, const pb_byte_t *buf, size_t count) {
  write_state *state = (write_state *)(stream->state);

  size_t written = 0;
  // while we have data left
  while (written < count) {
    size_t remaining = count - written;
    // if all remaining data fit into our packet
    if (state->packet_pos + remaining <= USB_PACKET_SIZE) {
      // append data from buf to state->buf
      memcpy(state->buf + state->packet_pos, buf + written, remaining);
      // advance position
      state->packet_pos += remaining;
      // and return
      return true;
    } else {
      // append data that fits
      memcpy(state->buf + state->packet_pos, buf + written,
             USB_PACKET_SIZE - state->packet_pos);
      written += USB_PACKET_SIZE - state->packet_pos;
      // send packet

      if (state->iface_num == USB_IFACE_NUM) {
        int r = usb_webusb_write_blocking(state->iface_num, state->buf,
                                          USB_PACKET_SIZE, USB_TIMEOUT);
        ensure(sectrue * (r == USB_PACKET_SIZE), NULL);
      }
#ifdef USE_BLE
      else if (state->iface_num == BLE_INT_IFACE_NUM) {
        ble_int_comm_send(state->buf, USB_PACKET_SIZE, INTERNAL_MESSAGE);
      } else if (state->iface_num == BLE_EXT_IFACE_NUM) {
        ble_int_comm_send(state->buf, USB_PACKET_SIZE, EXTERNAL_MESSAGE);
      }
#endif

      // prepare new packet
      state->packet_index++;
      memzero(state->buf, USB_PACKET_SIZE);
      state->buf[0] = '?';
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void _write_flush(write_state *state) {
  // if packet is not filled up completely
  if (state->packet_pos < USB_PACKET_SIZE) {
    // pad it with zeroes
    memzero(state->buf + state->packet_pos,
            USB_PACKET_SIZE - state->packet_pos);
  }
  // send packet
  if (state->iface_num == USB_IFACE_NUM) {
    int r = usb_webusb_write_blocking(state->iface_num, state->buf,
                                      USB_PACKET_SIZE, USB_TIMEOUT);
    ensure(sectrue * (r == USB_PACKET_SIZE), NULL);
  }
#ifdef USE_BLE
  else if (state->iface_num == BLE_INT_IFACE_NUM) {
    ble_int_comm_send(state->buf, USB_PACKET_SIZE, INTERNAL_MESSAGE);
  } else if (state->iface_num == BLE_EXT_IFACE_NUM) {
    ble_int_comm_send(state->buf, USB_PACKET_SIZE, EXTERNAL_MESSAGE);
  }
#endif
}

#define BLE_GAP_PASSKEY_LEN 6

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _write_authkey(pb_ostream_t *stream, const pb_field_iter_t *field,
                           void *const *arg) {
  uint8_t *key = (uint8_t *)(*arg);
  if (!pb_encode_tag_for_field(stream, field)) return false;

  return pb_encode_string(stream, (uint8_t *)key, BLE_GAP_PASSKEY_LEN);
}

static bool _read_authkey(pb_istream_t *stream, const pb_field_t *field,
                          void **arg) {
  uint8_t *key_buffer = (uint8_t *)(*arg);

  if (stream->bytes_left > BLE_GAP_PASSKEY_LEN) {
    return false;
  }

  memset(key_buffer, 0, BLE_GAP_PASSKEY_LEN);

  while (stream->bytes_left) {
    // read data
    if (!pb_read(stream, (pb_byte_t *)(key_buffer),
                 (stream->bytes_left > BLE_GAP_PASSKEY_LEN)
                     ? BLE_GAP_PASSKEY_LEN
                     : stream->bytes_left)) {
      return false;
    }
  }

  return true;
}

static void _usb_webusb_read_retry(uint8_t iface_num, uint8_t *buf) {
  for (int retry = 0;; retry++) {
    int r =
        usb_webusb_read_blocking(iface_num, buf, USB_PACKET_SIZE, USB_TIMEOUT);
    if (r != USB_PACKET_SIZE) {  // reading failed
      if (r == 0 && retry < 10) {
        // only timeout => let's try again
        continue;
      } else {
        // error
        error_shutdown("USB ERROR",
                       "Error reading from USB. Try different USB cable.");
      }
    }
    return;  // success
  }
}

#ifdef USE_BLE
static void _ble_read_retry(uint8_t iface_num, uint8_t *buf) {
  for (int retry = 0;; retry++) {
    int r = ble_ext_comm_receive(buf, BLE_PACKET_SIZE);
    if (r != BLE_PACKET_SIZE) {  // reading failed
      if (r == 0 && retry < 500) {
        // only timeout => let's try again
        HAL_Delay(10);
        continue;
      } else {
        // error
        error_shutdown("BLE ERROR",
                       "Error reading from BLE. Try different BLE cable.");
      }
    }
    return;  // success
  }
}

static void _ble_read_retry_int(uint8_t iface_num, uint8_t *buf) {
  for (int retry = 0;; retry++) {
    int r = ble_int_comm_receive(buf, USB_PACKET_SIZE);
    if (r == 0) {  // reading failed
      if (retry < 500) {
        // only timeout => let's try again
        HAL_Delay(10);
        continue;
      } else {
        // error
        error_shutdown("BLE ERROR",
                       "Error reading from BLE. Try different BLE cable.");
      }
    }
    return;  // success
  }
}
#endif

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _read(pb_istream_t *stream, uint8_t *buf, size_t count) {
  read_state *state = (read_state *)(stream->state);

  size_t read = 0;
  // while we have data left
  while (read < count) {
    size_t remaining = count - read;
    // if all remaining data fit into our packet
    if (state->packet_pos + remaining <= state->packet_size) {
      // append data from buf to state->buf
      memcpy(buf + read, state->buf + state->packet_pos, remaining);
      // advance position
      state->packet_pos += remaining;
      // and return
      return true;
    } else {
      // append data that fits
      memcpy(buf + read, state->buf + state->packet_pos,
             state->packet_size - state->packet_pos);
      read += state->packet_size - state->packet_pos;
      // read next packet (with retry)
#ifdef USE_BLE
      if (state->iface_num == BLE_EXT_IFACE_NUM) {
        _ble_read_retry(state->iface_num, state->buf);
      } else if (state->iface_num == BLE_INT_IFACE_NUM) {
        _ble_read_retry_int(state->iface_num, state->buf);
      } else
#endif
      {
        _usb_webusb_read_retry(state->iface_num, state->buf);
      }
      // prepare next packet
      state->packet_index++;
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void _read_flush(read_state *state) { (void)state; }

#define MSG_SEND_BLD(msg) (MSG_SEND(msg, _write, _write_flush))
#ifdef USE_BLE
#define MSG_RECV_BLD(msg, iface_num) \
  (MSG_RECV(                         \
      msg, _read, _read_flush,       \
      ((iface_num) == BLE_EXT_IFACE_NUM ? BLE_PACKET_SIZE : USB_PACKET_SIZE)))
#else
#define MSG_RECV_BLD(msg, iface_num) \
  (MSG_RECV(msg, _read, _read_flush, USB_PACKET_SIZE))
#endif

void send_user_abort(uint8_t iface_num, const char *msg) {
  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ActionCancelled);
  MSG_SEND_ASSIGN_STRING(message, msg);
  MSG_SEND_BLD(Failure);
}

static void send_msg_features(uint8_t iface_num,
                              const vendor_header *const vhdr,
                              const image_header *const hdr) {
  MSG_SEND_INIT(Features);
  MSG_SEND_ASSIGN_STRING(vendor, "trezor.io");
  MSG_SEND_ASSIGN_REQUIRED_VALUE(major_version, VERSION_MAJOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(minor_version, VERSION_MINOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(patch_version, VERSION_PATCH);
  MSG_SEND_ASSIGN_VALUE(bootloader_mode, true);
  MSG_SEND_ASSIGN_STRING(model, MODEL_NAME);
  MSG_SEND_ASSIGN_STRING(internal_model, MODEL_INTERNAL_NAME);
  if (vhdr && hdr) {
    MSG_SEND_ASSIGN_VALUE(firmware_present, true);
    MSG_SEND_ASSIGN_VALUE(fw_major, (hdr->version & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_minor, ((hdr->version >> 8) & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_patch, ((hdr->version >> 16) & 0xFF));
    MSG_SEND_ASSIGN_STRING_LEN(fw_vendor, vhdr->vstr, vhdr->vstr_len);
  } else {
    MSG_SEND_ASSIGN_VALUE(firmware_present, false);
  }
  if (unit_variant_present()) {
    MSG_SEND_ASSIGN_VALUE(unit_color, unit_variant_get_color());
    MSG_SEND_ASSIGN_VALUE(unit_btconly, unit_variant_get_btconly());
  }
#if USE_OPTIGA
  MSG_SEND_ASSIGN_VALUE(bootloader_locked,
                        (secret_bootloader_locked() == sectrue));
#endif
  MSG_SEND_BLD(Features);
}

uint32_t process_msg_ComparisonRequest(uint8_t iface_num, uint32_t msg_size,
                                       uint8_t *buf) {
  uint8_t buffer[BLE_GAP_PASSKEY_LEN];
  MSG_RECV_INIT(ComparisonRequest);
  MSG_RECV_CALLBACK(key, _read_authkey, buffer);
  MSG_RECV_BLD(ComparisonRequest, iface_num);

  uint32_t result = screen_comparison_confirm(buffer, BLE_GAP_PASSKEY_LEN);

  if (result == INPUT_CONFIRM) {
    MSG_SEND_INIT(Success);
    MSG_SEND_BLD(Success);
  } else {
    send_user_abort(iface_num, "Pairing cancelled");
  }

  return result;
}

uint32_t process_msg_Pairing(uint8_t iface_num, uint32_t msg_size,
                             uint8_t *buf) {
  uint8_t buffer[BLE_GAP_PASSKEY_LEN];
  MSG_RECV_INIT(PairingRequest);
  MSG_RECV_BLD(PairingRequest, iface_num);

  uint32_t result = screen_pairing_confirm(buffer);

  if (result == INPUT_CONFIRM) {
    MSG_SEND_INIT(AuthKey);
    MSG_SEND_CALLBACK(key, _write_authkey, buffer);
    MSG_SEND_BLD(AuthKey);
  } else {
    send_user_abort(iface_num, "Pairing cancelled");
  }

  return result;
}

uint32_t process_msg_Repair(uint8_t iface_num, uint32_t msg_size,
                            uint8_t *buf) {
  MSG_RECV_INIT(RepairRequest);
  MSG_RECV_BLD(RepairRequest, iface_num);
  uint32_t result = screen_repair_confirm();
  if (result == INPUT_CONFIRM) {
    MSG_SEND_INIT(Success);
    MSG_SEND_BLD(Success);
  } else {
    send_user_abort(iface_num, "Pairing cancelled");
  }
  return result;
}

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                            const vendor_header *const vhdr,
                            const image_header *const hdr) {
  MSG_RECV_INIT(Initialize);
  MSG_RECV_BLD(Initialize, iface_num);
  send_msg_features(iface_num, vhdr, hdr);
}

void process_msg_GetFeatures(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                             const vendor_header *const vhdr,
                             const image_header *const hdr) {
  MSG_RECV_INIT(GetFeatures);
  MSG_RECV_BLD(GetFeatures, iface_num);
  send_msg_features(iface_num, vhdr, hdr);
}

void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf) {
  MSG_RECV_INIT(Ping);
  MSG_RECV_BLD(Ping, iface_num);

  MSG_SEND_INIT(Success);
  MSG_SEND_ASSIGN_STRING(message, msg_recv.message);
  MSG_SEND_BLD(Success);
}

static uint32_t firmware_remaining;
static uint32_t firmware_block;
static uint32_t chunk_requested;
static uint32_t erase_offset;

void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf) {
  firmware_remaining = 0;
  firmware_block = 0;
  chunk_requested = 0;
  erase_offset = 0;

  MSG_RECV_INIT(FirmwareErase);
  MSG_RECV_BLD(FirmwareErase, iface_num);

  firmware_remaining = msg_recv.has_length ? msg_recv.length : 0;
  if ((firmware_remaining > 0) &&
      ((firmware_remaining % sizeof(uint32_t)) == 0) &&
      (firmware_remaining <= FIRMWARE_IMAGE_MAXSIZE)) {
    // request new firmware
    chunk_requested = (firmware_remaining > IMAGE_INIT_CHUNK_SIZE)
                          ? IMAGE_INIT_CHUNK_SIZE
                          : firmware_remaining;
    MSG_SEND_INIT(FirmwareRequest);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, 0);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
    MSG_SEND_BLD(FirmwareRequest);
  } else {
    // invalid firmware size
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Wrong firmware size");
    MSG_SEND_BLD(Failure);
  }
}

static uint32_t chunk_size = 0;

__attribute__((section(".buf"))) uint32_t chunk_buffer[IMAGE_CHUNK_SIZE / 4];

#define CHUNK_BUFFER_PTR ((const uint8_t *const)&chunk_buffer)

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _read_payload(pb_istream_t *stream, const pb_field_t *field,
                          void **arg) {
#define BUFSIZE 32768

  size_t offset = (size_t)(*arg);

  if (stream->bytes_left > IMAGE_CHUNK_SIZE) {
    chunk_size = 0;
    return false;
  }

  if (offset == 0) {
    // clear chunk buffer
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
  }

  uint32_t chunk_written = offset;
  chunk_size = offset + stream->bytes_left;

  while (stream->bytes_left) {
    // update loader but skip first block
    if (firmware_block > 0) {
      ui_screen_install_progress_upload(
          1000 * (firmware_block * IMAGE_CHUNK_SIZE + chunk_written) /
          (firmware_block * IMAGE_CHUNK_SIZE + firmware_remaining));
    }
    // read data
    if (!pb_read(
            stream, (pb_byte_t *)(CHUNK_BUFFER_PTR + chunk_written),
            (stream->bytes_left > BUFSIZE) ? BUFSIZE : stream->bytes_left)) {
      chunk_size = 0;
      return false;
    }
    chunk_written += BUFSIZE;
  }

  return true;
}

static int version_compare(uint32_t vera, uint32_t verb) {
  /* Explicit casts so that we control how compiler does the unsigned shift
   * and correctly then promote uint8_t to int without possibility of
   * having implementation-defined right shift on negative int
   * in case compiler promoted the wrong unsinged int
   */
  int a, b;
  a = (uint8_t)vera & 0xFF;
  b = (uint8_t)verb & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 8) & 0xFF;
  b = (uint8_t)(verb >> 8) & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 16) & 0xFF;
  b = (uint8_t)(verb >> 16) & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 24) & 0xFF;
  b = (uint8_t)(verb >> 24) & 0xFF;
  return a - b;
}

static void detect_installation(const vendor_header *current_vhdr,
                                const image_header *current_hdr,
                                const vendor_header *const new_vhdr,
                                const image_header *const new_hdr,
                                secbool *is_new, secbool *keep_seed,
                                secbool *is_newvendor, secbool *is_upgrade) {
  *is_new = secfalse;
  *keep_seed = secfalse;
  *is_newvendor = secfalse;
  *is_upgrade = secfalse;
  if (sectrue != check_vendor_header_keys(current_vhdr)) {
    *is_new = sectrue;
    return;
  }
  if (sectrue != check_image_model(current_hdr)) {
    *is_new = sectrue;
    return;
  }
  if (sectrue != check_image_header_sig(current_hdr, current_vhdr->vsig_m,
                                        current_vhdr->vsig_n,
                                        current_vhdr->vpub)) {
    *is_new = sectrue;
    return;
  }
  uint8_t hash1[32], hash2[32];
  vendor_header_hash(new_vhdr, hash1);
  vendor_header_hash(current_vhdr, hash2);
  if (0 != memcmp(hash1, hash2, 32)) {
    *is_newvendor = sectrue;
    return;
  }
  if (version_compare(new_hdr->version, current_hdr->fix_version) < 0) {
    return;
  }
  if (version_compare(new_hdr->version, current_hdr->version) > 0) {
    *is_upgrade = sectrue;
  }

  *keep_seed = sectrue;
}

static int firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;
static size_t headers_offset = 0;
static size_t read_offset = 0;

int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf) {
  MSG_RECV_INIT(FirmwareUpload);
  MSG_RECV_CALLBACK(payload, _read_payload, read_offset);
  const secbool r = MSG_RECV_BLD(FirmwareUpload, iface_num);

  if (sectrue != r || chunk_size != (chunk_requested + read_offset)) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Invalid chunk size");
    MSG_SEND_BLD(Failure);
    return UPLOAD_ERR_INVALID_CHUNK_SIZE;
  }

  static image_header hdr;

  if (firmware_block == 0) {
    if (headers_offset == 0) {
      // first block and headers are not yet parsed
      vendor_header vhdr;

      if (sectrue != read_vendor_header(CHUNK_BUFFER_PTR, &vhdr)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid vendor header");
        MSG_SEND_BLD(Failure);
        return UPLOAD_ERR_INVALID_VENDOR_HEADER;
      }

      if (sectrue != check_vendor_header_keys(&vhdr)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid vendor header signature");
        MSG_SEND_BLD(Failure);
        return UPLOAD_ERR_INVALID_VENDOR_HEADER_SIG;
      }

      const image_header *received_hdr =
          read_image_header(CHUNK_BUFFER_PTR + vhdr.hdrlen,
                            FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);

      if (received_hdr !=
          (const image_header *)(CHUNK_BUFFER_PTR + vhdr.hdrlen)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid firmware header");
        MSG_SEND_BLD(Failure);
        return UPLOAD_ERR_INVALID_IMAGE_HEADER;
      }

      if (sectrue != check_image_model(received_hdr)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Wrong firmware model");
        MSG_SEND_BLD(Failure);
        return UPLOAD_ERR_INVALID_IMAGE_MODEL;
      }

      if (sectrue != check_image_header_sig(received_hdr, vhdr.vsig_m,
                                            vhdr.vsig_n, vhdr.vpub)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid firmware signature");
        MSG_SEND_BLD(Failure);
        return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
      }

      memcpy(&hdr, received_hdr, sizeof(hdr));

      vendor_header current_vhdr;

      secbool is_new = secfalse;

      if (sectrue !=
          read_vendor_header((const uint8_t *)FIRMWARE_START, &current_vhdr)) {
        is_new = sectrue;
      }

      const image_header *current_hdr = NULL;

      if (is_new == secfalse) {
        current_hdr = read_image_header(
            (const uint8_t *)FIRMWARE_START + current_vhdr.hdrlen,
            FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);

        if (current_hdr !=
            (const image_header *)(FIRMWARE_START + current_vhdr.hdrlen)) {
          is_new = sectrue;
        }
      }

      secbool should_keep_seed = secfalse;
      secbool is_newvendor = secfalse;
      secbool is_upgrade = secfalse;
      if (is_new == secfalse) {
        detect_installation(&current_vhdr, current_hdr, &vhdr, &hdr, &is_new,
                            &should_keep_seed, &is_newvendor, &is_upgrade);
      }

      secbool is_ilu = secfalse;  // interaction-less update

      if (g_boot_command == BOOT_COMMAND_INSTALL_UPGRADE) {
        BLAKE2S_CTX ctx;
        uint8_t hash[BLAKE2S_DIGEST_LENGTH];
        blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
        blake2s_Update(&ctx, CHUNK_BUFFER_PTR,
                       vhdr.hdrlen + received_hdr->hdrlen);
        blake2s_Final(&ctx, hash, BLAKE2S_DIGEST_LENGTH);

        // the firmware must be the same as confirmed by the user
        if (memcmp(&g_boot_args[0], hash, sizeof(hash)) != 0) {
          MSG_SEND_INIT(Failure);
          MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
          MSG_SEND_ASSIGN_STRING(message, "Firmware mismatch");
          MSG_SEND_BLD(Failure);
          return UPLOAD_ERR_FIRMWARE_MISMATCH;
        }

        // the firmware must be from the same vendor
        // the firmware must be newer
        if (is_upgrade != sectrue || is_newvendor != secfalse) {
          MSG_SEND_INIT(Failure);
          MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
          MSG_SEND_ASSIGN_STRING(message, "Not a firmware upgrade");
          MSG_SEND_BLD(Failure);
          return UPLOAD_ERR_NOT_FIRMWARE_UPGRADE;
        }

        if ((vhdr.vtrust & VTRUST_ALL) != VTRUST_ALL) {
          MSG_SEND_INIT(Failure);
          MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
          MSG_SEND_ASSIGN_STRING(message, "Not a full-trust image");
          MSG_SEND_BLD(Failure);
          return UPLOAD_ERR_NOT_FULLTRUST_IMAGE;
        }

        // upload the firmware without confirmation
        is_ilu = sectrue;
      }

#ifdef USE_OPTIGA
      if (sectrue != secret_wiped() && ((vhdr.vtrust & VTRUST_SECRET) != 0)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Install restricted");
        MSG_SEND(Failure);
        return UPLOAD_ERR_BOOTLOADER_LOCKED;
      }
#endif

      uint32_t response = INPUT_CANCEL;
      if (sectrue == is_new || sectrue == is_ilu) {
        // new installation or interaction less updated - auto confirm
        response = INPUT_CONFIRM;
      } else {
        int version_cmp = version_compare(hdr.version, current_hdr->version);
        response = ui_screen_install_confirm(&vhdr, &hdr, should_keep_seed,
                                             is_newvendor, version_cmp);
      }

      if (INPUT_CANCEL == response) {
        send_user_abort(iface_num, "Firmware install cancelled");
        return UPLOAD_ERR_USER_ABORT;
      }

      ui_screen_install_start();

      // if firmware is not upgrade, erase storage
      if (sectrue != should_keep_seed) {
        ensure(flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL),
               NULL);
      }

      headers_offset = IMAGE_HEADER_SIZE + vhdr.hdrlen;
      read_offset = IMAGE_INIT_CHUNK_SIZE;

      // request the rest of the first chunk
      MSG_SEND_INIT(FirmwareRequest);
      uint32_t chunk_limit = (firmware_remaining > IMAGE_CHUNK_SIZE)
                                 ? IMAGE_CHUNK_SIZE
                                 : firmware_remaining;
      chunk_requested = chunk_limit - read_offset;
      MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, read_offset);
      MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
      MSG_SEND_BLD(FirmwareRequest);

      firmware_remaining -= read_offset;
      return (int)firmware_remaining;
    } else {
      // first block with the headers parsed -> the first chunk is now complete
      read_offset = 0;
    }
  }

  // should not happen, but double-check
  if (flash_area_get_address(&FIRMWARE_AREA, firmware_block * IMAGE_CHUNK_SIZE,
                             0) == NULL) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Firmware too big");
    MSG_SEND_BLD(Failure);
    return UPLOAD_ERR_FIRMWARE_TOO_BIG;
  }

  if (sectrue != check_single_hash(hdr.hashes + firmware_block * 32,
                                   CHUNK_BUFFER_PTR + headers_offset,
                                   chunk_size - headers_offset)) {
    if (firmware_upload_chunk_retry > 0) {
      --firmware_upload_chunk_retry;
      MSG_SEND_INIT(FirmwareRequest);
      MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, firmware_block * IMAGE_CHUNK_SIZE);
      MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
      MSG_SEND_BLD(FirmwareRequest);
      return (int)firmware_remaining;
    }

    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Invalid chunk hash");
    MSG_SEND_BLD(Failure);
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

  // buffer with the received data
  const uint32_t *quadword_ptr = (const uint32_t *)CHUNK_BUFFER_PTR;
  // number of received bytes
  uint32_t bytes_remaining = chunk_size;
  // offset into the FIRMWARE_AREA part of the flash
  uint32_t write_offset = firmware_block * IMAGE_CHUNK_SIZE;

  while (bytes_remaining > 0) {
    // erase flash before writing
    uint32_t bytes_erased = 0;

    if (write_offset >= erase_offset) {
      // erase the next flash section
      ensure(
          flash_area_erase_partial(&FIRMWARE_AREA, erase_offset, &bytes_erased),
          NULL);
      erase_offset += bytes_erased;
    } else {
      // some erased space left from the previous round => use it
      bytes_erased = erase_offset - write_offset;
    }

    // write the received data
    uint32_t bytes_to_write = MIN(bytes_erased, bytes_remaining);
    uint32_t write_end = write_offset + bytes_to_write;

    ensure(flash_unlock_write(), NULL);
    while (write_offset < write_end) {
      // write a quad word (16 bytes) to the flash
      ensure(
          flash_area_write_quadword(&FIRMWARE_AREA, write_offset, quadword_ptr),
          NULL);
      write_offset += 4 * sizeof(uint32_t);
      quadword_ptr += 4;
    }
    ensure(flash_lock_write(), NULL);

    bytes_remaining -= bytes_to_write;
  }

  firmware_remaining -= chunk_requested;

  if (firmware_remaining == 0) {
    // erase the rest (unused part) of the FIRMWARE_AREA
    uint32_t bytes_erased = 0;
    do {
      ensure(
          flash_area_erase_partial(&FIRMWARE_AREA, erase_offset, &bytes_erased),
          NULL);
      erase_offset += bytes_erased;
    } while (bytes_erased > 0);
  }

  headers_offset = 0;
  firmware_block++;
  firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;

  if (firmware_remaining > 0) {
    chunk_requested = (firmware_remaining > IMAGE_CHUNK_SIZE)
                          ? IMAGE_CHUNK_SIZE
                          : firmware_remaining;
    MSG_SEND_INIT(FirmwareRequest);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, firmware_block * IMAGE_CHUNK_SIZE);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
    MSG_SEND_BLD(FirmwareRequest);
  } else {
    MSG_SEND_INIT(Success);
    MSG_SEND_BLD(Success);
  }
  return (int)firmware_remaining;
}

secbool bootloader_WipeDevice(void) {
#ifdef USE_BLE
  if (!ble_firmware_running()) {
    return secfalse;
  }
  stop_advertising();
  send_erase_bonds();

  if (!wait_for_answer()) {
    return secfalse;
  }
#endif

  return flash_area_erase(&WIPE_AREA, ui_screen_wipe_progress);
}

int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf) {
  secbool wipe_result = bootloader_WipeDevice();
  if (sectrue != wipe_result) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Could not erase flash");
    MSG_SEND_BLD(Failure);
    return WIPE_ERR_CANNOT_ERASE;
  } else {
    MSG_SEND_INIT(Success);
    MSG_SEND_BLD(Success);
    return WIPE_OK;
  }
}

void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf) {
  // consume remaining message
  int remaining_chunks = 0;

  if (msg_size > (USB_PACKET_SIZE - MSG_HEADER1_LEN)) {
    // calculate how many blocks need to be read to drain the message (rounded
    // up to not leave any behind)
    remaining_chunks = (msg_size - (USB_PACKET_SIZE - MSG_HEADER1_LEN) +
                        ((USB_PACKET_SIZE - MSG_HEADER2_LEN) - 1)) /
                       (USB_PACKET_SIZE - MSG_HEADER2_LEN);
  }

  for (int i = 0; i < remaining_chunks; i++) {
    // read next packet (with retry)
    _usb_webusb_read_retry(iface_num, buf);
  }

  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_UnexpectedMessage);
  MSG_SEND_ASSIGN_STRING(message, "Unexpected message");
  MSG_SEND_BLD(Failure);
}

#ifdef USE_OPTIGA
void process_msg_UnlockBootloader(uint8_t iface_num, uint32_t msg_size,
                                  uint8_t *buf) {
  secret_erase();
  MSG_SEND_INIT(Success);
  MSG_SEND(Success);
}
#endif
