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

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/crc.h>
#include <zephyr/types.h>

#include <trz_comm/trz_comm.h>

#include "trz_comm_internal.h"

#define LOG_MODULE_NAME trz_comm_spi
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define MY_SPI_MASTER DT_NODELABEL(spi0)

static K_SEM_DEFINE(spi_comm_ok, 0, 1);
static K_FIFO_DEFINE(fifo_spi_tx_data);

const struct device *spi_dev;
static struct k_poll_signal spi_done_sig =
    K_POLL_SIGNAL_INITIALIZER(spi_done_sig);

struct spi_cs_control spim_cs = {
    .gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(reg_my_spi_master)),
    .delay = 0,
};

static const struct spi_config spi_cfg = {
    .operation = SPI_WORD_SET(8) | SPI_TRANSFER_MSB,
    .frequency = 8000000,
    .slave = 0,
    .cs =
        {
            .gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(reg_my_spi_master)),
            .delay = 0,
        },
};

void spi_init(void) {
  spi_dev = DEVICE_DT_GET(MY_SPI_MASTER);
  if (!device_is_ready(spi_dev)) {
    printk("SPI master device not ready!\n");
  }
  if (!device_is_ready(spim_cs.gpio.port)) {
    printk("SPI master chip select device not ready!\n");
  }

  k_sem_give(&spi_comm_ok);
}

bool spi_send(uint8_t service_id, const uint8_t *data, uint32_t len) {
  if (len != 244) {
    // unexpected length
    return false;
  }

  trz_packet_t *tx = k_malloc(sizeof(*tx));

  if (!tx) {
    printk("Not able to allocate SPI send data buffer\n");
    return false;
  }

  tx->len = len + 2;
  tx->data[0] = 0xA0 | service_id;
  memcpy(&tx->data[1], data, len);

  uint8_t crc = crc8(tx->data, len + 1, 0x07, 0x00, false);
  tx->data[len + 1] = crc;

  k_fifo_put(&fifo_spi_tx_data, tx);

  return true;
}

void spi_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&spi_comm_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to process */
    trz_packet_t *buf = k_fifo_get(&fifo_spi_tx_data, K_FOREVER);

    const struct spi_buf tx_buf = {
        .buf = buf->data,
        .len = buf->len,
    };

    const struct spi_buf_set tx = {.buffers = &tx_buf, .count = 1};

    spi_transceive(spi_dev, &spi_cfg, &tx, NULL);
    printk("SPI Data sent\n");

    k_free(buf);
  }
}

K_THREAD_DEFINE(spi_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE, spi_thread,
                NULL, NULL, NULL, 7, 0, 0);
