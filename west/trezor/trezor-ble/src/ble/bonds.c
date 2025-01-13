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
#include <zephyr/bluetooth/conn.h>

#include <zephyr/logging/log.h>

#include "ble_internal.h"

#define LOG_MODULE_NAME ble_bonds
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#include "ble_internal.h"

bool bonds_erase_all(void) {
  int err = bt_unpair(BT_ID_DEFAULT, BT_ADDR_LE_ANY);
  if (err) {
    LOG_INF("Cannot delete bonds (err: %d)\n", err);
    return false;
  } else {
    bt_le_filter_accept_list_clear();
    LOG_INF("Bonds deleted successfully \n");
    return true;
  }
}

static void count_bonds(const struct bt_bond_info *info, void *user_data) {
  int *bond_cnt = (int *)user_data;
  *bond_cnt += 1;
}

int bonds_get_count(void) {
  int bond_cnt = 0;

  bt_foreach_bond(BT_ID_DEFAULT, count_bonds, &bond_cnt);

  return bond_cnt;
}

bool bonds_erase_current(void) {
  int err;
  struct bt_conn *current = connection_get_current();

  if (current == NULL) {
    return false;
  }

  struct bt_conn_info info;

  err = bt_conn_get_info(current, &info);
  if (err) {
    LOG_ERR("Failed to get connection info (err %d)", err);
    return false;
  }

  err = bt_unpair(BT_ID_DEFAULT, info.le.dst);

  return err == 0;
}
