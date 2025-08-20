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

#include <string.h>

#define LOG_MODULE_NAME ble_bonds
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#include "ble_internal.h"

bool bonds_erase_all(void) {
  connection_disconnect();
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

  connection_disconnect();

  err = bt_unpair(BT_ID_DEFAULT, info.le.dst);

  return err == 0;
}

bool bonds_erase_device(const bt_addr_le_t *addr) {
  if (addr == NULL) {
    return false;
  }

  struct bt_conn *current = connection_get_current();

  bool erased = false;
  bt_addr_le_t target;

  // Copy MAC and try both address types (ignore the input type)
  memcpy(target.a.val, addr->a.val, BT_ADDR_SIZE);

  if (current != NULL) {
    struct bt_conn_info info;
    int err = bt_conn_get_info(current, &info);
    if (err == 0 &&
        memcmp(info.le.dst->a.val, target.a.val, BT_ADDR_SIZE) == 0) {
      // If the device is currently connected, disconnect it first
      connection_disconnect();
    }
  }

  target.type = BT_ADDR_LE_PUBLIC;
  if (bt_unpair(BT_ID_DEFAULT, &target) == 0) {
    erased = true;
  }

  target.type = BT_ADDR_LE_RANDOM;
  if (bt_unpair(BT_ID_DEFAULT, &target) == 0) {
    erased = true;
  }

  // Best-effort: remove from accept list for both types (ignore errors)
  target.type = BT_ADDR_LE_PUBLIC;
  (void)bt_le_filter_accept_list_remove(&target);
  target.type = BT_ADDR_LE_RANDOM;
  (void)bt_le_filter_accept_list_remove(&target);

  if (erased) {
    LOG_INF("Bond(s) deleted for device MAC");
  } else {
    LOG_INF("No bonds found for device MAC");
  }

  return erased;
}

typedef struct {
  bt_addr_le_t *addr_list;
  size_t max_count;
  size_t filled;
} bonds_ctx_t;

static void get_bonds(const struct bt_bond_info *info, void *user_data) {
  bonds_ctx_t *ctx = (bonds_ctx_t *)user_data;

  if (ctx == NULL) {
    return;
  }

  if ((ctx->filled < ctx->max_count) && (ctx->addr_list != NULL)) {
    bt_addr_le_t *dst = &ctx->addr_list[ctx->filled];
    // First byte: address type, next 6 bytes: MAC address
    dst->type = info->addr.type;
    memcpy(dst->a.val, info->addr.a.val, BT_ADDR_SIZE);
  }

  ctx->filled += 1;
}

size_t bonds_get_all(bt_addr_le_t *addr, size_t max_count) {
  // If no storage provided, just return total number of bonds
  if (addr == NULL || max_count == 0) {
    int total = 0;
    bt_foreach_bond(BT_ID_DEFAULT, count_bonds, &total);
    return total;
  }

  bonds_ctx_t ctx = {
      .addr_list = addr,
      .max_count = max_count,
      .filled = 0,
  };

  bt_foreach_bond(BT_ID_DEFAULT, get_bonds, &ctx);

  // Return how many entries were actually written (capped by max_count)
  if (ctx.filled > max_count) {
    return max_count;
  }
  return ctx.filled;
}
