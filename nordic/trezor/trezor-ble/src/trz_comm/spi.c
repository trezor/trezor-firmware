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

#include <signals/signals.h>
#include <trz_comm/trz_comm.h>

#include "trz_comm_internal.h"

#define LOG_MODULE_NAME trz_comm_spi
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define MY_SPI_MASTER DT_NODELABEL(spi0)

static K_SEM_DEFINE(spi_comm_ok, 0, 1);
static K_SEM_DEFINE(spi_can_send, 0, 1);
static K_FIFO_DEFINE(fifo_spi_tx_data);
static K_MUTEX_DEFINE(spi_mutex);

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

#define GPIO0_DEV DEVICE_DT_GET(DT_NODELABEL(gpio0))
#define READY_NODE DT_ALIAS(spi_ready)
#define REQUEST_NODE DT_ALIAS(spi_request)

static const struct gpio_dt_spec spi_ready =
    GPIO_DT_SPEC_GET(READY_NODE, gpios);
static const struct gpio_dt_spec spi_request =
    GPIO_DT_SPEC_GET(REQUEST_NODE, gpios);

#define MAX_SPI_DATA_SIZE (251)
typedef struct {
  uint8_t service_id;
  uint8_t msg_len;
  uint8_t data[MAX_SPI_DATA_SIZE];
  uint8_t crc;
} spi_packet_t;

/* This function will run in interrupt context. Keep it as short as possible. */
void gpio_callback_handler(const struct device *dev, struct gpio_callback *cb,
                           uint32_t pins) {
  if (pins & BIT(spi_ready.pin)) {
    if (k_sem_count_get(&spi_can_send) == 0) {
      k_sem_give(&spi_can_send);
    }
  }
}

void spi_init(void) {
  int ret;

  gpio_pin_configure_dt(&spi_ready, GPIO_INPUT);
  gpio_pin_configure_dt(&spi_request, GPIO_OUTPUT);

  ret = gpio_pin_interrupt_configure_dt(&spi_ready, GPIO_INT_EDGE_TO_ACTIVE);
  __ASSERT(ret == 0, "READY interrupt config failed");

  static struct gpio_callback gpio_cb_data;

  gpio_init_callback(&gpio_cb_data, gpio_callback_handler, BIT(spi_ready.pin));

  ret = gpio_add_callback(spi_ready.port, &gpio_cb_data);
  __ASSERT(ret == 0, "Adding EADY callback failed");

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
  if (len > MAX_SPI_DATA_SIZE) {
    printk("Too big data\n");
    return false;
  }

  trz_packet_t *tx = k_malloc(sizeof(*tx));

  if (tx == NULL) {
    printk("Not able to allocate SPI send data buffer\n");
    return false;
  }

  tx->len = PACKET_DATA_SIZE;
  tx->data[0] = 0xA0 | service_id;
  tx->data[1] = len;

  if (data != NULL) {
    memcpy(&tx->data[2], data, len);
  }
  memset(&tx->data[2 + len], 0, PACKET_DATA_SIZE - 2 - len);

  uint8_t crc = crc8(tx->data, PACKET_DATA_SIZE - 1, 0x07, 0x00, false);
  tx->data[PACKET_DATA_SIZE - 1] = crc;

  k_mutex_lock(&spi_mutex, K_FOREVER);
  k_fifo_put(&fifo_spi_tx_data, tx);
  gpio_pin_set_dt(&spi_request, 1);
  k_mutex_unlock(&spi_mutex);

  return true;
}

void spi_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&spi_comm_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for signal to process */
    k_sem_take(&spi_can_send, K_FOREVER);

    trz_packet_t *buf = k_fifo_get(&fifo_spi_tx_data, K_NO_WAIT);

    uint8_t *rx_data = k_malloc(PACKET_DATA_SIZE);

    if (rx_data == NULL) {
      printk("Not able to allocate SPI receive data buffer\n");
      k_free(buf);
      continue;
    }

    const struct spi_buf rx_buf = {
        .buf = (uint8_t *)rx_data,
        .len = PACKET_DATA_SIZE,
    };

    const struct spi_buf_set rx = {.buffers = &rx_buf, .count = 1};

    const struct spi_buf_set *txp = NULL;
    struct spi_buf tx_buf;
    struct spi_buf_set tx_set;

    if (buf != NULL) {
      tx_buf.buf = buf->data;
      tx_buf.len = buf->len;
      tx_set.buffers = &tx_buf;
      tx_set.count = 1;
      txp = &tx_set;
    }

    if (spi_transceive(spi_dev, &spi_cfg, txp, &rx) != 0) {
      printk("SPI Data not sent\n");
    }

    spi_packet_t *rx_msg = (spi_packet_t *)rx_data;

    uint8_t crc = crc8(rx_data, PACKET_DATA_SIZE - 1, 0x07, 0, false);

    if (crc == rx_msg->crc && (rx_msg->service_id & 0xF0) == 0xA0) {
      process_rx_msg(rx_msg->service_id & 0xF, rx_msg->data, rx_msg->msg_len);
    } else {
      if (rx_msg->service_id != 0) {
        printk("SPI RX invalid data\n");
      }
    }

    k_free(buf);
    k_free(rx_data);

    k_mutex_lock(&spi_mutex, K_FOREVER);
    gpio_pin_set_dt(&spi_request, 0);
    if (!k_fifo_is_empty(&fifo_spi_tx_data)) {
      gpio_pin_set_dt(&spi_request, 1);
    }
    k_mutex_unlock(&spi_mutex);
  }
}

K_THREAD_DEFINE(spi_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE, spi_thread,
                NULL, NULL, NULL, 1, 0, 0);
