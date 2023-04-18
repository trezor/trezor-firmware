
#include "int_comm.h"
#include "app_error.h"
#include "app_uart.h"
#include "ble_nus.h"
#include "messages.pb.h"
#include "nrf_drv_spi.h"
#include "nrf_log.h"
#include "protob_helpers.h"
#include "stdint.h"
#include "trezorhal/ble/int_comm_defs.h"

#define SPI_INSTANCE 0 /**< SPI instance index. */
#define SPI_SCK_PIN 26
#define SPI_MISO_PIN 30
#define SPI_MOSI_PIN 29
#define SPI_SS_PIN 31

static uint8_t m_uart_rx_data[BLE_NUS_MAX_DATA_LEN];
static uint8_t m_spi_tx_data[BLE_PACKET_SIZE];
static bool m_uart_rx_data_ready_internal = false;
static uint16_t *m_p_conn_handle = NULL;

BLE_NUS_DEF(m_nus,
            NRF_SDH_BLE_TOTAL_LINK_COUNT); /**< BLE NUS service instance. */

static const nrf_drv_spi_t spi =
    NRF_DRV_SPI_INSTANCE(SPI_INSTANCE);    /**< SPI instance. */
static volatile bool spi_xfer_done = true; /**< Flag used to indicate that SPI
                                       instance completed the transfer. */

/**
 * @brief SPI user event handler.
 * @param event
 */
void spi_event_handler(nrf_drv_spi_evt_t const *p_event, void *p_context) {
  spi_xfer_done = true;
  NRF_LOG_INFO("Transfer completed.");
}

void spi_init(void) {
  nrf_drv_spi_config_t spi_config = NRF_DRV_SPI_DEFAULT_CONFIG;
  spi_config.ss_pin = SPI_SS_PIN;
  spi_config.miso_pin = SPI_MISO_PIN;
  spi_config.mosi_pin = SPI_MOSI_PIN;
  spi_config.sck_pin = SPI_SCK_PIN;
  spi_config.frequency = NRF_DRV_SPI_FREQ_8M;
  APP_ERROR_CHECK(nrf_drv_spi_init(&spi, &spi_config, spi_event_handler, NULL));
}

void nus_init(uint16_t *p_conn_handle) {
  m_p_conn_handle = p_conn_handle;
  uint32_t err_code;

  ble_nus_init_t nus_init;

  memset(&nus_init, 0, sizeof(nus_init));

  nus_init.data_handler = nus_data_handler;

  err_code = ble_nus_init(&m_nus, &nus_init);
  APP_ERROR_CHECK(err_code);

  *p_conn_handle = BLE_CONN_HANDLE_INVALID;
}

void send_byte(uint8_t byte) {
  uint32_t err_code;

  do {
    err_code = app_uart_put(byte);
    if ((err_code != NRF_SUCCESS) && (err_code != NRF_ERROR_BUSY)) {
      NRF_LOG_ERROR("Failed receiving NUS message. Error 0x%x. ", err_code);
    }
  } while (err_code == NRF_ERROR_BUSY);
}

void send_packet(uint8_t message_type, const uint8_t *tx_data, uint16_t len) {
  uint16_t total_len = len + OVERHEAD_SIZE;
  send_byte(message_type);
  send_byte((total_len >> 8) & 0xFF);
  send_byte(total_len & 0xFF);
  for (uint32_t i = 0; i < len; i++) {
    send_byte(tx_data[i]);
  }
  send_byte(EOM);
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

      while (!m_uart_rx_data_ready_internal)
        ;
      m_uart_rx_data_ready_internal = false;
      memcpy(state->buf, m_uart_rx_data, USB_PACKET_SIZE);

      // prepare next packet
      state->packet_index++;
      state->packet_pos = MSG_HEADER2_LEN;
    }
  }

  return true;
}

static void read_flush(read_state *state) { (void)state; }

#define MSG_SEND_NRF(msg) (MSG_SEND(msg, write, write_flush))

void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  switch (cmd) {
    case INTERNAL_CMD_SEND_STATE:
      if (*m_p_conn_handle != BLE_CONN_HANDLE_INVALID) {
        send_connected_event();
      } else {
        send_disconnected_event();
      }
      break;
    default:
      break;
  }
}

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
  while (!m_uart_rx_data_ready_internal)
    ;

  m_uart_rx_data_ready_internal = false;

  uint16_t id = 0;
  uint32_t msg_size = 0;

  msg_parse_header(m_uart_rx_data, &id, &msg_size);

  if (id == expected) {
    return process(m_uart_rx_data, msg_size, msg_recv);
  } else {
    process_unexpected(m_uart_rx_data, msg_size);
  }
  return secfalse;
}

/**@brief   Function for handling app_uart events.
 *
 * @details This function will receive a single character from the app_uart
 * module and append it to a string. The string will be be sent over BLE when
 * the last character received was a 'new line' '\n' (hex 0x0A) or if the string
 * has reached the maximum data length.
 */
/**@snippet [Handling the data received over UART] */
void uart_event_handle(app_uart_evt_t *p_event) {
  static uint8_t index = 0;
  static uint8_t message_type = 0;
  static uint16_t len = 0;
  uint32_t err_code;
  uint8_t rx_byte = 0;

  switch (p_event->evt_type) {
    case APP_UART_DATA_READY:
      while (app_uart_get(&rx_byte) == NRF_SUCCESS) {
        if (index == 0) {
          if (rx_byte == INTERNAL_MESSAGE || rx_byte == INTERNAL_EVENT ||
              rx_byte == EXTERNAL_MESSAGE) {
            message_type = rx_byte;
            index += 1;
            continue;
          } else {
            // unknown message
            continue;
          }
        }

        if (index == 1) {
          // len HI
          len = rx_byte << 8;
          index += 1;
          continue;
        }

        if (index == 2) {
          // len LO
          len |= rx_byte;
          index += 1;
          if (len > sizeof(m_uart_rx_data) + OVERHEAD_SIZE) {
            // message too long
            index = 0;
            continue;
          }
          continue;
        }

        if (index < (len - 1)) {
          // command
          m_uart_rx_data[index - COMM_HEADER_SIZE] = rx_byte;
          index += 1;
          continue;
        }

        if (index >= (len - 1)) {
          if (rx_byte == EOM) {
            if (message_type == EXTERNAL_MESSAGE) {
              NRF_LOG_DEBUG("Ready to send data over BLE NUS");
              NRF_LOG_HEXDUMP_DEBUG(m_uart_rx_data, index);

              do {
                uint16_t length = (uint16_t)len - OVERHEAD_SIZE;
                err_code = ble_nus_data_send(&m_nus, m_uart_rx_data, &length,
                                             *m_p_conn_handle);
                if ((err_code != NRF_ERROR_INVALID_STATE) &&
                    (err_code != NRF_ERROR_RESOURCES) &&
                    (err_code != NRF_ERROR_NOT_FOUND)) {
                  APP_ERROR_CHECK(err_code);
                }
              } while (err_code == NRF_ERROR_RESOURCES);
            } else if (message_type == INTERNAL_MESSAGE) {
              m_uart_rx_data_ready_internal = true;
            } else if (message_type == INTERNAL_EVENT) {
              process_command(m_uart_rx_data, len - OVERHEAD_SIZE);
            }
          }
          index = 0;
        }
      }
      break;
    default:
      break;
  }
}
/**@snippet [Handling the data received over UART] */

/**@brief Function for handling the data from the Nordic UART Service.
 *
 * @details This function will process the data received from the Nordic UART
 * BLE Service and forward it to Trezor
 *
 * @param[in] p_evt       Nordic UART Service event.
 */
/**@snippet [Handling the data received over BLE] */
void nus_data_handler(ble_nus_evt_t *p_evt) {
  if (p_evt->type == BLE_NUS_EVT_RX_DATA) {
    NRF_LOG_DEBUG("Received data from BLE NUS. Forwarding.");
    NRF_LOG_HEXDUMP_DEBUG(p_evt->params.rx_data.p_data,
                          p_evt->params.rx_data.length);

    if (p_evt->params.rx_data.length != BLE_PACKET_SIZE) {
      return;
    }

    while (!spi_xfer_done)
      ;
    spi_xfer_done = false;

    memcpy(m_spi_tx_data, p_evt->params.rx_data.p_data, BLE_PACKET_SIZE);

    nrf_drv_spi_transfer(&spi, m_spi_tx_data, BLE_PACKET_SIZE, NULL, 0);
  }
}
/**@snippet [Handling the data received over BLE] */

void send_connected_event(void) {
  uint8_t tx_data[] = {
      INTERNAL_EVENT_CONNECTED,
  };
  send_packet(INTERNAL_EVENT, tx_data, sizeof(tx_data));
}

void send_disconnected_event(void) {
  uint8_t tx_data[] = {
      INTERNAL_EVENT_DISCONNECTED,
  };
  send_packet(INTERNAL_EVENT, tx_data, sizeof(tx_data));
}

uint16_t get_message_type(const uint8_t *rx_data) {
  return (rx_data[3] << 8) | rx_data[4];
}

#define AUTHKEY_LEN (6)

static bool read_authkey(pb_istream_t *stream, const pb_field_t *field,
                         void **arg) {
  uint8_t *key_buffer = (uint8_t *)(*arg);

  if (stream->bytes_left > AUTHKEY_LEN) {
    return false;
  }

  memset(key_buffer, 0, AUTHKEY_LEN);

  while (stream->bytes_left) {
    // read data
    if (!pb_read(stream, (pb_byte_t *)(key_buffer),
                 (stream->bytes_left > AUTHKEY_LEN) ? AUTHKEY_LEN
                                                    : stream->bytes_left)) {
      return false;
    }
  }

  return true;
}

bool send_auth_key_request(uint8_t *p_key, uint8_t p_key_len) {
  uint8_t iface_num = INTERNAL_MESSAGE;
  MSG_SEND_INIT(PairingRequest);
  MSG_SEND_NRF(PairingRequest);

  uint8_t buffer[AUTHKEY_LEN];
  MSG_RECV_INIT(AuthKey);
  MSG_RECV_CALLBACK(key, read_authkey, buffer);
  secbool result = await_response(MessageType_MessageType_AuthKey,
                                  process_auth_key, &msg_recv);

  if (result != sectrue) {
    return false;
  }

  memcpy(p_key, buffer, AUTHKEY_LEN > p_key_len ? p_key_len : AUTHKEY_LEN);

  return true;
}

bool send_repair_request(void) {
  uint8_t iface_num = INTERNAL_MESSAGE;
  MSG_SEND_INIT(RepairRequest);
  MSG_SEND_NRF(RepairRequest);

  MSG_RECV_INIT(Success);

  secbool result = await_response(MessageType_MessageType_Success,
                                  process_success, &msg_recv);

  return result == sectrue;
}

void send_initialized(void) {
  uint8_t tx_data[] = {
      INTERNAL_EVENT_INITIALIZED,
  };
  send_packet(INTERNAL_EVENT, tx_data, sizeof(tx_data));
}
