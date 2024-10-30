
#include <stdint.h>
#include <stdbool.h>

#include <zephyr/types.h>

#include <zephyr/kernel.h>

#include <zephyr/logging/log.h>
#include <zephyr/drivers/spi.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/sys/crc.h>

#include "spi.h"
#include "int_comm_defs.h"

#define MY_SPI_MASTER DT_NODELABEL(spi0)

static K_SEM_DEFINE(spi_comm_ok, 0, 1);
static K_FIFO_DEFINE(fifo_spi_tx_data);

typedef struct {
    void *fifo_reserved;
    uint8_t data[BLE_PACKET_SIZE + 2];
    uint16_t len;
}spi_data_t;


const struct device *spi_dev;
static struct k_poll_signal spi_done_sig = K_POLL_SIGNAL_INITIALIZER(spi_done_sig);

struct spi_cs_control spim_cs = {
        .gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(reg_my_spi_master)),
        .delay = 0,
};

static const struct spi_config spi_cfg = {
        .operation = SPI_WORD_SET(8) | SPI_TRANSFER_MSB,
        .frequency = 8000000,
        .slave = 0,
        .cs = {
                .gpio = SPI_CS_GPIOS_DT_SPEC_GET(DT_NODELABEL(reg_my_spi_master)),
                .delay = 0,
        },
};

void spi_init(void)
{
  spi_dev = DEVICE_DT_GET(MY_SPI_MASTER);
  if(!device_is_ready(spi_dev)) {
    printk("SPI master device not ready!\n");
  }
  if(!device_is_ready(spim_cs.gpio.port)){
    printk("SPI master chip select device not ready!\n");
  }

  k_sem_give(&spi_comm_ok);
}



void spi_send(const uint8_t * data, uint32_t len)
{
  if (len != 244) {
    // unexpected length
    return;
  }

  spi_data_t * tx = k_malloc(sizeof(*tx));

  if (!tx) {
    printk("Not able to allocate SPI send data buffer\n");
    return;
  }

  tx->len = len + 2;
  tx->data[0] = EXTERNAL_MESSAGE;
  memcpy(&tx->data[1], data, len);

    uint8_t crc = crc8(tx->data, len + 1, 0x07, 0x00, false);
  tx->data[len + 1] = crc;

  k_fifo_put(&fifo_spi_tx_data, tx);
}

void spi_thread(void)
{
  /* Don't go any further until BLE is initialized */
  k_sem_take(&spi_comm_ok, K_FOREVER);

  for (;;) {
    /* Wait indefinitely for data to process */
    spi_data_t *buf = k_fifo_get(&fifo_spi_tx_data, K_FOREVER);

    const struct spi_buf tx_buf = {
            .buf = buf->data,
            .len = buf->len,
    };

    const struct spi_buf_set tx = {
            .buffers = &tx_buf,
            .count = 1
    };

    spi_transceive(spi_dev, &spi_cfg, &tx,NULL);
    printk("SPI Data sent\n");

    k_free(buf);
  }
}

K_THREAD_DEFINE(spi_thread_id, CONFIG_BT_NUS_THREAD_STACK_SIZE, spi_thread, NULL, NULL,
        NULL, 7, 0, 0);
