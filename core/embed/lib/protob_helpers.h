#include <pb_decode.h>
#include <pb_encode.h>
#include <stdbool.h>
#include <stdint.h>
#include "secbool.h"

#define USB_PACKET_SIZE 64
#define MSG_HEADER1_LEN 9
#define MSG_HEADER2_LEN 1

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
#define MSG_SEND_CALLBACK(FIELD, CALLBACK, ARGUMENT) \
  {                                                  \
    msg_send.FIELD.funcs.encode = &CALLBACK;         \
    msg_send.FIELD.arg = (void *)ARGUMENT;           \
  }
#define MSG_SEND(TYPE, WRITE, WRITE_FLUSH)                                  \
  send_protob_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, \
                  &msg_send, WRITE, WRITE_FLUSH)

#define MSG_RECV_INIT(TYPE) TYPE msg_recv = TYPE##_init_default
#define MSG_RECV_CALLBACK(FIELD, CALLBACK, ARGUMENT) \
  {                                                  \
    msg_recv.FIELD.funcs.decode = &CALLBACK;         \
    msg_recv.FIELD.arg = (void *)ARGUMENT;           \
  }
#define MSG_RECV(TYPE, READ, READ_FLUSH, PACKET_SIZE)                       \
  recv_protob_msg(iface_num, msg_size, buf, TYPE##_fields, &msg_recv, READ, \
                  READ_FLUSH, PACKET_SIZE)

typedef struct {
  uint8_t iface_num;
  uint8_t packet_index;
  uint8_t packet_pos;
  uint8_t buf[USB_PACKET_SIZE];
} write_state;

typedef struct {
  uint8_t iface_num;
  uint8_t packet_index;
  uint8_t packet_pos;
  uint16_t packet_size;
  uint8_t *buf;
} read_state;

secbool send_protob_msg(uint8_t iface_num, uint16_t msg_id,
                        const pb_msgdesc_t *fields, const void *msg,
                        bool (*write_fnc)(pb_ostream_t *stream,
                                          const pb_byte_t *buf, size_t count),
                        void (*write_flush)(write_state *state));

secbool recv_protob_msg(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                        const pb_msgdesc_t *fields, void *msg,
                        bool (*read)(pb_istream_t *stream, pb_byte_t *buf,
                                     size_t count),
                        void (*read_flush)(read_state *state),
                        uint16_t packet_size);

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id,
                         uint32_t *msg_size);
