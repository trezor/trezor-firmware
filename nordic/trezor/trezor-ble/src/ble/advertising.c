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

bool advertising = false;
bool advertising_wl = false;

uint8_t manufacturer_data[8] = {0xff, 0xff, 0, 0, 'T', '3', 'W', '1'};

static struct bt_data advertising_data[2];

static const struct bt_data scan_response_data[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_TRZ_VAL),
    BT_DATA(BT_DATA_MANUFACTURER_DATA, manufacturer_data, 8),
};

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

void advertising_start(bool wl, uint8_t color, char *name, int name_len) {
  if (advertising) {
    LOG_WRN("Restarting advertising");
    bt_le_adv_stop();
  }
  int err;

  if (name == NULL || name_len == 0) {
    name = DEVICE_NAME;
    name_len = DEVICE_NAME_LEN;
  }

  manufacturer_data[3] = color;

  advertising_data[0].type = BT_DATA_FLAGS;
  advertising_data[0].data_len = 1;
  static const uint8_t flags = (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR);
  advertising_data[0].data = &flags;

  /* Fill second element for the name */
  advertising_data[1].type = BT_DATA_NAME_COMPLETE;
  advertising_data[1].data_len = name_len;
  advertising_data[1].data = (const uint8_t *)name;

  char gap_name[21] = {0};
  memcpy(gap_name, name, name_len);

  bt_set_name(gap_name);

  if (wl) {
    advertising_setup_wl();
    LOG_INF("Advertising with whitelist");

    manufacturer_data[2] = 0x00;

    err = bt_le_adv_start(
        BT_LE_ADV_PARAM(BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_SCANNABLE |
                            BT_LE_ADV_OPT_FILTER_CONN |
                            BT_LE_ADV_OPT_FILTER_SCAN_REQ,
                        160, 1600, NULL),
        advertising_data, ARRAY_SIZE(advertising_data), scan_response_data,
        ARRAY_SIZE(scan_response_data));
  } else {
    LOG_INF("Advertising no whitelist");

    manufacturer_data[2] = 0x01;

    err = bt_le_adv_start(
        BT_LE_ADV_PARAM(BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_SCANNABLE,
                        160, 1600, NULL),
        advertising_data, ARRAY_SIZE(advertising_data), scan_response_data,
        ARRAY_SIZE(scan_response_data));
  }
  if (err) {
    LOG_ERR("Advertising failed to start (err %d)", err);
    management_send_status_event();
    return;
  }
  advertising = true;
  advertising_wl = wl;

  management_send_status_event();
}

void advertising_stop(void) {
  if (!advertising) {
    LOG_WRN("Not advertising");

    management_send_status_event();
    return;
  }

  int err = bt_le_adv_stop();
  if (err) {
    LOG_ERR("Advertising failed to stop (err %d)", err);
    management_send_status_event();
    return;
  }
  advertising = false;
  advertising_wl = false;
  management_send_status_event();
}

bool advertising_is_advertising(void) { return advertising; }

bool advertising_is_advertising_whitelist(void) { return advertising_wl; }

void advertising_init(void) {
  LOG_INF("Advertising init");
  advertising_setup_wl();
}
