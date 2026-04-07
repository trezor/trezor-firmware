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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/tsqueue.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#include "../crc8.h"
#include "../nrf_internal.h"

#define SPI_OVERHEAD_SIZE (sizeof(spi_packet_t) - MAX_SPI_DATA_SIZE)
#define SPI_HEADER_SIZE (SPI_OVERHEAD_SIZE - 1)

#define START_BYTE (0xA0)

extern nrf_driver_t g_nrf_driver;

void nrf_spi_init(nrf_driver_t *drv) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  __HAL_RCC_GPDMA1_CLK_ENABLE();
  __HAL_RCC_SPI1_CLK_ENABLE();

  // SPI pins
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  GPIO_InitStructure.Pin = GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->spi_rx_dma.Instance = GPDMA1_Channel2;
  drv->spi_rx_dma.Init.Direction = DMA_PERIPH_TO_MEMORY;
  drv->spi_rx_dma.Init.Mode = DMA_NORMAL;
  drv->spi_rx_dma.Init.Request = GPDMA1_REQUEST_SPI1_RX;
  drv->spi_rx_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->spi_rx_dma.Init.SrcInc = DMA_SINC_FIXED;
  drv->spi_rx_dma.Init.DestInc = DMA_DINC_INCREMENTED;
  drv->spi_rx_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->spi_rx_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->spi_rx_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->spi_rx_dma.Init.SrcBurstLength = 1;
  drv->spi_rx_dma.Init.DestBurstLength = 1;
  drv->spi_rx_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->spi_rx_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  drv->spi_rx_dma.Parent = &drv->spi;

  HAL_DMA_Init(&drv->spi_rx_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->spi_rx_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                            DMA_CHANNEL_SRC_SEC | DMA_CHANNEL_DEST_SEC);

  drv->spi_tx_dma.Init.Direction = DMA_MEMORY_TO_PERIPH;
  drv->spi_tx_dma.Init.Mode = DMA_NORMAL;
  drv->spi_tx_dma.Instance = GPDMA1_Channel1;
  drv->spi_tx_dma.Init.Request = GPDMA1_REQUEST_SPI1_TX;
  drv->spi_tx_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->spi_tx_dma.Init.SrcInc = DMA_SINC_INCREMENTED;
  drv->spi_tx_dma.Init.DestInc = DMA_DINC_FIXED;
  drv->spi_tx_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->spi_tx_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->spi_tx_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->spi_tx_dma.Init.SrcBurstLength = 1;
  drv->spi_tx_dma.Init.DestBurstLength = 1;
  drv->spi_tx_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->spi_tx_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  drv->spi_tx_dma.Parent = &drv->spi;
  HAL_DMA_Init(&drv->spi_tx_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->spi_tx_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                            DMA_CHANNEL_SRC_SEC | DMA_CHANNEL_DEST_SEC);

  drv->spi.Instance = SPI1;
  drv->spi.Init.Mode = SPI_MODE_SLAVE;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.NSS = SPI_NSS_HARD_INPUT;
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 0;
  drv->spi.hdmarx = &drv->spi_rx_dma;
  drv->spi.hdmatx = &drv->spi_tx_dma;

  HAL_SPI_Init(&drv->spi);
}

void nrf_spi_deinit(void) {
  __HAL_RCC_SPI1_FORCE_RESET();
  __HAL_RCC_SPI1_RELEASE_RESET();

  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_1);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_4);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_6);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_7);
}

int32_t nrf_send_msg(nrf_service_id_t service, const uint8_t *data,
                     uint32_t len, nrf_tx_callback_t callback, void *context) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return -1;
  }

  if (len > NRF_MAX_TX_DATA_SIZE) {
    return -1;
  }

  if (service > NRF_SERVICE_CNT) {
    return -1;
  }

  if (!nrf_is_running()) {
    return -1;
  }

  if (!drv->comm_running) {
    return -1;
  }

  int32_t id = 0;

  nrf_tx_request_t tx_request = {0};

  tx_request.callback = callback;
  tx_request.context = context;
  tx_request.packet.service_id = 0xA0 | (uint8_t)service;
  tx_request.packet.msg_len = len;
  memcpy(&tx_request.packet.data, data, len);
  memset(&tx_request.packet.data[len], 0, sizeof(tx_request.packet.data) - len);
  tx_request.packet.crc =
      crc8((uint8_t *)&tx_request.packet, sizeof(tx_request.packet) - 1, 0x07,
           0x00, false);

  tsqueue_enqueue(&drv->tx_queue, (uint8_t *)&tx_request,
                  sizeof(nrf_tx_request_t), &id);

  irq_key_t key = irq_lock();
  if (drv->tx_request_id <= 0 && !tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }
  irq_unlock(key);

  return id;
}

bool nrf_abort_msg(int32_t id) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  bool aborted = tsqueue_abort(&drv->tx_queue, id, NULL, 0, NULL);

  if (aborted) {
    return true;
  }

  irq_key_t key = irq_lock();
  if (drv->tx_request_id == id) {
    drv->tx_request_id = -1;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

static bool nrf_is_valid_startbyte(uint8_t val) {
  if ((val & 0xF0) != START_BYTE) {
    return false;
  }

  if ((val & 0x0F) >= NRF_SERVICE_CNT) {
    return false;
  }

  return true;
}

void GPDMA1_Channel1_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_tx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void GPDMA1_Channel2_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_rx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void SPI1_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_SPI_IRQHandler(&drv->spi);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

static void nrf_process_msg(nrf_driver_t *drv, const uint8_t *data,
                            uint32_t len, nrf_service_id_t service) {
  if (drv->service_listeners[service] != NULL) {
    drv->service_listeners[service](data, len);
  }
}

void nrf_prepare_spi_data(nrf_driver_t *drv) {
  if (drv->pending_spi_transaction) {
    return;
  }
  memset(&drv->long_rx_buffer, 0, sizeof(spi_packet_t));
  if (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_request,
                      sizeof(nrf_tx_request_t), NULL, &drv->tx_request_id)) {
    HAL_SPI_TransmitReceive_DMA(&drv->spi, (uint8_t *)&drv->tx_request.packet,
                                (uint8_t *)&drv->long_rx_buffer,
                                sizeof(spi_packet_t));
  } else {
    memset(&drv->tx_request.packet, 0, sizeof(spi_packet_t));
    HAL_SPI_TransmitReceive_DMA(&drv->spi, (uint8_t *)&drv->tx_request.packet,
                                (uint8_t *)&drv->long_rx_buffer,
                                sizeof(spi_packet_t));
  }

  drv->pending_spi_transaction = true;
  nrf_signal_data_ready();
  systick_delay_us(1);
  nrf_signal_no_data();
  systimer_set(drv->timer, 2000);
}

void nrf_spi_transfer_complete(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  if (!drv->comm_running) {
    return;
  }

  spi_packet_t packet;
  memcpy(&packet, &drv->long_rx_buffer, sizeof(spi_packet_t));

  drv->pending_spi_transaction = false;

  // tx was completed
  nrf_complete_current_request(drv, NRF_STATUS_OK);

  // something to send?
  if (!tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }

  // process received data
  uint8_t crc = crc8((uint8_t *)&packet, MAX_SPI_DATA_SIZE + SPI_HEADER_SIZE,
                     0x07, 0x00, false);

  if (nrf_is_valid_startbyte(packet.service_id) && packet.crc == crc) {
    nrf_process_msg(drv, packet.data, packet.msg_len, packet.service_id & 0x0F);
  }
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_spi_transfer_complete(hspi);
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_spi_transfer_complete(hspi);
}

void HAL_SPI_ErrorCallback(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  if (!drv->comm_running) {
    return;
  }

  drv->pending_spi_transaction = false;
  nrf_complete_current_request(drv, NRF_STATUS_ERROR);

  if (!tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }
}

#endif
