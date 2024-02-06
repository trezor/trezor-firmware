

#include "protob_helpers.h"

secbool send_protob_msg(uint8_t iface_num, uint16_t msg_id,
                        const pb_msgdesc_t *fields, const void *msg,
                        bool (*write)(pb_ostream_t *stream,
                                      const pb_byte_t *buf, size_t count),
                        void (*write_flush)(write_state *state)) {
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

  write_state state = {
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

  pb_ostream_t stream = {.callback = write,
                         .state = &state,
                         .max_size = SIZE_MAX,
                         .bytes_written = 0,
                         .errmsg = NULL};

  if (false == pb_encode(&stream, fields, msg)) {
    return secfalse;
  }

  write_flush(&state);
  return secfalse;
}

secbool recv_protob_msg(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                        const pb_msgdesc_t *fields, void *msg,
                        bool (*read)(pb_istream_t *stream, pb_byte_t *buf,
                                     size_t count),
                        void (*read_flush)(read_state *state),
                        uint16_t packet_size) {
  read_state state = {.iface_num = iface_num,
                      .packet_index = 0,
                      .packet_pos = MSG_HEADER1_LEN,
                      .packet_size = packet_size,
                      .buf = buf};

  pb_istream_t stream = {.callback = read,
                         .state = &state,
                         .bytes_left = msg_size,
                         .errmsg = NULL};

  if (false == pb_decode_noinit(&stream, fields, msg)) {
    return secfalse;
  }

  read_flush(&state);

  return sectrue;
}

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id,
                         uint32_t *msg_size) {
  if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {
    return secfalse;
  }
  *msg_id = (buf[3] << 8) + buf[4];
  *msg_size = (buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
  return sectrue;
}
