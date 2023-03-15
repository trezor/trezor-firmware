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

#include STM32_HAL_H
#include TREZOR_BOARD

#include "comm.h"
#include <string.h>
#include "dma.h"
#include "int_comm_defs.h"
#include "state.h"

#define SPI_PACKET_SIZE 64
#define SPI_QUEUE_SIZE 4

static UART_HandleTypeDef urt;
static uint8_t last_init_byte = 0;

static SPI_HandleTypeDef spi = {0};
static DMA_HandleTypeDef spi_dma = {0};

typedef struct {
  uint8_t buffer[SPI_PACKET_SIZE];
  bool used;
  bool ready;
} spi_buffer_t;

spi_buffer_t spi_queue[SPI_QUEUE_SIZE];
static int head = 0, tail = 0;
static bool overrun = 1;

void ble_comm_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  __HAL_RCC_USART1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  GPIO_InitStructure.Pin = GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  urt.Init.Mode = UART_MODE_TX_RX;
  urt.Init.BaudRate = 1000000;
  urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  urt.Init.OverSampling = UART_OVERSAMPLING_16;
  urt.Init.Parity = UART_PARITY_NONE, urt.Init.StopBits = UART_STOPBITS_1;
  urt.Init.WordLength = UART_WORDLENGTH_8B;
  urt.Instance = USART1;

  HAL_UART_Init(&urt);

  __HAL_RCC_DMA2_CLK_ENABLE();
  __HAL_RCC_SPI4_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();

  GPIO_InitStructure.Pin = GPIO_PIN_2 | GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI4;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  dma_init(&spi_dma, &dma_SPI_4_RX, DMA_PERIPH_TO_MEMORY, &spi);

  spi.Instance = SPI4;
  spi.Init.Mode = SPI_MODE_SLAVE;
  spi.Init.Direction = SPI_DIRECTION_2LINES;  // rx only?
  spi.Init.DataSize = SPI_DATASIZE_8BIT;
  spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  spi.Init.NSS = SPI_NSS_HARD_INPUT;
  spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  spi.Init.TIMode = SPI_TIMODE_DISABLE;
  spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  spi.Init.CRCPolynomial = 0;
  spi.hdmarx = &spi_dma;

  spi_dma.Parent = &spi;

  HAL_SPI_Init(&spi);

  set_initialized(false);

  HAL_SPI_Receive_DMA(&spi, spi_queue[0].buffer, 64);
}

void ble_comm_send(uint8_t *data, uint32_t len) {
  HAL_UART_Transmit(&urt, data, len, 30);
}

uint32_t ble_comm_receive(uint8_t *data, uint32_t len) {
  if (urt.Instance->SR & USART_SR_RXNE) {
    HAL_StatusTypeDef result = HAL_UART_Receive(&urt, data, len, 30);

    if (result == HAL_OK) {
      return len;
    } else {
      if (urt.RxXferCount == len) {
        return 0;
      }
      return len - urt.RxXferCount - 1;
    }
  }
  return 0;
}

void ble_int_comm_send(uint8_t *data, uint32_t len, uint8_t message_type) {
  uint16_t msg_len = len + OVERHEAD_SIZE;
  uint8_t len_hi = msg_len >> 8;
  uint8_t len_lo = msg_len & 0xFF;
  uint8_t eom = EOM;

  HAL_UART_Transmit(&urt, &message_type, 1, 1);
  HAL_UART_Transmit(&urt, &len_hi, 1, 1);
  HAL_UART_Transmit(&urt, &len_lo, 1, 1);

  HAL_UART_Transmit(&urt, data, len, 10);
  HAL_UART_Transmit(&urt, &eom, 1, 1);
}

void process_poll(uint8_t *data, uint32_t len) {
  uint8_t cmd = data[0];

  switch (cmd) {
    case INTERNAL_EVENT_INITIALIZED: {
      set_connected(false);
      set_initialized(true);
      break;
    }
    case INTERNAL_EVENT_CONNECTED: {
      set_connected(true);
      set_initialized(true);
      break;
    }
    case INTERNAL_EVENT_DISCONNECTED: {
      set_connected(false);
      set_initialized(true);
      break;
    }
    default:
      break;
  }
}

void flush_line(void) {
  while (urt.Instance->SR & USART_SR_RXNE) {
    (void)urt.Instance->DR;
  }
}

uint32_t ble_int_comm_poll(void) {
  uint8_t data[64] = {0};
  if (urt.Instance->SR & USART_SR_RXNE) {
    uint8_t init_byte = 0;

    if (last_init_byte != 0) {
      if (last_init_byte == INTERNAL_EVENT) {
        init_byte = last_init_byte;
      } else {
        return 0;
      }
    } else {
      HAL_UART_Receive(&urt, &init_byte, 1, 1);
    }

    if (init_byte == INTERNAL_EVENT) {
      uint8_t len_hi = 0;
      uint8_t len_lo = 0;
      HAL_UART_Receive(&urt, &len_hi, 1, 1);
      HAL_UART_Receive(&urt, &len_lo, 1, 1);

      uint16_t act_len = (len_hi << 8) | len_lo;

      if (act_len > sizeof(data) + OVERHEAD_SIZE) {
        last_init_byte = 0;
        flush_line();
        return 0;
      }

      HAL_StatusTypeDef result =
          HAL_UART_Receive(&urt, data, act_len - OVERHEAD_SIZE, 5);

      if (result != HAL_OK) {
        last_init_byte = 0;
        flush_line();
        return 0;
      }

      uint8_t eom = 0;
      HAL_UART_Receive(&urt, &eom, 1, 1);

      if (eom == EOM) {
        process_poll(data, act_len - OVERHEAD_SIZE);
        last_init_byte = 0;
        return act_len - OVERHEAD_SIZE;
      }
      return 0;

    } else if (init_byte == INTERNAL_MESSAGE || init_byte == EXTERNAL_MESSAGE) {
      last_init_byte = init_byte;
    } else {
      flush_line();
    }
    return 0;
  }

  if (!ble_initialized()) {
    uint8_t cmd = INTERNAL_CMD_SEND_STATE;
    ble_int_comm_send(&cmd, sizeof(cmd), INTERNAL_EVENT);
  }

  return 0;
}

uint32_t ble_int_comm_receive(uint8_t *data, uint32_t len) {
  if (urt.Instance->SR & USART_SR_RXNE) {
    uint8_t init_byte = 0;

    if (last_init_byte != 0) {
      if (last_init_byte == INTERNAL_MESSAGE) {
        init_byte = last_init_byte;
      } else {
        return 0;
      }

    } else {
      HAL_UART_Receive(&urt, &init_byte, 1, 1);
    }

    if (init_byte == INTERNAL_MESSAGE) {
      uint8_t len_hi = 0;
      uint8_t len_lo = 0;
      HAL_UART_Receive(&urt, &len_hi, 1, 1);
      HAL_UART_Receive(&urt, &len_lo, 1, 1);

      uint16_t act_len = (len_hi << 8) | len_lo;

      if (act_len > len + OVERHEAD_SIZE) {
        last_init_byte = 0;
        flush_line();
        return 0;
      }

      HAL_StatusTypeDef result =
          HAL_UART_Receive(&urt, data, act_len - OVERHEAD_SIZE, 5);

      if (result != HAL_OK) {
        last_init_byte = 0;
        flush_line();
        return 0;
      }

      uint8_t eom = 0;
      HAL_UART_Receive(&urt, &eom, 1, 1);

      if (eom == EOM) {
        last_init_byte = 0;
        return act_len - OVERHEAD_SIZE;
      }
      return 0;

    } else if (init_byte == INTERNAL_EVENT) {
      last_init_byte = init_byte;
    } else {
      flush_line();
      return 0;
    }
  }

  return 0;
}

bool start_spi_dma(void) {
  if (spi_queue[tail].used || spi_queue[tail].ready) {
    overrun = true;
    return false;
  }
  spi_queue[tail].used = true;
  HAL_SPI_Receive_DMA(&spi, spi_queue[tail].buffer, SPI_PACKET_SIZE);
  return true;
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  spi_queue[tail].ready = true;
  tail = (tail + 1) % SPI_QUEUE_SIZE;
  start_spi_dma();
}

uint32_t ble_ext_comm_receive(uint8_t *data, uint32_t len) {
  if (spi_queue[head].ready) {
    uint8_t *buffer = (uint8_t *)spi_queue[head].buffer;
    memcpy(data, buffer, len > SPI_PACKET_SIZE ? SPI_PACKET_SIZE : len);

    spi_queue[head].used = false;
    spi_queue[head].ready = false;
    head = (head + 1) % SPI_QUEUE_SIZE;

    if (overrun && start_spi_dma()) {
      // overrun was before, need to restart the DMA
      overrun = false;
    }

    return len > SPI_PACKET_SIZE ? SPI_PACKET_SIZE : len;
  }

  return 0;
}
