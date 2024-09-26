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

#include "tsqueue/tsqueue.h"

#include "crc8.h"
#include "irq.h"
#include "mpu.h"
#include "nrf.h"
#include "nrf_internal.h"

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
  void (*callback)(nrf_status_t status, void *context);
  void *context;
} nrf_uart_tx_data_t;

typedef struct {
  UART_HandleTypeDef urt;
  DMA_HandleTypeDef urt_tx_dma;

  uint8_t urt_tx_buffers[UART_QUEUE_SIZE][sizeof(nrf_uart_tx_data_t)];
  tsqueue_entry_t urt_tx_queue_entries[UART_QUEUE_SIZE];
  tsqueue_t urt_tx_queue;

  uint8_t urt_rx_buf[UART_PACKET_SIZE];
  uint8_t urt_rx_len;
  uint8_t urt_rx_byte;
  uint16_t urt_rx_idx;

  SPI_HandleTypeDef spi;
  DMA_HandleTypeDef spi_dma;
  uint8_t spi_buffer[SPI_PACKET_SIZE];

  bool urt_tx_running;
  bool spi_rx_running;
  bool comm_running;

  bool initialized;

  void (*service_listeners[NRF_SERVICE_CNT])(const uint8_t *data, uint32_t len);

} nrf_driver_t;

__attribute__((section(".buf"))) static nrf_driver_t g_nrf_driver = {0};

static void nrf_start(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  HAL_SPI_Receive_DMA(&drv->spi, drv->spi_buffer, SPI_PACKET_SIZE);

  tsqueue_reset(&drv->urt_tx_queue);
  HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);

  drv->spi_rx_running = true;
  drv->comm_running = true;

  nrf_signal_running();
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
  tsqueue_reset(&drv->urt_tx_queue);
  irq_unlock(key);
}

void nrf_init(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    return;
  }

  __HAL_RCC_USART1_CLK_ENABLE();
  __HAL_RCC_DMA1_CLK_ENABLE();
  __HAL_RCC_DMA2_CLK_ENABLE();
  __HAL_RCC_SPI2_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  memset(drv, 0, sizeof(*drv));
  tsqueue_init(&drv->urt_tx_queue, drv->urt_tx_queue_entries,
               (uint8_t *)drv->urt_tx_buffers, sizeof(nrf_uart_tx_data_t),
               UART_QUEUE_SIZE);

  GPIO_InitTypeDef GPIO_InitStructure;

  // synchronization signals
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_12;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_1_PIN;
  HAL_GPIO_Init(GPIO_1_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_2_PIN;
  HAL_GPIO_Init(GPIO_2_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_3_PIN;
  HAL_GPIO_Init(GPIO_3_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->urt.Init.Mode = UART_MODE_TX_RX;
  drv->urt.Init.BaudRate = 1000000;
  drv->urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  drv->urt.Init.OverSampling = UART_OVERSAMPLING_16;
  drv->urt.Init.Parity = UART_PARITY_NONE;
  drv->urt.Init.StopBits = UART_STOPBITS_1;
  drv->urt.Init.WordLength = UART_WORDLENGTH_8B;
  drv->urt.Instance = USART1;
  drv->urt.hdmatx = &drv->urt_tx_dma;

  drv->urt_tx_dma.Init.Channel = DMA_CHANNEL_4;
  drv->urt_tx_dma.Init.Direction = DMA_MEMORY_TO_PERIPH;
  drv->urt_tx_dma.Init.PeriphInc = DMA_PINC_DISABLE;
  drv->urt_tx_dma.Init.MemInc = DMA_MINC_ENABLE;
  drv->urt_tx_dma.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
  drv->urt_tx_dma.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
  drv->urt_tx_dma.Init.Mode = DMA_NORMAL;
  drv->urt_tx_dma.Init.Priority = DMA_PRIORITY_LOW;
  drv->urt_tx_dma.Init.FIFOMode = DMA_FIFOMODE_DISABLE;
  drv->urt_tx_dma.Init.FIFOThreshold = DMA_FIFO_THRESHOLD_FULL;
  drv->urt_tx_dma.Init.MemBurst = DMA_MBURST_SINGLE;
  drv->urt_tx_dma.Init.PeriphBurst = DMA_PBURST_SINGLE;
  drv->urt_tx_dma.Instance = DMA2_Stream7;
  drv->urt_tx_dma.Parent = &drv->urt;
  HAL_DMA_Init(&drv->urt_tx_dma);

  HAL_UART_Init(&drv->urt);

  NVIC_SetPriority(DMA2_Stream7_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(DMA2_Stream7_IRQn);
  NVIC_SetPriority(USART1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(USART1_IRQn);

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI2;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  GPIO_InitStructure.Pin = GPIO_PIN_2 | GPIO_PIN_3;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_9;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_3;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

  drv->spi_dma.Init.Channel = DMA_CHANNEL_0;
  drv->spi_dma.Init.Direction = DMA_PERIPH_TO_MEMORY;
  drv->spi_dma.Init.PeriphInc = DMA_PINC_DISABLE;
  drv->spi_dma.Init.MemInc = DMA_MINC_ENABLE;
  drv->spi_dma.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
  drv->spi_dma.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
  drv->spi_dma.Init.Mode = DMA_NORMAL;
  drv->spi_dma.Init.Priority = DMA_PRIORITY_LOW;
  drv->spi_dma.Init.FIFOMode = DMA_FIFOMODE_DISABLE;
  drv->spi_dma.Init.FIFOThreshold = DMA_FIFO_THRESHOLD_FULL;
  drv->spi_dma.Init.MemBurst = DMA_MBURST_SINGLE;
  drv->spi_dma.Init.PeriphBurst = DMA_PBURST_SINGLE;
  drv->spi_dma.Instance = DMA1_Stream3;
  HAL_DMA_Init(&drv->spi_dma);

  drv->spi.Instance = SPI2;
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

  NVIC_SetPriority(DMA1_Stream3_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(DMA1_Stream3_IRQn);

  drv->initialized = true;

  nrf_start();
}

void nrf_deinit(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  nrf_stop();

  drv->initialized = false;
}

void nrf_register_listener(nrf_service_id_t service,
                           void (*listener)(const uint8_t *data,
                                            uint32_t len)) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  if (service < NRF_SERVICE_CNT) {
    drv->service_listeners[service] = listener;
  }
}

void nrf_unregister_listener(nrf_service_id_t service) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  if (service < NRF_SERVICE_CNT) {
    drv->service_listeners[service] = NULL;
  }
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

uint32_t nrf_send_msg(nrf_service_id_t service, const uint8_t *data,
                      uint32_t len,
                      void (*callback)(nrf_status_t status, void *context),
                      void *context) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (len > NRF_MAX_TX_DATA_SIZE) {
    return 0;
  }

  if (service > NRF_SERVICE_CNT) {
    return 0;
  }

  uint32_t id = 0;

  nrf_uart_tx_data_t *buffer =
      (nrf_uart_tx_data_t *)tsqueue_allocate(&drv->urt_tx_queue, &id);

  if (buffer == NULL) {
    return 0;
  }

  buffer->callback = callback;
  buffer->context = context;
  buffer->len = len + UART_OVERHEAD_SIZE;

  uart_header_t header = {
      .service_id = 0xA0 | (uint8_t)service,
      .msg_len = len + UART_OVERHEAD_SIZE,
  };
  memcpy(buffer->data, &header, UART_HEADER_SIZE);

  memcpy(&buffer->data[UART_HEADER_SIZE], data, len);

  uart_footer_t footer = {
      .crc = crc8(buffer->data, len + UART_HEADER_SIZE, 0x07, 0x00, false),
  };
  memcpy(&buffer->data[UART_HEADER_SIZE + len], &footer, UART_FOOTER_SIZE);

  tsqueue_finalize(&drv->urt_tx_queue, (uint8_t *)buffer,
                   sizeof(nrf_uart_tx_data_t));

  irq_key_t key = irq_lock();
  if (!drv->urt_tx_running) {
    nrf_uart_tx_data_t *send_buffer =
        (nrf_uart_tx_data_t *)tsqueue_process(&drv->urt_tx_queue, NULL);
    if (send_buffer != NULL) {
      HAL_UART_Transmit_DMA(&drv->urt, send_buffer->data, send_buffer->len);
    }
    drv->urt_tx_running = true;
  }
  irq_unlock(key);

  return id;
}

bool nrf_abort_msg(uint32_t id) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  bool aborted = tsqueue_abort(&drv->urt_tx_queue, id, NULL, 0, NULL);

  if (!aborted) {
    return false;
  }

  return true;
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
    if (drv->urt_rx_idx == 0) {
      // received first byte: START BYTE
      if (nrf_is_valid_startbyte(drv->urt_rx_byte)) {
        drv->urt_rx_buf[0] = drv->urt_rx_byte;
        drv->urt_rx_idx++;
      } else {
        // bad message, flush the line
        drv->urt_rx_idx = 0;
      }
    } else if (drv->urt_rx_idx == 1) {
      // received second byte: LEN

      drv->urt_rx_buf[1] = drv->urt_rx_byte;
      drv->urt_rx_len = drv->urt_rx_byte;

      if (drv->urt_rx_len > UART_PACKET_SIZE) {
        drv->urt_rx_len = 0;
      } else {
        drv->urt_rx_idx++;
      }
    } else if (drv->urt_rx_idx >= UART_HEADER_SIZE &&
               drv->urt_rx_idx < (drv->urt_rx_len - 1)) {
      // receive the rest of the message

      drv->urt_rx_buf[drv->urt_rx_idx] = drv->urt_rx_byte;
      drv->urt_rx_idx++;

      if (drv->urt_rx_idx >= NRF_MAX_TX_DATA_SIZE) {
        // message is too long, flush the line
        drv->urt_rx_idx = 0;
        drv->urt_rx_len = 0;
      }

    } else if (drv->urt_rx_idx == (drv->urt_rx_len - 1)) {
      // received last byte: CRC

      uint8_t crc =
          crc8(drv->urt_rx_buf, drv->urt_rx_len - 1, 0x07, 0x00, false);

      if (drv->urt_rx_byte == crc) {
        uart_header_t *header = (uart_header_t *)drv->urt_rx_buf;
        nrf_process_msg(drv, drv->urt_rx_buf, drv->urt_rx_len,
                        header->service_id & 0x0F, UART_HEADER_SIZE,
                        UART_OVERHEAD_SIZE);
      }

      drv->urt_rx_idx = 0;
      drv->urt_rx_len = 0;

    } else {
      // bad message, flush the line
      drv->urt_rx_idx = 0;
      drv->urt_rx_len = 0;
    }
  }

  // receive the rest of the message, or new message in any case.
  HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    HAL_UART_AbortReceive(urt);
    HAL_UART_AbortTransmit(urt);

    tsqueue_reset(&drv->urt_tx_queue);

    drv->urt_rx_idx = 0;
    drv->urt_rx_len = 0;

    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    nrf_uart_tx_data_t sent;
    bool aborted = false;
    if (tsqueue_process_done(&drv->urt_tx_queue, (uint8_t *)&sent, sizeof(sent),
                             NULL, &aborted)) {
      if (!aborted && sent.callback != NULL) {
        sent.callback(NRF_STATUS_OK, sent.context);
      }
    }

    nrf_uart_tx_data_t *send_buffer =
        (nrf_uart_tx_data_t *)tsqueue_process(&drv->urt_tx_queue, NULL);
    if (send_buffer != NULL) {
      HAL_UART_Transmit_DMA(&drv->urt, send_buffer->data, send_buffer->len);
      drv->urt_tx_running = true;
    } else {
      drv->urt_tx_running = false;
    }
  }
}

void USART1_IRQHandler(void) {
  IRQ_ENTER(USART1_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_UART_IRQHandler(&drv->urt);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(USART1_IRQn);
}

void DMA2_Stream7_IRQHandler(void) {
  IRQ_ENTER(DMA2_Stream7_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->urt_tx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(DMA2_Stream7_IRQn);
}

/// SPI communication
/// ----------------------------------------------------------

static bool start_spi_dma(nrf_driver_t *drv) {
  if (!drv->comm_running) {
    return false;
  }

  HAL_SPI_Receive_DMA(&drv->spi, drv->spi_buffer, SPI_PACKET_SIZE);
  drv->spi_rx_running = true;

  return true;
}

void DMA1_Stream3_IRQHandler(void) {
  IRQ_ENTER(DMA1_Stream3_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(DMA1_Stream3_IRQn);
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  spi_header_t *header = (spi_header_t *)drv->spi_buffer;
  spi_footer_t *footer =
      (spi_footer_t *)(drv->spi_buffer + SPI_PACKET_SIZE - SPI_FOOTER_SIZE);

  uint8_t crc = crc8(drv->spi_buffer, SPI_PACKET_SIZE - SPI_FOOTER_SIZE, 0x07,
                     0x00, false);

  if ((header->service_id & 0xF0) != START_BYTE || footer->crc != crc) {
    HAL_SPI_Abort(&drv->spi);
    HAL_SPI_Receive_DMA(&drv->spi, drv->spi_buffer, SPI_PACKET_SIZE);
    return;
  }

  nrf_process_msg(drv, drv->spi_buffer, SPI_PACKET_SIZE,
                  header->service_id & 0x0F, SPI_HEADER_SIZE,
                  SPI_OVERHEAD_SIZE);
  drv->spi_rx_running = false;
  start_spi_dma(drv);
}

/// GPIO communication
/// ---------------------------------------------------------

bool nrf_reboot_to_bootloader(void) {
  uint32_t tick_start = 0;

  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1, GPIO_PIN_RESET);

  HAL_Delay(10);
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1, GPIO_PIN_SET);

  tick_start = HAL_GetTick();

  while (HAL_GPIO_ReadPin(GPIO_1_PORT, GPIO_1_PIN) == GPIO_PIN_RESET) {
    if (HAL_GetTick() - tick_start > 4000) {
      return false;
    }
  }

  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);

  HAL_Delay(1000);

  return true;
}

bool nrf_reboot(void) {
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
  HAL_Delay(50);
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
  return true;
}

void nrf_signal_running(void) {
  HAL_GPIO_WritePin(GPIO_3_PORT, GPIO_3_PIN, GPIO_PIN_SET);
}

void nrf_signal_off(void) {
  HAL_GPIO_WritePin(GPIO_3_PORT, GPIO_3_PIN, GPIO_PIN_RESET);
}

bool nrf_firmware_running(void) {
  return HAL_GPIO_ReadPin(GPIO_2_PORT, GPIO_2_PIN) != 0;
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
