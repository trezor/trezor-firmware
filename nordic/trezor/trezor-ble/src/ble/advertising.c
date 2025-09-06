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

#include <zephyr/kernel.h>
#include <zephyr/types.h>

#include <zephyr/bluetooth/bluetooth.h>

#include <zephyr/logging/log.h>

#include "ble_internal.h"

#define LOG_MODULE_NAME ble_advertising
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

#define ADV_FLAG_PAIRING 0x01
#define ADV_FLAG_BOND_MEM_FULL 0x02
#define ADV_FLAG_DEV_CONNECTED 0x04
#define ADV_FLAG_USER_DISCONNECT 0x08

#define ADV_INTERVAL_FAST_MIN_MS 20
#define ADV_INTERVAL_FAST_MAX_MS 25
#define ADV_INTERVAL_SLOW_MIN_MS 152.5
#define ADV_INTERVAL_SLOW_MAX_MS 211.25

#define ADV_INTERVAL_MS_TO_UNITS(x) ((int)(x / 0.625))

#define ADV_INTERVAL_FAST_MIN ADV_INTERVAL_MS_TO_UNITS(ADV_INTERVAL_FAST_MIN_MS)
#define ADV_INTERVAL_FAST_MAX ADV_INTERVAL_MS_TO_UNITS(ADV_INTERVAL_FAST_MAX_MS)
#define ADV_INTERVAL_SLOW_MIN ADV_INTERVAL_MS_TO_UNITS(ADV_INTERVAL_SLOW_MIN_MS)
#define ADV_INTERVAL_SLOW_MAX ADV_INTERVAL_MS_TO_UNITS(ADV_INTERVAL_SLOW_MAX_MS)

bool advertising = false;
bool advertising_wl = false;

// Add mutex for synchronization
static K_MUTEX_DEFINE(adv_mutex);

uint32_t adv_options = 0;
uint8_t manufacturer_data[8] = {0x29, 0x0F, 0, 0, 0, 0, 0, 0};

static struct bt_data advertising_data[2];

static const struct bt_data scan_response_data[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_TRZ_VAL),
    BT_DATA(BT_DATA_MANUFACTURER_DATA, manufacturer_data, 8),
};

static void change_adv_work_handler(struct k_work *work);
static void change_adv_interval_handler(struct k_timer *timer_id);
K_TIMER_DEFINE(change_adv_timer, change_adv_interval_handler, NULL);
static K_WORK_DEFINE(change_adv_work, change_adv_work_handler);

static void change_adv_interval_handler(struct k_timer *timer_id) {
  // This is safe to do in an ISR
  k_work_submit(&change_adv_work);
}

static void add_to_whitelist(const struct bt_bond_info *info, void *user_data) {
  char addr[BT_ADDR_LE_STR_LEN];
  bt_addr_le_to_str(&info->addr, addr, sizeof(addr));

  int err = bt_le_filter_accept_list_add(&info->addr);
  if (err) {
    LOG_WRN("whitelist add: %s FAILED!\n", addr);
  } else {
    LOG_INF("whitelist add: %s\n", addr);
  }
}

void advertising_setup_wl(void) {
  bt_le_filter_accept_list_clear();
  bt_foreach_bond(BT_ID_DEFAULT, add_to_whitelist, NULL);
}

static void change_adv_work_handler(struct k_work *work) {
  k_mutex_lock(&adv_mutex, K_FOREVER);

  if (!advertising) {
    k_mutex_unlock(&adv_mutex);
    return;
  }

  int err;
  LOG_INF("30s timer expired. Switching to slow advertising interval (%d ms).",
          ADV_INTERVAL_SLOW_MIN);

  // Stop current advertising
  err = bt_le_adv_stop();
  if (err) {
    LOG_ERR("Failed to stop advertising (err %d)", err);
    k_mutex_unlock(&adv_mutex);
    return;
  }

  // Restart advertising with new parameters
  err = bt_le_adv_start(BT_LE_ADV_PARAM(adv_options, ADV_INTERVAL_SLOW_MIN,
                                        ADV_INTERVAL_SLOW_MAX, NULL),
                        advertising_data, ARRAY_SIZE(advertising_data),
                        scan_response_data, ARRAY_SIZE(scan_response_data));

  if (err) {
    LOG_ERR("Failed to restart advertising with slow interval (err %d)", err);
  } else {
    LOG_INF("Successfully restarted advertising with slow interval.");
  }

  k_mutex_unlock(&adv_mutex);
}

void advertising_start(bool wl, bool user_disconnect, uint8_t color,
                       uint8_t device_code, bool static_addr, char *name,
                       int name_len) {
  k_mutex_lock(&adv_mutex, K_FOREVER);

  if (advertising) {
    LOG_WRN("Restarting advertising");
    k_timer_stop(&change_adv_timer);
    bt_le_adv_stop();
  }
  int err;

  if (name == NULL || name_len == 0) {
    name = DEVICE_NAME;
    name_len = DEVICE_NAME_LEN;
  }

  int bonds_count = bonds_get_count();

  manufacturer_data[2] = 0;

  if (CONFIG_BT_MAX_PAIRED == bonds_count) {
    manufacturer_data[2] |= ADV_FLAG_BOND_MEM_FULL;
  }
  if (connection_is_connected()) {
    manufacturer_data[2] |= ADV_FLAG_DEV_CONNECTED;
  }
  if (user_disconnect) {
    manufacturer_data[2] |= ADV_FLAG_USER_DISCONNECT;
  }

  manufacturer_data[3] = color;
  manufacturer_data[4] = device_code;

  advertising_data[0].type = BT_DATA_FLAGS;
  advertising_data[0].data_len = 1;
  static const uint8_t flags = (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR);
  advertising_data[0].data = &flags;

  /* Fill second element for the name */
  advertising_data[1].type = BT_DATA_NAME_COMPLETE;
  advertising_data[1].data_len = name_len;
  advertising_data[1].data = (const uint8_t *)name;

  char gap_name[BLE_ADV_NAME_LEN + 1] = {0};
  memcpy(gap_name, name, name_len);

  bt_set_name(gap_name);

  if (wl) {
    advertising_setup_wl();
    LOG_INF("Advertising with whitelist");

    uint32_t options = BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_SCANNABLE |
                       BT_LE_ADV_OPT_FILTER_CONN |
                       BT_LE_ADV_OPT_FILTER_SCAN_REQ;
    if (static_addr) {
      LOG_ERR("Advertising with static ADDR");
      options |= BT_LE_ADV_OPT_USE_IDENTITY;
    }

    adv_options = options;

    err = bt_le_adv_start(BT_LE_ADV_PARAM(options, ADV_INTERVAL_FAST_MIN,
                                          ADV_INTERVAL_FAST_MAX, NULL),
                          advertising_data, ARRAY_SIZE(advertising_data),
                          scan_response_data, ARRAY_SIZE(scan_response_data));
  } else {
    LOG_INF("Advertising no whitelist");

    manufacturer_data[2] |= ADV_FLAG_PAIRING;

    uint32_t options = BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_SCANNABLE;
    if (static_addr) {
      LOG_ERR("Advertising with static ADDR");
      options |= BT_LE_ADV_OPT_USE_IDENTITY;
    }

    adv_options = options;

    err = bt_le_adv_start(BT_LE_ADV_PARAM(options, ADV_INTERVAL_FAST_MIN,
                                          ADV_INTERVAL_FAST_MAX, NULL),
                          advertising_data, ARRAY_SIZE(advertising_data),
                          scan_response_data, ARRAY_SIZE(scan_response_data));
  }
  if (err) {
    LOG_ERR("Advertising failed to start (err %d)", err);
    ble_management_send_status_event();
    k_mutex_unlock(&adv_mutex);
    return;
  }
  advertising = true;
  advertising_wl = wl;

  k_timer_start(&change_adv_timer, K_SECONDS(30), K_NO_WAIT);
  LOG_INF("Started 30-second timer to switch advertising interval.");

  ble_management_send_status_event();
  k_mutex_unlock(&adv_mutex);
}

void advertising_stop(void) {
  k_mutex_lock(&adv_mutex, K_FOREVER);

  if (!advertising) {
    LOG_WRN("Not advertising");
    ble_management_send_status_event();
    k_mutex_unlock(&adv_mutex);
    return;
  }

  // Stop the timer first to prevent work handler from running
  k_timer_stop(&change_adv_timer);

  int err = bt_le_adv_stop();
  if (err) {
    LOG_ERR("Advertising failed to stop (err %d)", err);
    ble_management_send_status_event();
    k_mutex_unlock(&adv_mutex);
    return;
  }
  advertising = false;
  advertising_wl = false;
  ble_management_send_status_event();
  k_mutex_unlock(&adv_mutex);
}

bool advertising_is_advertising(void) { return advertising; }

bool advertising_is_advertising_whitelist(void) { return advertising_wl; }

void advertising_init(void) {
  LOG_INF("Advertising init");
  advertising_setup_wl();
}

void advertising_get_mac(uint8_t *mac, uint16_t max_len) {
  bt_addr_le_t addr[CONFIG_BT_ID_MAX] = {0};
  size_t count = 0;

  // Get the first (default) identity address
  bt_id_get(addr, &count);

  struct bt_le_oob oob_data;
  bt_le_oob_get_local(BT_ID_DEFAULT, &oob_data);

  for (size_t i = 0; i < count; i++) {
    char addr_str[BT_ADDR_LE_STR_LEN];
    bt_addr_le_to_str(addr, addr_str, sizeof(addr_str));
    LOG_ERR("Current BT MAC Address: %s\n", addr_str);
  }

  char addr_str[BT_ADDR_LE_STR_LEN];
  bt_addr_le_to_str(&oob_data.addr, addr_str, sizeof(addr_str));
  LOG_ERR("Current BT MAC Address: %s\n", addr_str);

  LOG_ERR("Num of IDS: %d", count);

  memcpy(mac, oob_data.addr.a.val, max_len);
}
