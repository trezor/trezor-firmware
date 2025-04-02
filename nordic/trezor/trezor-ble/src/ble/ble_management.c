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

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/kernel.h>
#include <zephyr/types.h>

#include <zephyr/logging/log.h>
#include <zephyr/sys/crc.h>

#include "ble_internal.h"

#include <trz_comm/trz_comm.h>

#define LOG_MODULE_NAME ble_manangement
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(ble_management_ok, 0, 1);

void ble_management_send_status_event(void) {
  //  ble_version_t version = {0};
  //
  //  sd_ble_version_get(&version);
  LOG_WRN(
      "Sending status event: connected: %d, advertising: %d, "
      "advertising_whitelist: %d, peer_count: %d",
      connection_is_connected(), advertising_is_advertising(),
      advertising_is_advertising_whitelist(), bonds_get_count());

  event_status_msg_t msg = {0};
  msg.msg_id = INTERNAL_EVENT_STATUS;
  msg.connected = connection_is_connected();
  msg.advertising = advertising_is_advertising();
  msg.advertising_whitelist = advertising_is_advertising_whitelist();
  msg.peer_count = bonds_get_count();
  msg.sd_version_number = 0;
  msg.sd_company_id = 0;
  msg.sd_subversion_number = 0;
  msg.app_version = 0;
  msg.bld_version = 0;

  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, (uint8_t *)&msg, sizeof(msg));
}

static void management_send_success_event(void) {
  uint8_t tx_data[] = {
      INTERNAL_EVENT_SUCCESS,
  };
  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, tx_data, sizeof(tx_data));
}

static void management_send_failure_event(void) {
  uint8_t tx_data[] = {
      INTERNAL_EVENT_FAILURE,
  };
  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, tx_data, sizeof(tx_data));
}

void ble_management_send_pairing_cancelled_event(void) {
  uint8_t tx_data[1] = {0};

  tx_data[0] = INTERNAL_EVENT_PAIRING_CANCELLED;

  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, tx_data, sizeof(tx_data));
}

void ble_management_send_pairing_request_event(uint8_t *data, uint16_t len) {
  uint8_t tx_data[7] = {0};

  tx_data[0] = INTERNAL_EVENT_PAIRING_REQUEST;
  tx_data[1] = data[0];
  tx_data[2] = data[1];
  tx_data[3] = data[2];
  tx_data[4] = data[3];
  tx_data[5] = data[4];
  tx_data[6] = data[5];

  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, tx_data, sizeof(tx_data));
}

static void management_send_mac(uint8_t *mac) {
  uint8_t tx_data[1 + BT_ADDR_SIZE] = {0};
  tx_data[0] = INTERNAL_EVENT_MAC;
  memcpy(&tx_data[1], mac, BT_ADDR_SIZE);
  trz_comm_send_msg(NRF_SERVICE_BLE_MANAGER, tx_data, sizeof(tx_data));
}

static void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  bool success = true;
  bool send_response = true;
  switch (cmd) {
    case INTERNAL_CMD_SEND_STATE:
      send_response = false;
      ble_management_send_status_event();
      break;
    case INTERNAL_CMD_ADVERTISING_ON: {
      cmd_advertising_on_t *cmd = (cmd_advertising_on_t *)data;

      int name_len = strnlen(cmd->name, BLE_ADV_NAME_LEN);
      advertising_start(cmd->whitelist != 0, cmd->color, cmd->device_code,
                        cmd->static_addr, (char *)cmd->name, name_len);
    } break;
    case INTERNAL_CMD_ADVERTISING_OFF:
      advertising_stop();
      break;
    case INTERNAL_CMD_ERASE_BONDS:
      bonds_erase_all();
      break;
    case INTERNAL_CMD_DISCONNECT:
      connection_disconnect();
    case INTERNAL_CMD_ACK:
      // pb_msg_ack();
      break;
    case INTERNAL_CMD_ALLOW_PAIRING:
      cmd_allow_pairing_t *cmd = (cmd_allow_pairing_t *)data;

      pairing_num_comp_reply(true, cmd->code);
      break;
    case INTERNAL_CMD_REJECT_PAIRING:
      pairing_num_comp_reply(false, NULL);
      break;
    case INTERNAL_CMD_UNPAIR:
      success = bonds_erase_current();
      break;
    case INTERNAL_CMD_GET_MAC: {
      uint8_t mac[BT_ADDR_SIZE] = {0};
      advertising_get_mac(mac, BT_ADDR_SIZE);
      management_send_mac(mac);
      send_response = false;
    } break;
    default:
      break;
  }

  if (send_response) {
    if (success) {
      management_send_success_event();
    } else {
      management_send_failure_event();
    }
  }
}

void ble_management_init(void) { k_sem_give(&ble_management_ok); }

void ble_management_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&ble_management_ok, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_BLE_MANAGER);
    process_command(buf->data, buf->len);
    k_free(buf);
  }
}

K_THREAD_DEFINE(ble_management_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                ble_management_thread, NULL, NULL, NULL, 7, 0, 0);
