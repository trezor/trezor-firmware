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

#include <stdint.h>

#include <trz_comm/trz_comm.h>

#define SPI_TX_DATA_LEN 244
#define MAX_UART_DATA_SIZE 64

void spi_init(void);

int uart_init(void);

bool spi_send(uint8_t service_id, const uint8_t *data, uint32_t len);

bool uart_send(uint8_t service_id, const uint8_t *tx_data, uint8_t len);

void process_rx_msg(uint8_t service_id, uint8_t *data, uint32_t len);
