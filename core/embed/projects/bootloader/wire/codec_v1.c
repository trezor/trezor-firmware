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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <pb.h>
#include <pb_decode.h>
#include <pb_encode.h>
#include "memzero.h"

#include "codec_v1.h"

#define MSG_HEADER1_LEN 9
#define MSG_HEADER2_LEN 1

typedef struct {
  wire_iface_t *iface;

  uint8_t packet_pos;
  uint8_t buf[MAX_PACKET_SIZE];

} packet_write_state_t;

typedef struct {
  wire_iface_t *iface;
  uint8_t packet_pos;
  uint8_t *buf;
} packet_read_state_t;

secbool codec_parse_header(const uint8_t *buf, uint16_t *msg_id,
                           size_t *msg_size) {
  if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {
    return secfalse;
  }
  *msg_id = (buf[3] << 8) + buf[4];
  *msg_size = (buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
  return sectrue;
}

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool write(pb_ostream_t *stream, const pb_byte_t *buf, size_t count) {
  packet_write_state_t *state = (packet_write_state_t *)(stream->state);

  size_t tx_len = state->iface->tx_packet_size;
  uint8_t *tx_buf = state->buf;

  size_t written = 0;
  // while we have data left
  while (written < count) {
    size_t remaining = count - written;
    // if all remaining data fit into our packet
    if (state->packet_pos + remaining <= tx_len) {
      // append data from buf to state->buf
      memcpy(tx_buf + state->packet_pos, buf + written, remaining);
      // advance position
      state->packet_pos += remaining;
      // and return
      return true;
    } else {
      // append data that fits
      memcpy(tx_buf + state->packet_pos, buf + written,
             tx_len - state->packet_pos);
      written += tx_len - state->packet_pos;
      // send packet
      bool ok = state->iface->write(tx_buf, tx_len);
      ensure(sectrue * ok, NULL);
      // prepare new packet
      memzero(tx_buf, tx_len);
      tx_buf[0] = '?';
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void write_flush(packet_write_state_t *state) {
  size_t packet_size = state->iface->tx_packet_size;

  // if packet is not filled up completely
  if (state->packet_pos < packet_size) {
    // pad it with zeroes
    memzero(state->buf + state->packet_pos, packet_size - state->packet_pos);
  }
  // send packet
  bool ok = state->iface->write(state->buf, packet_size);
  ensure(sectrue * (ok), NULL);
}

secbool codec_send_msg(wire_iface_t *iface, uint16_t msg_id,
                       const pb_msgdesc_t *fields, const void *msg) {
  // determine message size by serializing it into a dummy stream
  pb_ostream_t sizestream = {.callback = NULL,
                             .state = NULL,
                             .max_size = SIZE_MAX,
                             .bytes_written = 0,
                             .errmsg = NULL};
  if (!pb_encode(&sizestream, fields, msg)) {
    return secfalse;
  }
  const uint32_t msg_size = sizestream.bytes_written;

  packet_write_state_t state = {
      .iface = iface,
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

  pb_ostream_t stream = {.callback = &write,
                         .state = &state,
                         .max_size = SIZE_MAX,
                         .bytes_written = 0,
                         .errmsg = NULL};

  if (!pb_encode(&stream, fields, msg)) {
    return secfalse;
  }

  write_flush(&state);

  return sectrue;
}

static void read_retry(wire_iface_t *iface, uint8_t *buf) {
  size_t packet_size = iface->rx_packet_size;

  for (int retry = 0;; retry++) {
    int r = iface->read(buf, packet_size);
    if (r != packet_size) {  // reading failed
      if (r == 0 && retry < 10) {
        // only timeout => let's try again
        continue;
      } else {
        iface->error();
      }
    }
    return;  // success
  }
}

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool read(pb_istream_t *stream, uint8_t *buf, size_t count) {
  packet_read_state_t *state = (packet_read_state_t *)(stream->state);

  size_t packet_size = state->iface->rx_packet_size;

  size_t read = 0;
  // while we have data left
  while (read < count) {
    size_t remaining = count - read;
    // if all remaining data fit into our packet
    if (state->packet_pos + remaining <= packet_size) {
      // append data from buf to state->buf
      memcpy(buf + read, state->buf + state->packet_pos, remaining);
      // advance position
      state->packet_pos += remaining;
      // and return
      return true;
    } else {
      // append data that fits
      memcpy(buf + read, state->buf + state->packet_pos,
             packet_size - state->packet_pos);
      read += packet_size - state->packet_pos;
      // read next packet (with retry)
      read_retry(state->iface, state->buf);
      // prepare next packet
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void read_flush(packet_read_state_t *state) { (void)state; }

secbool codec_recv_message(wire_iface_t *iface, uint32_t msg_size, uint8_t *buf,
                           const pb_msgdesc_t *fields, void *msg) {
  packet_read_state_t state = {
      .iface = iface, .packet_pos = MSG_HEADER1_LEN, .buf = buf};

  pb_istream_t stream = {.callback = &read,
                         .state = &state,
                         .bytes_left = msg_size,
                         .errmsg = NULL};

  if (!pb_decode_noinit(&stream, fields, msg)) {
    return secfalse;
  }

  read_flush(&state);

  return sectrue;
}

void codec_flush(wire_iface_t *iface, uint32_t msg_size, uint8_t *buf) {
  // consume remaining message
  int remaining_chunks = 0;

  size_t packet_size = iface->rx_packet_size;

  if (msg_size > (packet_size - MSG_HEADER1_LEN)) {
    // calculate how many blocks need to be read to drain the message (rounded
    // up to not leave any behind)
    remaining_chunks = (msg_size - (packet_size - MSG_HEADER1_LEN) +
                        ((packet_size - MSG_HEADER2_LEN) - 1)) /
                       (packet_size - MSG_HEADER2_LEN);
  }

  for (int i = 0; i < remaining_chunks; i++) {
    // read next packet (with retry)
    read_retry(iface, buf);
  }
}
