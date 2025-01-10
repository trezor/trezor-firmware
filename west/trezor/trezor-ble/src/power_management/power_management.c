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
#include <zephyr/sys/poweroff.h>

#include <trz_comm/trz_comm.h>

#define LOG_MODULE_NAME power_manangement
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(power_management_ok, 0, 1);

typedef enum {
  PWR_CMD_SYSTEM_OFF = 0x00,
} power_management_cmd_t;

void power_management_init(void) { k_sem_give(&power_management_ok); }

static void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  switch (cmd) {
    case PWR_CMD_SYSTEM_OFF:
      LOG_INF("System off");
      sys_poweroff();
      break;
    default:
      break;
  }
}

void power_management_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&power_management_ok, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_POWER_MANAGEMENT);
    process_command(buf->data, buf->len);
    k_free(buf);
  }
}

K_THREAD_DEFINE(power_management_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                power_management_thread, NULL, NULL, NULL, 7, 0, 0);
