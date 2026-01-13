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

#include <trezor_types.h>

#include <io/nrf.h>
#include <io/tsqueue.h>
#include <sys/systimer.h>

#define TX_QUEUE_SIZE (8)

#define MAX_SPI_DATA_SIZE (251)

typedef enum {
  MGMT_CMD_SYSTEM_OFF = 0x00,
  MGMT_CMD_INFO = 0x01,
  MGMT_CMD_START_UART = 0x02,
  MGMT_CMD_STOP_UART = 0x03,
  MGMT_CMD_SUSPEND = 0x04,
  MGMT_CMD_RESUME = 0x05,
  MGMT_CMD_AUTH_CHALLENGE = 0x06,
} management_cmd_t;

typedef enum {
  MGMT_RESP_INFO = 0,
  MGMT_RESP_AUTH_RESPONSE = 1,
} management_resp_t;

typedef struct {
  uint8_t service_id;
  uint8_t msg_len;
  uint8_t data[MAX_SPI_DATA_SIZE];
  uint8_t crc;
} spi_packet_t;

typedef struct {
  spi_packet_t packet;
  nrf_tx_callback_t callback;
  void *context;
} nrf_tx_request_t;

typedef struct {
  UART_HandleTypeDef urt;
  DMA_HandleTypeDef urt_tx_dma;

  uint8_t tx_buffers[TX_QUEUE_SIZE][sizeof(nrf_tx_request_t)];
  tsqueue_entry_t tx_queue_entries[TX_QUEUE_SIZE];
  tsqueue_t tx_queue;
  nrf_tx_request_t tx_request;
  int32_t tx_request_id;

  uint8_t urt_rx_byte;
  uint8_t urt_tx_byte;
  bool urt_tx_complete;
  bool urt_rx_complete;

  SPI_HandleTypeDef spi;
  DMA_HandleTypeDef spi_rx_dma;
  DMA_HandleTypeDef spi_tx_dma;
  spi_packet_t long_rx_buffer;

  EXTI_HandleTypeDef exti;

  bool comm_running;
  bool initialized;
  bool wakeup;

  nrf_rx_callback_t service_listeners[NRF_SERVICE_CNT];

  bool info_valid;
  nrf_info_t info;

  bool auth_data_valid;
  uint8_t auth_data[SHA256_DIGEST_LENGTH];

  systimer_t *timer;
  bool pending_spi_transaction;

  bool dfu_mode;
  bool dfu_tx_pending;

  bool dtm_mode;
  void (*dtm_callback)(uint8_t byte);

} nrf_driver_t;

void nrf_start(void);
void nrf_stop(void);

void nrf_int_send(const uint8_t *data, uint32_t len);
uint32_t nrf_int_receive(uint8_t *data, uint32_t len);

bool nrf_reboot_to_bootloader(void);

void nrf_signal_data_ready(void);
void nrf_signal_no_data(void);

bool nrf_force_reset(void);
void nrf_stay_in_bootloader(bool set);
bool nrf_in_reserved(void);

void nrf_complete_current_request(nrf_driver_t *drv, nrf_status_t status);
void nrf_spi_init(nrf_driver_t *drv);
void nrf_spi_deinit(void);
void nrf_prepare_spi_data(nrf_driver_t *drv);

#ifdef USE_SMP
void nrf_uart_init(nrf_driver_t *drv);
void nrf_uart_deinit(void);
void nrf_uart_send(uint8_t data);
uint8_t nrf_uart_get_received(void);
void nrf_set_dfu_mode(bool set);
bool nrf_is_dfu_mode(void);
void nrf_dfu_comm_send(const uint8_t *data, uint32_t len);
uint32_t nrf_dfu_comm_receive(uint8_t *data, uint32_t len);
#endif
