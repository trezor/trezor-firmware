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

#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/byteorder.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/hci_vs.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/settings/settings.h>

#include <app_version.h>

#include "ble_internal.h"

#define LOG_MODULE_NAME ble
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define STR_HELPER(x) #x
#define STR(x) STR_HELPER(x)

#define APP_VERSION_STR  \
  STR(APP_VERSION_MAJOR) \
  "." STR(APP_VERSION_MINOR) "." STR(APP_PATCHLEVEL) "." STR(APP_TWEAK)

static K_SEM_DEFINE(ble_init_ok, 0, 1);

atomic_t g_busy_flag = ATOMIC_INIT(0);

#if IS_ENABLED(CONFIG_BT_CTLR_TX_PWR_PLUS_4)
static int8_t g_act_tx_power_level = 4;
static int8_t g_set_tx_power_level = 4;
#else
static int8_t g_act_tx_power_level = 0;
static int8_t g_set_tx_power_level = 0;
#endif

static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data,
                          uint16_t len) {
  if (atomic_get(&g_busy_flag) != 0) {
    LOG_INF("Trezor not ready, rejecting data");
    service_send_busy();
    return;
  }

  char addr[BT_ADDR_LE_STR_LEN] = {0};

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, ARRAY_SIZE(addr));

  LOG_DBG("Received data from: %s, %d", addr, len);

  uint8_t data_copy[BLE_RX_PACKET_SIZE + 7] = {0};

  data_copy[0] = bt_conn_get_dst(conn)->type;
  memcpy(data_copy + 1, bt_conn_get_dst(conn)->a.val, BT_ADDR_SIZE);
  memcpy(data_copy + 1 + BT_ADDR_SIZE, data, len);

  trz_comm_send_msg(NRF_SERVICE_BLE, data_copy, len + 1 + BT_ADDR_SIZE);
}

bool ble_init(void) {
  int err = 0;

  connection_init();
  pairing_init();

  err = bt_enable(NULL);
  if (err) {
    return false;
  }

  if (IS_ENABLED(CONFIG_SETTINGS)) {
    settings_load();
  }

#if defined(CONFIG_BT_DIS_FW_REV)
  settings_runtime_set("bt/dis/fw", APP_VERSION_STR, sizeof(APP_VERSION_STR));
#endif
#if defined(CONFIG_BT_DIS_SW_REV)
  settings_runtime_set("bt/dis/sw", APP_VERSION_STR, sizeof(APP_VERSION_STR));
#endif

  err = service_init(bt_receive_cb);
  if (err) {
    LOG_ERR("Failed to initialize UART service (err: %d)", err);
    return 0;
  }

  advertising_init();
  ble_management_init();

  k_sem_give(&ble_init_ok);
  LOG_INF("Bluetooth initialized");

  ble_management_send_status_event();

  ble_management_send_battery_request();

  return true;
}

void ble_write_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&ble_init_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to be sent over bluetooth */
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_BLE);

    struct bt_conn *conn = connection_get_current();

    if (conn == NULL) {
      LOG_WRN("No active BLE connection, cannot send data");
      k_free(buf);
      return;
    }

    const bt_addr_le_t *addr = bt_conn_get_dst(conn);

    if (addr->type != buf->data[0] ||
        memcmp(addr->a.val, &buf->data[1], BT_ADDR_SIZE) != 0) {
      LOG_WRN("Address mismatch, cannot send data");
      k_free(buf);
      return;
    }

    trz_packet_t *data_to_send = k_malloc(sizeof(*data_to_send));
    data_to_send->len = buf->len - 1 - BT_ADDR_SIZE;
    memcpy(data_to_send->data, &buf->data[1 + BT_ADDR_SIZE], data_to_send->len);
    k_free(buf);

    if (service_send(conn, data_to_send)) {
      LOG_WRN("Failed to send data over BLE connection: %d", data_to_send->len);
      k_free(data_to_send);
    }

    LOG_DBG("Freeing UART data");
  }
}

void ble_set_busy_flag(uint8_t flag) { atomic_set(&g_busy_flag, flag); }

uint8_t ble_get_busy_flag(void) { return atomic_get(&g_busy_flag); }

static int ble_configure_tx_power(int8_t tx_power_level, struct bt_conn *conn) {
  struct bt_hci_cp_vs_write_tx_power_level *cp;
  struct bt_hci_rp_vs_write_tx_power_level *rp;
  struct net_buf *buf, *rsp = NULL;
  int err;

  buf = bt_hci_cmd_create(BT_HCI_OP_VS_WRITE_TX_POWER_LEVEL, sizeof(*cp));
  if (!buf) {
    LOG_ERR("Unable to allocate command buffer for TX power");
    return -ENOMEM;
  }

  cp = net_buf_add(buf, sizeof(*cp));

  if (conn == NULL) {
    // No connection, set for advertising
    cp->handle = sys_cpu_to_le16(0);                 // Handle 0 for advertising
    cp->handle_type = BT_HCI_VS_LL_HANDLE_TYPE_ADV;  // Advertising handle type
  } else {
    uint16_t handle = 0;
    bt_hci_get_conn_handle(conn, &handle);
    cp->handle = handle;                              // Connection handle
    cp->handle_type = BT_HCI_VS_LL_HANDLE_TYPE_CONN;  // Connection handle type
  }
  cp->tx_power_level = tx_power_level;

  err = bt_hci_cmd_send_sync(BT_HCI_OP_VS_WRITE_TX_POWER_LEVEL, buf, &rsp);
  if (err) {
    LOG_ERR("Set TX power failed: %d", err);
    return err;
  }

  if (rsp) {
    rp = (void *)rsp->data;
    LOG_INF("Actual TX Power set to: %d dBm", rp->selected_tx_power);
    net_buf_unref(rsp);
    g_act_tx_power_level = rp->selected_tx_power;
  }
  return 0;
}

int8_t ble_get_tx_power(void) { return g_act_tx_power_level; }

int ble_set_tx_power(int8_t tx_power_level) {
  g_set_tx_power_level = tx_power_level;

  int8_t res = ble_configure_tx_power(tx_power_level, NULL);

  struct bt_conn *conn = connection_get_current();

  if (conn != NULL) {
    return ble_configure_tx_power(tx_power_level, conn);
  }
  return res;
}

int ble_reconfigure_tx_power(void) {
  struct bt_conn *conn = connection_get_current();

  if (conn != NULL) {
    return ble_configure_tx_power(g_set_tx_power_level, conn);
  }

  return -1;
}

K_THREAD_DEFINE(ble_write_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                ble_write_thread, NULL, NULL, NULL, 7, 0, 0);
