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
#include STM32_HAL_H
#include TREZOR_BOARD

#include <string.h>

#include "ble.h"
#include "ble_hal.h"
#include "int_comm_defs.h"
#include "irq.h"
#include "mpu.h"
#include "static_queue.h"

#define SPI_PACKET_SIZE BLE_PACKET_SIZE
#define SPI_QUEUE_SIZE (16)

#define UART_COMM_HEADER_SIZE (3)
#define UART_COMM_FOOTER_SIZE (1)
#define UART_OVERHEAD_SIZE (UART_COMM_HEADER_SIZE + UART_COMM_FOOTER_SIZE)
#define UART_PACKET_SIZE (INTERNAL_DATA_SIZE + UART_OVERHEAD_SIZE)
#define UART_QUEUE_SIZE (4)

CREATE_QUEUE_TYPE(spi_rx, SPI_PACKET_SIZE, SPI_QUEUE_SIZE)
CREATE_QUEUE_TYPE(uart_rx, INTERNAL_DATA_SIZE, UART_QUEUE_SIZE)
CREATE_QUEUE_TYPE(uart_tx, UART_PACKET_SIZE, UART_QUEUE_SIZE)

typedef struct {
  UART_HandleTypeDef urt;
  DMA_HandleTypeDef urt_tx_dma;
  uart_tx_queue_t urt_tx_queue;

  uart_rx_queue_t urt_rx_queue;
  uint16_t urt_rx_idx;
  uint16_t urt_rx_len;
  uint8_t urt_rx_byte;
  uint8_t *urt_rx_buf;

  SPI_HandleTypeDef spi;
  DMA_HandleTypeDef spi_dma;
  spi_rx_queue_t spi_queue;
  bool spi_rx_running;
  bool comm_running;

  bool initialized;

} ble_hal_driver_t;

__attribute__((section(".buf"))) static ble_hal_driver_t g_ble_hal_driver = {0};

void ble_hal_init(void) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;

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
  spi_rx_queue_init(&drv->spi_queue);
  uart_rx_queue_init(&drv->urt_rx_queue);

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
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;  // rx only?
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
}

void ble_hal_deinit(void) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return;
  }

  // TODO proceed with deinitialization, stop comm etc
}

void ble_hal_start(void) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return;
  }

  spi_rx_queue_init(&drv->spi_queue);
  uint8_t *buffer = spi_rx_queue_allocate(&drv->spi_queue);
  if (buffer != NULL) {
    HAL_SPI_Receive_DMA(&drv->spi, buffer, BLE_PACKET_SIZE);
  }

  uart_rx_queue_init(&drv->urt_rx_queue);
  drv->urt_rx_buf = uart_rx_queue_allocate(&drv->urt_rx_queue);
  HAL_UART_Receive_IT(&drv->urt, (uint8_t *)&drv->urt_rx_byte, 1);

  drv->spi_rx_running = true;
  drv->comm_running = true;

  ble_hal_signal_running();
}

void ble_hal_stop(void) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return;
  }

  ble_hal_signal_off();
  irq_key_t key = irq_lock();
  drv->comm_running = false;
  HAL_SPI_DMAStop(&drv->spi);
  spi_rx_queue_init(&drv->spi_queue);
  uart_rx_queue_init(&drv->urt_rx_queue);
  uart_tx_queue_init(&drv->urt_tx_queue);
  irq_unlock(key);
}

bool ble_hal_comm_running(void) {
  return g_ble_hal_driver.initialized && g_ble_hal_driver.comm_running;
}

/// DFU communication ----------------------------------------------------------

void ble_hal_dfu_comm_send(const uint8_t *data, uint32_t len) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return;
  }

  HAL_UART_Transmit(&drv->urt, (uint8_t *)data, len, 30);
}

uint32_t ble_hal_dfu_comm_receive(uint8_t *data, uint32_t len) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
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

/// UART communication ---------------------------------------------------------

static void ble_hal_send(const uint8_t *data, uint32_t len,
                         uint8_t message_type) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return;
  }

  if (len > INTERNAL_DATA_SIZE) {
    return;
  }

  bool empty_queue = uart_tx_queue_empty(&drv->urt_tx_queue);

  uint8_t *buffer = uart_tx_queue_allocate(&drv->urt_tx_queue);

  if (buffer == NULL) {
    return;
  }

  uint16_t msg_len = len + UART_OVERHEAD_SIZE;
  uint8_t len_hi = msg_len >> 8;
  uint8_t len_lo = msg_len & 0xFF;
  uint8_t eom = EOM;

  buffer[0] = message_type;
  buffer[1] = len_hi;
  buffer[2] = len_lo;
  memcpy(&buffer[3], data, len);
  buffer[msg_len - 1] = eom;

  uart_tx_queue_finalize(&drv->urt_tx_queue, buffer, msg_len);

  if (empty_queue) {
    uint16_t send_len = 0;
    uint8_t *send_buffer = uart_tx_queue_process(&drv->urt_tx_queue, &send_len);
    if (send_buffer != NULL) {
      HAL_UART_Transmit_DMA(&drv->urt, send_buffer, msg_len);
    }
  }
}

void ble_hal_int_send(const uint8_t *data, uint32_t len) {
  ble_hal_send(data, len, INTERNAL_MESSAGE);
}

void ble_hal_ext_send(const uint8_t *data, uint32_t len) {
  ble_hal_send(data, len, EXTERNAL_MESSAGE);
}

uint32_t ble_hal_int_receive(uint8_t *data, uint32_t len) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return 0;
  }

  uint16_t real_len = 0;
  bool read_ok = uart_rx_queue_read(&drv->urt_rx_queue, data, len, &real_len);

  if (read_ok) {
    return real_len;
  }

  return 0;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *urt) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized && urt == &drv->urt) {
    if (drv->urt_rx_buf != NULL) {
      // queue is not full, can process received byte

      if (drv->urt_rx_idx == 0) {
        // received first byte
        // check message type
        if (drv->urt_rx_byte == INTERNAL_MESSAGE) {
          drv->urt_rx_idx = 1;
        } else {
          // bad message, flush the line
          drv->urt_rx_idx = 0;
        }
      } else if (drv->urt_rx_idx == 1) {
        // received second byte
        // which is LEN HI

        drv->urt_rx_len = drv->urt_rx_byte << 8;
        drv->urt_rx_idx = 2;
      } else if (drv->urt_rx_idx == 2) {
        // received third byte
        // which is LEN LO

        drv->urt_rx_len |= drv->urt_rx_byte;

        if (drv->urt_rx_len > UART_PACKET_SIZE + UART_OVERHEAD_SIZE) {
          drv->urt_rx_len = 0;
        } else {
          drv->urt_rx_idx = UART_COMM_HEADER_SIZE;
        }
      } else if (drv->urt_rx_idx >= UART_COMM_HEADER_SIZE &&
                 drv->urt_rx_idx < (drv->urt_rx_len - 1)) {
        // receive the rest of the message

        drv->urt_rx_buf[drv->urt_rx_idx - UART_COMM_HEADER_SIZE] =
            drv->urt_rx_byte;
        drv->urt_rx_idx++;
      } else if (drv->urt_rx_idx == (drv->urt_rx_len - 1)) {
        // received last byte
        // which is EOM

        if (drv->urt_rx_byte == EOM) {
          uart_rx_queue_finalize(&drv->urt_rx_queue, drv->urt_rx_buf,
                                 drv->urt_rx_len - UART_OVERHEAD_SIZE);
          drv->urt_rx_buf = uart_rx_queue_allocate(&drv->urt_rx_queue);
        }

        drv->urt_rx_idx = 0;
        drv->urt_rx_len = 0;

      } else {
        // bad message, flush the line
        drv->urt_rx_idx = 0;
        drv->urt_rx_len = 0;
      }
    }

    if (drv->urt_rx_buf == NULL) {
      // queue is not allocated, flush the line and try allocation
      drv->urt_rx_idx = 0;
      drv->urt_rx_len = 0;
      drv->urt_rx_buf = uart_rx_queue_allocate(&drv->urt_rx_queue);
    }

    // receive the rest of the message, or new message in any case.
    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *urt) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized && urt == &drv->urt) {
    HAL_UART_AbortReceive(urt);
    HAL_UART_AbortTransmit(urt);

    uart_tx_queue_init(&drv->urt_tx_queue);
    uart_rx_queue_init(&drv->urt_rx_queue);

    drv->urt_rx_buf = uart_rx_queue_allocate(&drv->urt_rx_queue);
    drv->urt_rx_idx = 0;
    drv->urt_rx_len = 0;

    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *urt) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized && urt == &drv->urt) {
    uart_tx_queue_process_done(&drv->urt_tx_queue);

    uint16_t send_len = 0;
    uint8_t *send_buffer = uart_tx_queue_process(&drv->urt_tx_queue, &send_len);
    if (send_buffer != NULL) {
      HAL_UART_Transmit_DMA(&drv->urt, send_buffer, send_len);
    }
  }
}

void USART1_IRQHandler(void) {
  IRQ_ENTER(USART1_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized) {
    HAL_UART_IRQHandler(&drv->urt);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(USART1_IRQn);
}

void DMA2_Stream7_IRQHandler(void) {
  IRQ_ENTER(DMA2_Stream7_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->urt_tx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(DMA1_Stream3_IRQn);
}

/// SPI communication ----------------------------------------------------------

static bool start_spi_dma(ble_hal_driver_t *drv) {
  spi_rx_queue_t *queue = &drv->spi_queue;

  uint8_t *data = spi_rx_queue_allocate(queue);

  if (data != NULL) {
    HAL_SPI_Receive_DMA(&drv->spi, data, BLE_PACKET_SIZE);
    drv->spi_rx_running = true;
    return true;
  }

  return false;
}

void DMA1_Stream3_IRQHandler(void) {
  IRQ_ENTER(DMA1_Stream3_IRQn);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_EXIT(DMA1_Stream3_IRQn);
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (drv->initialized && hspi == &drv->spi) {
    spi_rx_queue_finalize(&drv->spi_queue, hspi->pRxBuffPtr, SPI_PACKET_SIZE);
    drv->spi_rx_running = false;
    start_spi_dma(drv);
  }
}

uint32_t ble_hal_ext_receive(uint8_t *data, uint32_t len) {
  ble_hal_driver_t *drv = &g_ble_hal_driver;
  if (!drv->initialized) {
    return 0;
  }

  spi_rx_queue_t *queue = &drv->spi_queue;

  uint16_t read_len = 0;

  bool received = spi_rx_queue_read(queue, data, len, &read_len);

  if (!drv->spi_rx_running) {
    start_spi_dma(drv);
  }

  if (received) {
    if (data[0] != '?') {
      // bad packet, restart the DMA
      HAL_SPI_Abort(&drv->spi);
      irq_key_t key = irq_lock();
      spi_rx_queue_init(queue);
      uint8_t *buffer = spi_rx_queue_allocate(queue);
      irq_unlock(key);
      if (buffer != NULL) {
        HAL_SPI_Receive_DMA(&drv->spi, buffer, BLE_PACKET_SIZE);
      }
      return 0;
    }
    return len > BLE_PACKET_SIZE ? BLE_PACKET_SIZE : len;
  }

  return 0;
}

/// GPIO communication ---------------------------------------------------------

bool ble_hal_reboot_to_bootloader(void) {
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

bool ble_hal_reboot(void) {
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
  HAL_Delay(50);
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
  return true;
}

void ble_hal_signal_running(void) {
  HAL_GPIO_WritePin(GPIO_3_PORT, GPIO_3_PIN, GPIO_PIN_SET);
}

void ble_hal_signal_off(void) {
  HAL_GPIO_WritePin(GPIO_3_PORT, GPIO_3_PIN, GPIO_PIN_RESET);
}

bool ble_hal_firmware_running(void) {
  return HAL_GPIO_ReadPin(GPIO_2_PORT, GPIO_2_PIN) != 0;
}

#endif
