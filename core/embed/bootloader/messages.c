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

#include "common.h"
#include "flash.h"
#include "image.h"
#include "secbool.h"
#include "unit_variant.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "rust_ui.h"

#include "memzero.h"
#include "model.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

#define MSG_HEADER1_LEN 9
#define MSG_HEADER2_LEN 1

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id,
                         uint32_t *msg_size) {
  if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {
    return secfalse;
  }
  *msg_id = (buf[3] << 8) + buf[4];
  *msg_size = (buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
  return sectrue;
}

typedef struct {
  uint8_t iface_num;
  uint8_t packet_index;
  uint8_t packet_pos;
  uint8_t buf[USB_PACKET_SIZE];
} usb_write_state;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _usb_write(pb_ostream_t *stream, const pb_byte_t *buf,
                       size_t count) {
  usb_write_state *state = (usb_write_state *)(stream->state);

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
      int r = usb_webusb_write_blocking(state->iface_num, state->buf,
                                        USB_PACKET_SIZE, USB_TIMEOUT);
      ensure(sectrue * (r == USB_PACKET_SIZE), NULL);
      // prepare new packet
      state->packet_index++;
      memzero(state->buf, USB_PACKET_SIZE);
      state->buf[0] = '?';
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void _usb_write_flush(usb_write_state *state) {
  // if packet is not filled up completely
  if (state->packet_pos < USB_PACKET_SIZE) {
    // pad it with zeroes
    memzero(state->buf + state->packet_pos,
            USB_PACKET_SIZE - state->packet_pos);
  }
  // send packet
  int r = usb_webusb_write_blocking(state->iface_num, state->buf,
                                    USB_PACKET_SIZE, USB_TIMEOUT);
  ensure(sectrue * (r == USB_PACKET_SIZE), NULL);
}

static secbool _send_msg(uint8_t iface_num, uint16_t msg_id,
                         const pb_msgdesc_t *fields, const void *msg) {
  // determine message size by serializing it into a dummy stream
  pb_ostream_t sizestream = {.callback = NULL,
                             .state = NULL,
                             .max_size = SIZE_MAX,
                             .bytes_written = 0,
                             .errmsg = NULL};
  if (false == pb_encode(&sizestream, fields, msg)) {
    return secfalse;
  }
  const uint32_t msg_size = sizestream.bytes_written;

  usb_write_state state = {
      .iface_num = iface_num,
      .packet_index = 0,
      .packet_pos = MSG_HEADER1_LEN,
      .buf =
          {
              '?',
              '#',
              '#',
              (msg_id >> 8) & 0xFF,
              msg_id & 0xFF,
              (msg_size >> 24) & 0xFF,
              (msg_size >> 16) & 0xFF,
              (msg_size >> 8) & 0xFF,
              msg_size & 0xFF,
          },
  };

  pb_ostream_t stream = {.callback = &_usb_write,
                         .state = &state,
                         .max_size = SIZE_MAX,
                         .bytes_written = 0,
                         .errmsg = NULL};

  if (false == pb_encode(&stream, fields, msg)) {
    return secfalse;
  }

  _usb_write_flush(&state);

  return sectrue;
}

#define MSG_SEND_INIT(TYPE) TYPE msg_send = TYPE##_init_default
#define MSG_SEND_ASSIGN_REQUIRED_VALUE(FIELD, VALUE) \
  { msg_send.FIELD = VALUE; }
#define MSG_SEND_ASSIGN_VALUE(FIELD, VALUE) \
  {                                         \
    msg_send.has_##FIELD = true;            \
    msg_send.FIELD = VALUE;                 \
  }
#define MSG_SEND_ASSIGN_STRING(FIELD, VALUE)                    \
  {                                                             \
    msg_send.has_##FIELD = true;                                \
    memzero(msg_send.FIELD, sizeof(msg_send.FIELD));            \
    strncpy(msg_send.FIELD, VALUE, sizeof(msg_send.FIELD) - 1); \
  }
#define MSG_SEND_ASSIGN_STRING_LEN(FIELD, VALUE, LEN)                     \
  {                                                                       \
    msg_send.has_##FIELD = true;                                          \
    memzero(msg_send.FIELD, sizeof(msg_send.FIELD));                      \
    strncpy(msg_send.FIELD, VALUE, MIN(LEN, sizeof(msg_send.FIELD) - 1)); \
  }
#define MSG_SEND_ASSIGN_BYTES(FIELD, VALUE, LEN)                  \
  {                                                               \
    msg_send.has_##FIELD = true;                                  \
    memzero(msg_send.FIELD.bytes, sizeof(msg_send.FIELD.bytes));  \
    memcpy(msg_send.FIELD.bytes, VALUE,                           \
           MIN(LEN, sizeof(msg_send.FIELD.bytes)));               \
    msg_send.FIELD.size = MIN(LEN, sizeof(msg_send.FIELD.bytes)); \
  }
#define MSG_SEND(TYPE) \
  _send_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, &msg_send)

typedef struct {
  uint8_t iface_num;
  uint8_t packet_index;
  uint8_t packet_pos;
  uint8_t *buf;
} usb_read_state;

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

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _usb_read(pb_istream_t *stream, uint8_t *buf, size_t count) {
  usb_read_state *state = (usb_read_state *)(stream->state);

  size_t read = 0;
  // while we have data left
  while (read < count) {
    size_t remaining = count - read;
    // if all remaining data fit into our packet
    if (state->packet_pos + remaining <= USB_PACKET_SIZE) {
      // append data from buf to state->buf
      memcpy(buf + read, state->buf + state->packet_pos, remaining);
      // advance position
      state->packet_pos += remaining;
      // and return
      return true;
    } else {
      // append data that fits
      memcpy(buf + read, state->buf + state->packet_pos,
             USB_PACKET_SIZE - state->packet_pos);
      read += USB_PACKET_SIZE - state->packet_pos;
      // read next packet (with retry)
      _usb_webusb_read_retry(state->iface_num, state->buf);
      // prepare next packet
      state->packet_index++;
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void _usb_read_flush(usb_read_state *state) { (void)state; }

static secbool _recv_msg(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                         const pb_msgdesc_t *fields, void *msg) {
  usb_read_state state = {.iface_num = iface_num,
                          .packet_index = 0,
                          .packet_pos = MSG_HEADER1_LEN,
                          .buf = buf};

  pb_istream_t stream = {.callback = &_usb_read,
                         .state = &state,
                         .bytes_left = msg_size,
                         .errmsg = NULL};

  if (false == pb_decode_noinit(&stream, fields, msg)) {
    return secfalse;
  }

  _usb_read_flush(&state);

  return sectrue;
}

#define MSG_RECV_INIT(TYPE) TYPE msg_recv = TYPE##_init_default
#define MSG_RECV_CALLBACK(FIELD, CALLBACK, ARGUMENT) \
  {                                                  \
    msg_recv.FIELD.funcs.decode = &CALLBACK;         \
    msg_recv.FIELD.arg = (void *)ARGUMENT;           \
  }
#define MSG_RECV(TYPE) \
  _recv_msg(iface_num, msg_size, buf, TYPE##_fields, &msg_recv)

void send_user_abort(uint8_t iface_num, const char *msg) {
  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ActionCancelled);
  MSG_SEND_ASSIGN_STRING(message, msg);
  MSG_SEND(Failure);
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
  MSG_SEND(Features);
}

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                            const vendor_header *const vhdr,
                            const image_header *const hdr) {
  MSG_RECV_INIT(Initialize);
  MSG_RECV(Initialize);
  send_msg_features(iface_num, vhdr, hdr);
}

void process_msg_GetFeatures(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                             const vendor_header *const vhdr,
                             const image_header *const hdr) {
  MSG_RECV_INIT(GetFeatures);
  MSG_RECV(GetFeatures);
  send_msg_features(iface_num, vhdr, hdr);
}

void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf) {
  MSG_RECV_INIT(Ping);
  MSG_RECV(Ping);

  MSG_SEND_INIT(Success);
  MSG_SEND_ASSIGN_STRING(message, msg_recv.message);
  MSG_SEND(Success);
}

static uint32_t firmware_remaining, firmware_block, chunk_requested;

void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf) {
  firmware_remaining = 0;
  firmware_block = 0;
  chunk_requested = 0;

  MSG_RECV_INIT(FirmwareErase);
  MSG_RECV(FirmwareErase);

  firmware_remaining = msg_recv.has_length ? msg_recv.length : 0;
  if ((firmware_remaining > 0) &&
      ((firmware_remaining % sizeof(uint32_t)) == 0) &&
      (firmware_remaining <= (FIRMWARE_SECTORS_COUNT * IMAGE_CHUNK_SIZE))) {
    // request new firmware
    chunk_requested = (firmware_remaining > IMAGE_INIT_CHUNK_SIZE)
                          ? IMAGE_INIT_CHUNK_SIZE
                          : firmware_remaining;
    MSG_SEND_INIT(FirmwareRequest);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, 0);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
    MSG_SEND(FirmwareRequest);
  } else {
    // invalid firmware size
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Wrong firmware size");
    MSG_SEND(Failure);
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
          250 + 750 * (firmware_block * IMAGE_CHUNK_SIZE + chunk_written) /
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

secbool check_vendor_header_keys(const vendor_header *const vhdr);

static int version_compare(uint32_t vera, uint32_t verb) {
  int a, b;
  a = vera & 0xFF;
  b = verb & 0xFF;
  if (a != b) return a - b;
  a = (vera >> 8) & 0xFF;
  b = (verb >> 8) & 0xFF;
  if (a != b) return a - b;
  a = (vera >> 16) & 0xFF;
  b = (verb >> 16) & 0xFF;
  if (a != b) return a - b;
  a = (vera >> 24) & 0xFF;
  b = (verb >> 24) & 0xFF;
  return a - b;
}

static void detect_installation(const vendor_header *current_vhdr,
                                const image_header *current_hdr,
                                const vendor_header *const new_vhdr,
                                const image_header *const new_hdr,
                                secbool *is_new, secbool *is_upgrade,
                                secbool *is_newvendor) {
  *is_new = secfalse;
  *is_upgrade = secfalse;
  *is_newvendor = secfalse;
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
  *is_upgrade = sectrue;
}

static int firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;
static size_t headers_offset = 0;
static size_t read_offset = 0;

int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf) {
  MSG_RECV_INIT(FirmwareUpload);
  MSG_RECV_CALLBACK(payload, _read_payload, read_offset);
  const secbool r = MSG_RECV(FirmwareUpload);

  if (sectrue != r || chunk_size != (chunk_requested + read_offset)) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Invalid chunk size");
    MSG_SEND(Failure);
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
        MSG_SEND(Failure);
        return UPLOAD_ERR_INVALID_VENDOR_HEADER;
      }

      if (sectrue != check_vendor_header_keys(&vhdr)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid vendor header signature");
        MSG_SEND(Failure);
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
        MSG_SEND(Failure);
        return UPLOAD_ERR_INVALID_IMAGE_HEADER;
      }

      if (sectrue != check_image_model(received_hdr)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Wrong firmware model");
        MSG_SEND(Failure);
        return UPLOAD_ERR_INVALID_IMAGE_MODEL;
      }

      if (sectrue != check_image_header_sig(received_hdr, vhdr.vsig_m,
                                            vhdr.vsig_n, vhdr.vpub)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid firmware signature");
        MSG_SEND(Failure);
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
      if (is_new == secfalse) {
        detect_installation(&current_vhdr, current_hdr, &vhdr, &hdr, &is_new,
                            &should_keep_seed, &is_newvendor);
      }

      uint32_t response = INPUT_CANCEL;
      if (sectrue == is_new) {
        // new installation - auto confirm
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
        ensure(
            flash_erase_sectors(STORAGE_SECTORS, STORAGE_SECTORS_COUNT, NULL),
            NULL);
      }
      ensure(flash_erase_sectors(FIRMWARE_SECTORS, FIRMWARE_SECTORS_COUNT,
                                 ui_screen_install_progress_erase),
             NULL);

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
      MSG_SEND(FirmwareRequest);

      firmware_remaining -= read_offset;
      return (int)firmware_remaining;
    } else {
      // first block with the headers parsed -> the first chunk is now complete
      read_offset = 0;
    }
  }

  // should not happen, but double-check
  if (firmware_block >= FIRMWARE_SECTORS_COUNT) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Firmware too big");
    MSG_SEND(Failure);
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
      MSG_SEND(FirmwareRequest);
      return (int)firmware_remaining;
    }

    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Invalid chunk hash");
    MSG_SEND(Failure);
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

  ensure(flash_unlock_write(), NULL);

  const uint32_t *const src = (const uint32_t *const)CHUNK_BUFFER_PTR;
  for (int i = 0; i < chunk_size / sizeof(uint32_t); i++) {
    ensure(flash_write_word(FIRMWARE_SECTORS[firmware_block],
                            i * sizeof(uint32_t), src[i]),
           NULL);
  }

  ensure(flash_lock_write(), NULL);

  headers_offset = 0;
  firmware_remaining -= chunk_requested;
  firmware_block++;
  firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;

  if (firmware_remaining > 0) {
    chunk_requested = (firmware_remaining > IMAGE_CHUNK_SIZE)
                          ? IMAGE_CHUNK_SIZE
                          : firmware_remaining;
    MSG_SEND_INIT(FirmwareRequest);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, firmware_block * IMAGE_CHUNK_SIZE);
    MSG_SEND_ASSIGN_REQUIRED_VALUE(length, chunk_requested);
    MSG_SEND(FirmwareRequest);
  } else {
    MSG_SEND_INIT(Success);
    MSG_SEND(Success);
  }
  return (int)firmware_remaining;
}

secbool bootloader_WipeDevice(void) {
  static const uint8_t sectors[] = {
      FLASH_SECTOR_STORAGE_1,
      FLASH_SECTOR_STORAGE_2,
      // 3,  // skip because of MPU protection
      FLASH_SECTOR_FIRMWARE_START,
      7,
      8,
      9,
      10,
      FLASH_SECTOR_FIRMWARE_END,
      FLASH_SECTOR_UNUSED_START,
      13,
      14,
      // FLASH_SECTOR_UNUSED_END,  // skip because of MPU protection
      FLASH_SECTOR_FIRMWARE_EXTRA_START,
      18,
      19,
      20,
      21,
      22,
      FLASH_SECTOR_FIRMWARE_EXTRA_END,
  };
  return flash_erase_sectors(sectors, sizeof(sectors), ui_screen_wipe_progress);
}

int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf) {
  secbool wipe_result = bootloader_WipeDevice();
  if (sectrue != wipe_result) {
    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
    MSG_SEND_ASSIGN_STRING(message, "Could not erase flash");
    MSG_SEND(Failure);
    return WIPE_ERR_CANNOT_ERASE;
  } else {
    MSG_SEND_INIT(Success);
    MSG_SEND(Success);
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
  MSG_SEND(Failure);
}
