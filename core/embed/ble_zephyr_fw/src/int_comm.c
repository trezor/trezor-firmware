

#include <stdint.h>
#include <stdbool.h>

#include <zephyr/types.h>
#include <zephyr/kernel.h>

#include <zephyr/logging/log.h>

#include "uart.h"
#include "int_comm_defs.h"
#include "connection.h"
#include "advertising.h"
#include "pb_comm.h"

#define LOG_MODULE_NAME fw_int_comm
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(int_comm_ok, 0, 1);



void send_packet(uint8_t message_type, const uint8_t *tx_data, uint16_t len) {
  uart_data_t *tx = k_malloc(sizeof(*tx));

  if (!tx) {
    LOG_WRN("Not able to allocate UART send data buffer");
    return;
  }

  tx->len = len + OVERHEAD_SIZE;

  tx->data[0] = message_type;
  tx->data[1] = (tx->len >> 8) & 0xFF;
  tx->data[2] = tx->len & 0xFF;
  memcpy(&tx->data[3], tx_data, len);
  tx->data[tx->len-1] = EOM;

  uart_send(tx);

}

void send_status_event(void) {
//  ble_version_t version = {0};
//
//  sd_ble_version_get(&version);

  event_status_msg_t msg = {0};
  msg.msg_id = INTERNAL_EVENT_STATUS;
  msg.connected = is_connected();
  msg.advertising = is_advertising();
  msg.advertising_whitelist = is_advertising_whitelist();
  msg.peer_count = advertising_get_bond_count();
  msg.sd_version_number = 0;
  msg.sd_company_id = 0;
  msg.sd_subversion_number = 0;
  msg.app_version = 0;
  msg.bld_version = 0;

  send_packet(INTERNAL_EVENT, (uint8_t *)&msg, sizeof(msg));
}


void send_success_event(void) {
  uint8_t tx_data[] = {
          INTERNAL_EVENT_SUCCESS,
  };
  send_packet(INTERNAL_EVENT, tx_data, sizeof(tx_data));
}

uint16_t get_message_type(const uint8_t *rx_data) {
  return (rx_data[3] << 8) | rx_data[4];
}


void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  switch (cmd) {
    case INTERNAL_CMD_SEND_STATE:
      send_status_event();
      break;
    case INTERNAL_CMD_ADVERTISING_ON:
      advertising_start(data[1] != 0);
      break;
    case INTERNAL_CMD_ADVERTISING_OFF:
      advertising_stop();
      break;
    case INTERNAL_CMD_ERASE_BONDS:
      erase_bonds();
      send_success_event();
      break;
    case INTERNAL_CMD_DISCONNECT:
      disconnect();
      send_success_event();
    case INTERNAL_CMD_ACK:
      pb_msg_ack();
      break;
    default:
      break;
  }
}


void int_comm_start(void)
{
  k_sem_give(&int_comm_ok);
}


void int_comm_thread(void)
{
  /* Don't go any further until BLE is initialized */
  k_sem_take(&int_comm_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to process */
    uart_data_t *buf = uart_get_data_int();

    process_command(buf->data, buf->len);

    k_free(buf);
  }
}

//K_THREAD_DEFINE(int_comm_thread_id, CONFIG_BT_NUS_THREAD_STACK_SIZE, int_comm_thread, NULL, NULL,
//        NULL, 7, 0, 0);
