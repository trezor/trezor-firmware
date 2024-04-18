
#include <zephyr/types.h>
#include <zephyr/kernel.h>

#include <dk_buttons_and_leds.h>

#include "protob/protob_helpers.h"
#include "protob/messages.pb.h"

#include "int_comm.h"
#include "int_comm_defs.h"
#include "uart.h"
#include "pb_comm.h"
#include "connection.h"



typedef struct {
    void *fifo_reserved;
    uint8_t cmd;
    uint8_t data[PB_BUF_SIZE];
    uint16_t len;
}pb_comm_data_t;


#define PASSKEY_LEN 6

static K_SEM_DEFINE(pb_comm_ok, 0, 1);
static K_SEM_DEFINE(pb_wait_for_ack, 0, 1);


static K_FIFO_DEFINE(fifo_pb_tx_in);  // data to send to trezor
static K_FIFO_DEFINE(fifo_pb_tx_out); // data to send to host


void prepare_response_wait() {
  k_sem_reset(&pb_wait_for_ack);
  uart_data_pb_flush();
}



bool write_resp(pb_ostream_t *stream, const pb_byte_t *buf, size_t count) {
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
      uart_data_t * buf = k_malloc(sizeof(uart_data_t));
      buf->len = USB_DATA_SIZE;
      memcpy(buf->data, state->buf, USB_DATA_SIZE);
      uart_send_ext(buf);

      // prepare new packet
      state->packet_index++;
      memset(state->buf, 0, USB_PACKET_SIZE);
      state->buf[0] = '?';
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
};

void write_resp_flush(write_state *state) {
  // if packet is not filled up completely
  if (state->packet_pos < USB_PACKET_SIZE) {
    // pad it with zeroes
    memset(state->buf + state->packet_pos, 0,
           USB_PACKET_SIZE - state->packet_pos);
  }
  // send packet
  uart_data_t * buf = k_malloc(sizeof(uart_data_t));
  buf->len = USB_DATA_SIZE;
  memcpy(buf->data, state->buf, USB_DATA_SIZE);
  uart_send_ext(buf);
}

bool write(pb_ostream_t *stream, const pb_byte_t *buf, size_t count) {
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
      send_packet(state->iface_num, state->buf, USB_PACKET_SIZE);

      // prepare new packet
      state->packet_index++;
      memset(state->buf, 0, USB_PACKET_SIZE);
      state->buf[0] = '?';
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
};

void write_flush(write_state *state) {
  // if packet is not filled up completely
  if (state->packet_pos < USB_PACKET_SIZE) {
    // pad it with zeroes
    memset(state->buf + state->packet_pos, 0,
           USB_PACKET_SIZE - state->packet_pos);
  }
  // send packet
  send_packet(state->iface_num, state->buf, USB_PACKET_SIZE);
}

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool read(pb_istream_t *stream, uint8_t *buf, size_t count) {
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

      // read next packet
      uart_data_t * data = uart_get_data_pb();
      if (data == NULL) {
        return false;
      }
      memcpy(state->buf, data->data, USB_PACKET_SIZE > data->len ? data->len : USB_PACKET_SIZE);
      k_free(data);

      // prepare next packet
      state->packet_index++;
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void read_flush(read_state *state) { (void)state; }

#define MSG_SEND_NRF(msg) (MSG_SEND(msg, write, write_flush))
#define MSG_SEND_NRF_RESPONSE(msg) (MSG_SEND(msg, write_resp, write_resp_flush))



secbool process_auth_key(uint8_t *data, uint32_t len, void *msg) {
  recv_protob_msg(INTERNAL_MESSAGE, len, data, AuthKey_fields, msg, read,
                  read_flush, USB_PACKET_SIZE);
  return sectrue;
}

secbool process_success(uint8_t *data, uint32_t len, void *msg) {
  recv_protob_msg(INTERNAL_MESSAGE, len, data, Success_fields, msg, read,
                  read_flush, USB_PACKET_SIZE);
  return sectrue;
}

void process_unexpected(uint8_t *data, uint32_t len) {}



secbool await_response(uint16_t expected,
                       secbool (*process)(uint8_t *data, uint32_t len,
                                          void *msg),
                       void *msg_recv) {

  if (k_sem_take(&pb_wait_for_ack, K_MSEC(100)) != 0) {
    return secfalse;
  }

  if ((dk_get_buttons() & DK_BTN2_MSK) == 0) {
    return secfalse;
  }

  uint16_t id = 0;
  uint32_t msg_size = 0;

  uart_data_t * data = uart_get_data_pb();
  while (data == NULL) {

    if ((dk_get_buttons() & DK_BTN2_MSK) == 0) {
      return secfalse;
    }

    data = uart_get_data_pb();
  }

  msg_parse_header(data->data, &id, &msg_size);

  if (id == expected) {
    if (process != NULL) {
      return process(data->data, msg_size, msg_recv);
    }
    return sectrue;
  } else {
    process_unexpected(data->data, msg_size);
  }
  return secfalse;
}



static bool read_authkey(pb_istream_t *stream, const pb_field_t *field,
                         void **arg) {
  uint8_t *key_buffer = (uint8_t *)(*arg);

  if (stream->bytes_left > PASSKEY_LEN) {
    return false;
  }

  memset(key_buffer, 0, PASSKEY_LEN);

  while (stream->bytes_left) {
    // read data
    if (!pb_read(stream, (pb_byte_t *)(key_buffer),
                 (stream->bytes_left > PASSKEY_LEN)
                 ? PASSKEY_LEN
                 : stream->bytes_left)) {
      return false;
    }
  }

  return true;
}

static bool write_authkey(pb_ostream_t *stream, const pb_field_t *field,
                          void *const *arg) {
  uint8_t *key = (uint8_t *)(*arg);
  if (!pb_encode_tag_for_field(stream, field)) return false;

  return pb_encode_string(stream, (uint8_t *)key, PASSKEY_LEN);
}

bool send_comparison_request(uint8_t *p_key, int8_t p_key_len) {
  prepare_response_wait();
  uint8_t iface_num = INTERNAL_MESSAGE;
  MSG_SEND_INIT(ComparisonRequest);
  MSG_SEND_CALLBACK(key, write_authkey, p_key);
  MSG_SEND_NRF(ComparisonRequest);

  MSG_RECV_INIT(Success);
  secbool result = await_response(MessageType_MessageType_Success,
                                  process_success, &msg_recv);

  if (result != sectrue) {
    return false;
  }

  return true;
}

bool send_auth_key_request(uint8_t *p_key, uint8_t p_key_len) {
  prepare_response_wait();
  uint8_t iface_num = INTERNAL_MESSAGE;
  MSG_SEND_INIT(PairingRequest);
  MSG_SEND_NRF(PairingRequest);

  uint8_t buffer[PASSKEY_LEN];
  MSG_RECV_INIT(AuthKey);
  MSG_RECV_CALLBACK(key, read_authkey, buffer);
  secbool result = await_response(MessageType_MessageType_AuthKey,
                                  process_auth_key, &msg_recv);

  if (result != sectrue) {
    return false;
  }

  memcpy(p_key, buffer,
         PASSKEY_LEN > p_key_len ? p_key_len : PASSKEY_LEN);

  return true;
}

bool send_repair_request(void) {
  prepare_response_wait();
  uint8_t iface_num = INTERNAL_MESSAGE;
  MSG_SEND_INIT(RepairRequest);
  MSG_SEND_NRF(RepairRequest);

  MSG_RECV_INIT(Success);

  secbool result = await_response(MessageType_MessageType_Success,
                                  process_success, &msg_recv);

  return result == sectrue;
}


void send_error_response(void) {
  // communication with trezor is disabled
  uint8_t iface_num = 0;

  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);

  msg_send.has_message = true;
  memset(msg_send.message, 0, sizeof(msg_send.message));
  const char msg[] = "Device Locked or Busy";
  strncpy(msg_send.message, msg, sizeof(msg_send.message) - 1);
  MSG_SEND_NRF_RESPONSE(Failure);

}



void pb_comm_start(void)
{
  k_sem_give(&pb_comm_ok);
}

void pb_comm_enqueue(uint8_t cmd, uint8_t * data, uint16_t len)
{
  pb_comm_data_t * buf = k_malloc(sizeof(pb_comm_data_t));
  buf->cmd = cmd;
  memcpy(buf->data, data, len);
  buf->len = len;
  k_fifo_put(&fifo_pb_tx_in, buf);
}


void pb_comm_thread(void)
{
  /* Don't go any further until BLE is initialized */
  k_sem_take(&pb_comm_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to process */
    pb_comm_data_t * buf = k_fifo_get(&fifo_pb_tx_in, K_FOREVER);

    switch(buf->cmd) {
      case COMPARISON_REQUEST:
        if (send_comparison_request(buf->data, buf->len)) {
          num_comp_reply(true);
        } else {
          num_comp_reply(false);
        }
        break;
    }

    k_free(buf);
  }
}

void pb_msg_ack(void) {
  k_sem_give(&pb_wait_for_ack);
}


K_THREAD_DEFINE(p_comm_thread_id, CONFIG_BT_NUS_THREAD_STACK_SIZE, pb_comm_thread, NULL, NULL,
        NULL, 7, 0, 0);
