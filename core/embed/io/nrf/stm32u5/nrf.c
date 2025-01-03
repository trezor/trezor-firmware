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

#include <io/nrf.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include <util/tsqueue.h>

#include "../crc8.h"
#include "../nrf_internal.h"

#define MAX_SPI_DATA_SIZE (244)

typedef struct {
  uint8_t service_id;
} spi_header_t;

typedef struct {
  uint8_t crc;
} spi_footer_t;

#define SPI_HEADER_SIZE (sizeof(spi_header_t))
#define SPI_FOOTER_SIZE (sizeof(spi_footer_t))
#define SPI_OVERHEAD_SIZE (SPI_HEADER_SIZE + SPI_FOOTER_SIZE)
#define SPI_PACKET_SIZE (MAX_SPI_DATA_SIZE + SPI_OVERHEAD_SIZE)

typedef struct {
  uint8_t service_id;
  uint8_t msg_len;
} uart_header_t;

typedef struct {
  uint8_t crc;
} uart_footer_t;

#define UART_HEADER_SIZE (sizeof(uart_header_t))
#define UART_FOOTER_SIZE (sizeof(uart_footer_t))
#define UART_OVERHEAD_SIZE (UART_HEADER_SIZE + UART_FOOTER_SIZE)
#define UART_PACKET_SIZE (NRF_MAX_TX_DATA_SIZE + UART_OVERHEAD_SIZE)
#define UART_QUEUE_SIZE (8)

#define START_BYTE (0xA0)

typedef struct {
  uint8_t data[UART_PACKET_SIZE];
  uint8_t len;
  nrf_tx_callback_t callback;
  void *context;
} nrf_uart_tx_data_t;

typedef struct {
  UART_HandleTypeDef urt;
  DMA_HandleTypeDef urt_tx_dma;

  uint8_t tx_buffers[UART_QUEUE_SIZE][sizeof(nrf_uart_tx_data_t)];
  tsqueue_entry_t tx_queue_entries[UART_QUEUE_SIZE];
  tsqueue_t tx_queue;
  nrf_uart_tx_data_t tx_data;
  int32_t tx_msg_id;

  uint8_t rx_buffer[UART_PACKET_SIZE];
  uint8_t rx_len;
  uint8_t rx_byte;
  uint16_t rx_idx;

  SPI_HandleTypeDef spi;
  DMA_HandleTypeDef spi_dma;
  uint8_t long_rx_buffer[SPI_PACKET_SIZE];

  bool comm_running;
  bool initialized;

  nrf_rx_callback_t service_listeners[NRF_SERVICE_CNT];

} nrf_driver_t;

static nrf_driver_t g_nrf_driver = {0};

static void nrf_start(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  HAL_SPI_Receive_DMA(&drv->spi, drv->long_rx_buffer, SPI_PACKET_SIZE);

  tsqueue_reset(&drv->tx_queue);
  HAL_UART_Receive_IT(&drv->urt, &drv->rx_byte, 1);

  drv->comm_running = true;

  nrf_signal_running();
}

static void nrf_abort_urt_comm(nrf_driver_t *drv) {
  HAL_UART_AbortReceive(&drv->urt);
  HAL_UART_AbortTransmit(&drv->urt);

  if (drv->tx_data.callback != NULL) {
    drv->tx_data.callback(NRF_STATUS_ERROR, drv->tx_data.context);
  }

  drv->rx_idx = 0;
  drv->rx_len = 0;
  drv->tx_msg_id = -1;

  while (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_data,
                         sizeof(nrf_uart_tx_data_t), NULL, &drv->tx_msg_id)) {
    if (drv->tx_data.callback != NULL) {
      drv->tx_data.callback(NRF_STATUS_ERROR, drv->tx_data.context);
    }
  }

  memset(&drv->tx_data, 0, sizeof(nrf_uart_tx_data_t));

  tsqueue_reset(&drv->tx_queue);
}

static void nrf_stop(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  nrf_signal_off();
  irq_key_t key = irq_lock();
  drv->comm_running = false;
  HAL_SPI_DMAStop(&drv->spi);
  nrf_abort_urt_comm(drv);
  irq_unlock(key);
}

void nrf_init(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    return;
  }

  __HAL_RCC_USART3_CLK_ENABLE();
  __HAL_RCC_GPDMA1_CLK_ENABLE();
  __HAL_RCC_SPI1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  memset(drv, 0, sizeof(*drv));
  tsqueue_init(&drv->tx_queue, drv->tx_queue_entries,
               (uint8_t *)drv->tx_buffers, sizeof(nrf_uart_tx_data_t),
               UART_QUEUE_SIZE);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // synchronization signals
  NRF_OUT_RESET_CLK_ENA();
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_RESET_PIN;
  HAL_GPIO_Init(NRF_OUT_RESET_PORT, &GPIO_InitStructure);

  NRF_IN_GPIO0_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_GPIO0_PIN;
  HAL_GPIO_Init(NRF_IN_GPIO0_PORT, &GPIO_InitStructure);

  NRF_IN_FW_RUNNING_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_FW_RUNNING_PIN;
  HAL_GPIO_Init(NRF_IN_FW_RUNNING_PORT, &GPIO_InitStructure);

  NRF_OUT_STAY_IN_BLD_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_STAY_IN_BLD_PIN;
  HAL_GPIO_Init(NRF_OUT_STAY_IN_BLD_PORT, &GPIO_InitStructure);

  NRF_OUT_FW_RUNNING_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_FW_RUNNING_PIN;
  HAL_GPIO_Init(NRF_OUT_FW_RUNNING_PORT, &GPIO_InitStructure);

  // UART PINS
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART3;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Pin = GPIO_PIN_5;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_10 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_11;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

  drv->urt.Init.Mode = UART_MODE_TX_RX;
  drv->urt.Init.BaudRate = 1000000;
  drv->urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  drv->urt.Init.OverSampling = UART_OVERSAMPLING_16;
  drv->urt.Init.Parity = UART_PARITY_NONE;
  drv->urt.Init.StopBits = UART_STOPBITS_1;
  drv->urt.Init.WordLength = UART_WORDLENGTH_8B;
  drv->urt.Instance = USART3;
  drv->urt.hdmatx = &drv->urt_tx_dma;

  drv->urt_tx_dma.Init.Direction = DMA_MEMORY_TO_PERIPH;
  drv->urt_tx_dma.Init.Mode = DMA_NORMAL;
  drv->urt_tx_dma.Instance = GPDMA1_Channel1;
  drv->urt_tx_dma.Init.Request = GPDMA1_REQUEST_USART3_TX;
  drv->urt_tx_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->urt_tx_dma.Init.SrcInc = DMA_SINC_INCREMENTED;
  drv->urt_tx_dma.Init.DestInc = DMA_DINC_FIXED;
  drv->urt_tx_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->urt_tx_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->urt_tx_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->urt_tx_dma.Init.SrcBurstLength = 1;
  drv->urt_tx_dma.Init.DestBurstLength = 1;
  drv->urt_tx_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->urt_tx_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;

  drv->urt_tx_dma.Parent = &drv->urt;
  HAL_DMA_Init(&drv->urt_tx_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->urt_tx_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                            DMA_CHANNEL_SRC_SEC | DMA_CHANNEL_DEST_SEC);

  HAL_UART_Init(&drv->urt);

  NVIC_SetPriority(GPDMA1_Channel1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_SetPriority(USART3_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(USART3_IRQn);

  // SPI pins
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  GPIO_InitStructure.Pin = GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->spi_dma.Instance = GPDMA1_Channel2;
  drv->spi_dma.Init.Direction = DMA_PERIPH_TO_MEMORY;
  drv->spi_dma.Init.Mode = DMA_NORMAL;
  drv->spi_dma.Init.Request = GPDMA1_REQUEST_SPI1_RX;
  drv->spi_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->spi_dma.Init.SrcInc = DMA_SINC_FIXED;
  drv->spi_dma.Init.DestInc = DMA_DINC_INCREMENTED;
  drv->spi_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->spi_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->spi_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->spi_dma.Init.SrcBurstLength = 1;
  drv->spi_dma.Init.DestBurstLength = 1;
  drv->spi_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->spi_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;

  HAL_DMA_Init(&drv->spi_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->spi_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC | DMA_CHANNEL_SRC_SEC |
                         DMA_CHANNEL_DEST_SEC);

  drv->spi.Instance = SPI1;
  drv->spi.Init.Mode = SPI_MODE_SLAVE;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES_RXONLY;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.NSS = SPI_NSS_HARD_INPUT;
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 0;
  drv->spi.hdmarx = &drv->spi_dma;

  drv->spi_dma.Parent = &drv->spi;

  HAL_SPI_Init(&drv->spi);

  NVIC_SetPriority(GPDMA1_Channel2_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_SetPriority(SPI1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(SPI1_IRQn);

  drv->initialized = true;

  nrf_start();
}

void nrf_deinit(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  nrf_stop();

  NVIC_DisableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_DisableIRQ(SPI1_IRQn);

  __HAL_RCC_SPI1_FORCE_RESET();
  __HAL_RCC_SPI1_RELEASE_RESET();

  __HAL_RCC_USART1_FORCE_RESET();
  __HAL_RCC_USART1_RELEASE_RESET();

  drv->initialized = false;
}

bool nrf_register_listener(nrf_service_id_t service,
                           nrf_rx_callback_t callback) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  if (service >= NRF_SERVICE_CNT) {
    return false;
  }

  if (drv->service_listeners[service] != NULL) {
    return false;
  }

  irq_key_t key = irq_lock();
  drv->service_listeners[service] = callback;
  irq_unlock(key);

  return true;
}

void nrf_unregister_listener(nrf_service_id_t service) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  if (service >= NRF_SERVICE_CNT) {
    return;
  }

  irq_key_t key = irq_lock();
  drv->service_listeners[service] = NULL;
  irq_unlock(key);
}

static void nrf_process_msg(nrf_driver_t *drv, const uint8_t *data,
                            uint32_t len, nrf_service_id_t service,
                            uint8_t header_size, uint8_t overhead_size) {
  const uint8_t *service_data = data + header_size;
  uint32_t service_data_len = len - overhead_size;
  if (drv->service_listeners[service] != NULL) {
    drv->service_listeners[service](service_data, service_data_len);
  }
}

/// DFU communication
/// ----------------------------------------------------------

void nrf_dfu_comm_send(const uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  HAL_UART_Transmit(&drv->urt, (uint8_t *)data, len, 30);
}

uint32_t nrf_dfu_comm_receive(uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (__HAL_UART_GET_FLAG(&drv->urt, UART_FLAG_RXNE)) {
    HAL_StatusTypeDef result = HAL_UART_Receive(&drv->urt, data, len, 30);

    if (result == HAL_OK) {
      return len;
    }

    if (drv->urt.RxXferCount == len) {
      return 0;
    }

    return len - drv->urt.RxXferCount - 1;
  }

  return 0;
}

/// UART communication
/// ---------------------------------------------------------

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

  int32_t id = 0;

  nrf_uart_tx_data_t buffer;

  buffer.callback = callback;
  buffer.context = context;
  buffer.len = len + UART_OVERHEAD_SIZE;

  uart_header_t header = {
      .service_id = 0xA0 | (uint8_t)service,
      .msg_len = len + UART_OVERHEAD_SIZE,
  };
  memcpy(buffer.data, &header, UART_HEADER_SIZE);

  memcpy(&buffer.data[UART_HEADER_SIZE], data, len);

  uart_footer_t footer = {
      .crc = crc8(buffer.data, len + UART_HEADER_SIZE, 0x07, 0x00, false),
  };
  memcpy(&buffer.data[UART_HEADER_SIZE + len], &footer, UART_FOOTER_SIZE);

  if (!tsqueue_enqueue(&drv->tx_queue, (uint8_t *)&buffer,
                       sizeof(nrf_uart_tx_data_t), &id)) {
    return -1;
  }

  irq_key_t key = irq_lock();
  if (drv->tx_msg_id < 0) {
    int32_t tx_id = 0;
    if (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_data,
                        sizeof(nrf_uart_tx_data_t), NULL, &tx_id)) {
      HAL_UART_Transmit_DMA(&drv->urt, drv->tx_data.data, drv->tx_data.len);
      drv->tx_msg_id = tx_id;
    }
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
  if (drv->tx_msg_id == id) {
    drv->tx_msg_id = -1;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

static bool nrf_is_valid_startbyte(uint8_t val) {
  if ((val & 0xF0) != 0xA0) {
    return false;
  }

  if ((val & 0x0F) >= NRF_SERVICE_CNT) {
    return false;
  }

  return true;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    if (drv->rx_idx == 0) {
      // received first byte: START BYTE
      if (nrf_is_valid_startbyte(drv->rx_byte)) {
        drv->rx_buffer[0] = drv->rx_byte;
        drv->rx_idx++;
      } else {
        // bad message, flush the line
        drv->rx_idx = 0;
      }
    } else if (drv->rx_idx == 1) {
      // received second byte: LEN

      drv->rx_buffer[1] = drv->rx_byte;
      drv->rx_len = drv->rx_byte;

      if (drv->rx_len > UART_PACKET_SIZE) {
        drv->rx_len = 0;
      } else {
        drv->rx_idx++;
      }
    } else if (drv->rx_idx >= UART_HEADER_SIZE &&
               drv->rx_idx < (drv->rx_len - 1)) {
      // receive the rest of the message

      drv->rx_buffer[drv->rx_idx] = drv->rx_byte;
      drv->rx_idx++;

      if (drv->rx_idx >= NRF_MAX_TX_DATA_SIZE) {
        // message is too long, flush the line
        drv->rx_idx = 0;
        drv->rx_len = 0;
      }

    } else if (drv->rx_idx == (drv->rx_len - 1)) {
      // received last byte: CRC

      uint8_t crc = crc8(drv->rx_buffer, drv->rx_len - 1, 0x07, 0x00, false);

      if (drv->rx_byte == crc) {
        uart_header_t *header = (uart_header_t *)drv->rx_buffer;
        nrf_process_msg(drv, drv->rx_buffer, drv->rx_len,
                        header->service_id & 0x0F, UART_HEADER_SIZE,
                        UART_OVERHEAD_SIZE);
      }

      drv->rx_idx = 0;
      drv->rx_len = 0;

    } else {
      // bad message, flush the line
      drv->rx_idx = 0;
      drv->rx_len = 0;
    }
  }

  // receive the rest of the message, or new message in any case.
  HAL_UART_Receive_IT(&drv->urt, &drv->rx_byte, 1);
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    nrf_abort_urt_comm(drv);

    HAL_UART_Receive_IT(&drv->urt, &drv->rx_byte, 1);
  }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    if (drv->tx_msg_id >= 0 && (drv->tx_data.callback != NULL)) {
      drv->tx_data.callback(NRF_STATUS_OK, drv->tx_data.context);
      drv->tx_msg_id = -1;
      memset(&drv->tx_data, 0, sizeof(nrf_uart_tx_data_t));
    }

    bool msg =
        tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_data,
                        sizeof(nrf_uart_tx_data_t), NULL, &drv->tx_msg_id);
    if (msg) {
      HAL_UART_Transmit_DMA(&drv->urt, drv->tx_data.data, drv->tx_data.len);
    }
  }
}

void USART3_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_UART_IRQHandler(&drv->urt);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void GPDMA1_Channel1_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->urt_tx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

/// SPI communication
/// ----------------------------------------------------------

void GPDMA1_Channel2_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_dma);
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

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  spi_header_t *header = (spi_header_t *)drv->long_rx_buffer;
  spi_footer_t *footer =
      (spi_footer_t *)(drv->long_rx_buffer + SPI_PACKET_SIZE - SPI_FOOTER_SIZE);

  uint8_t crc = crc8(drv->long_rx_buffer, SPI_PACKET_SIZE - SPI_FOOTER_SIZE,
                     0x07, 0x00, false);

  if ((header->service_id & 0xF0) != START_BYTE || footer->crc != crc) {
    HAL_SPI_Abort(&drv->spi);
    HAL_SPI_Receive_DMA(&drv->spi, drv->long_rx_buffer, SPI_PACKET_SIZE);
    return;
  }

  nrf_process_msg(drv, drv->long_rx_buffer, SPI_PACKET_SIZE,
                  header->service_id & 0x0F, SPI_HEADER_SIZE,
                  SPI_OVERHEAD_SIZE);

  HAL_SPI_Receive_DMA(&drv->spi, drv->long_rx_buffer, SPI_PACKET_SIZE);
}

/// GPIO communication
/// ---------------------------------------------------------

bool nrf_reboot_to_bootloader(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);

  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_SET);

  systick_delay_ms(50);

  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);

  systick_delay_ms(1000);

  return true;
}

bool nrf_reboot(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_RESET);
  systick_delay_ms(50);
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);
  return true;
}

void nrf_signal_running(void) {
  HAL_GPIO_WritePin(NRF_OUT_FW_RUNNING_PORT, NRF_OUT_FW_RUNNING_PIN,
                    GPIO_PIN_SET);
}

void nrf_signal_off(void) {
  HAL_GPIO_WritePin(NRF_OUT_FW_RUNNING_PORT, NRF_OUT_FW_RUNNING_PIN,
                    GPIO_PIN_RESET);
}

bool nrf_firmware_running(void) {
  return HAL_GPIO_ReadPin(NRF_IN_FW_RUNNING_PORT, NRF_IN_FW_RUNNING_PIN) != 0;
}

bool nrf_is_running(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  if (!nrf_firmware_running()) {
    return false;
  }

  return drv->comm_running;
}

void nrf_set_dfu_mode(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  // TODO
  //  if (nrf_reboot_to_bootloader()) {
  //    drv->mode_current = BLE_MODE_DFU;
  //  } else {
  //    drv->status_valid = false;
  //  }
}

bool nrf_is_dfu_mode(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return false;
  }

  return true;
  // TODO
}

#endif
