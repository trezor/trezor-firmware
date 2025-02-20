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

#pragma once

#include <stdbool.h>
#include <zephyr/types.h>

#define PACKET_DATA_SIZE 246

typedef enum {
  NRF_SERVICE_BLE = 0,
  NRF_SERVICE_BLE_MANAGER = 1,
  NRF_SERVICE_MANAGEMENT = 2,
  NRF_SERVICE_PRODTEST = 3,

  NRF_SERVICE_CNT  // Number of services
} nrf_service_id_t;

typedef struct {
  void *fifo_reserved;
  uint8_t data[PACKET_DATA_SIZE];
  uint16_t len;
} trz_packet_t;

// Initialized the communication module
void trz_comm_init(void);

// Sends a message to the specified service over fitting communication channel
bool trz_comm_send_msg(nrf_service_id_t service, const uint8_t *data,
                       uint32_t len);

// Polls for incoming data from the specified service
trz_packet_t *trz_comm_poll_data(nrf_service_id_t service);
