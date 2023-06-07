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
#include "buffers.h"
#include "dma.h"
#include "int_comm_defs.h"
#include "messages.h"
#include "state.h"

#define SPI_QUEUE_SIZE 10

static UART_HandleTypeDef urt;

static SPI_HandleTypeDef spi = {0};
static DMA_HandleTypeDef spi_dma = {0};

typedef struct {
  uint8_t buffer[BLE_PACKET_SIZE];
  bool used;
  bool ready;
} spi_buffer_t;

BUFFER_SECTION spi_buffer_t spi_queue[SPI_QUEUE_SIZE];
static int head = 0, tail = 0;
static bool overrun = false;
volatile uint16_t overrun_count = 0;
volatile uint16_t msg_cntr = 0;
volatile uint16_t first_overrun_at = 0;

static uint8_t int_comm_buffer[USB_DATA_SIZE];
static uint16_t int_comm_msg_len = 0;
static uint8_t int_event_buffer[USB_DATA_SIZE];
static uint16_t int_event_msg_len = 0;

static bool dfu_mode = false;

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
  __HAL_RCC_SPI1_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  GPIO_InitStructure.Pin = GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_5;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);
  //  GPIO_InitStructure.Pin = GPIO_PIN_9;
  //  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  dma_init(&spi_dma, &dma_SPI_1_RX, DMA_PERIPH_TO_MEMORY, &spi);

  spi.Instance = SPI1;
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

  HAL_SPI_Receive_DMA(&spi, spi_queue[0].buffer, BLE_PACKET_SIZE);
  spi_queue[0].used = true;

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_2_PIN;
  HAL_GPIO_Init(GPIO_2_PORT, &GPIO_InitStructure);

  tail = 0;
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
      //    case INTERNAL_EVENT_INITIALIZED: {
      //      set_connected(false);
      //      set_initialized(true);
      //      break;
      //    }
    case INTERNAL_EVENT_STATUS: {
      set_connected(data[1]);
      set_advertising(data[2]);
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

void ble_uart_receive(void) {
  if (urt.Instance->SR & USART_SR_RXNE) {
    uint8_t init_byte = 0;

    HAL_UART_Receive(&urt, &init_byte, 1, 1);

    if (init_byte == INTERNAL_EVENT || init_byte == INTERNAL_MESSAGE) {
      uint8_t len_hi = 0;
      uint8_t len_lo = 0;
      HAL_UART_Receive(&urt, &len_hi, 1, 1);
      HAL_UART_Receive(&urt, &len_lo, 1, 1);

      uint16_t act_len = (len_hi << 8) | len_lo;

      if (act_len > UART_PACKET_SIZE) {
        flush_line();
        return;
      }

      uint8_t *data = NULL;
      uint16_t *len = NULL;
      if (init_byte == INTERNAL_EVENT) {
        data = int_event_buffer;
        len = &int_event_msg_len;
      } else if (init_byte == INTERNAL_MESSAGE) {
        data = int_comm_buffer;
        len = &int_comm_msg_len;
      } else {
        memset(data, 0, USB_DATA_SIZE);
        *len = 0;
        flush_line();
        return;
      }

      HAL_StatusTypeDef result =
          HAL_UART_Receive(&urt, data, act_len - OVERHEAD_SIZE, 5);

      if (result != HAL_OK) {
        memset(data, 0, USB_DATA_SIZE);
        *len = 0;
        flush_line();
        return;
      }

      uint8_t eom = 0;
      HAL_UART_Receive(&urt, &eom, 1, 1);

      if (eom == EOM) {
        *len = act_len - OVERHEAD_SIZE;
      } else {
        memset(data, 0, USB_DATA_SIZE);
        *len = 0;
        flush_line();
      }
    } else {
      flush_line();
    }
  }
  //
}

void ble_set_dfu_mode(bool dfu) { dfu_mode = dfu; }

void ble_event_poll() {
  ble_uart_receive();

  if (int_event_msg_len > 0) {
    process_poll(int_event_buffer, int_event_msg_len);
    memset(int_event_buffer, 0, USB_DATA_SIZE);
    int_event_msg_len = 0;
  }

  if (!ble_initialized() && !dfu_mode && ble_firmware_running()) {
    send_state_request();
  }
}

bool ble_firmware_running(void) {
  return HAL_GPIO_ReadPin(GPIO_2_PORT, GPIO_2_PIN) != 0;
}

uint32_t ble_int_event_receive(uint8_t *data, uint32_t len) {
  ble_uart_receive();
  if (int_event_msg_len > 0) {
    memcpy(data, int_event_buffer,
           int_event_msg_len > len ? len : int_event_msg_len);
    memset(int_event_buffer, 0, USB_DATA_SIZE);
    uint32_t res = int_event_msg_len;
    int_event_msg_len = 0;
    return res;
  }
  return 0;
}

uint32_t ble_int_comm_receive(uint8_t *data, uint32_t len) {
  ble_uart_receive();
  if (int_comm_msg_len > 0) {
    memcpy(data, int_comm_buffer,
           int_comm_msg_len > len ? len : int_comm_msg_len);
    memset(int_comm_buffer, 0, USB_DATA_SIZE);
    uint32_t res = int_comm_msg_len;
    int_comm_msg_len = 0;
    return res;
  }
  return 0;
}

bool start_spi_dma(void) {
  int tmp_tail = (tail + 1) % SPI_QUEUE_SIZE;
  if (spi_queue[tmp_tail].used || spi_queue[tmp_tail].ready) {
    overrun = true;
    overrun_count++;
    if (first_overrun_at == 0) {
      first_overrun_at = msg_cntr;
    }
    return false;
  }
  spi_queue[tmp_tail].used = true;
  HAL_SPI_Receive_DMA(&spi, spi_queue[tmp_tail].buffer, BLE_PACKET_SIZE);

  tail = tmp_tail;
  return true;
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  spi_queue[tail].ready = true;
  msg_cntr++;
  start_spi_dma();
}

#include "supervise.h"

uint32_t ble_ext_comm_receive(uint8_t *data, uint32_t len) {
  svc_disableIRQ(DMA2_Stream0_IRQn);
  if (spi_queue[head].ready) {
    uint8_t *buffer = (uint8_t *)spi_queue[head].buffer;
    memcpy(data, buffer, len > BLE_PACKET_SIZE ? BLE_PACKET_SIZE : len);

    spi_queue[head].used = false;
    spi_queue[head].ready = false;
    head = (head + 1) % SPI_QUEUE_SIZE;

    if (overrun && start_spi_dma()) {
      // overrun was before, need to restart the DMA
      overrun = false;
    }

    if (data[0] != '?') {
      // bad packet, restart the DMA
      HAL_SPI_Abort(&spi);

      memset(spi_queue, 0, sizeof(spi_queue));
      head = 0;
      tail = 0;
      overrun = false;
      HAL_SPI_Receive_DMA(&spi, spi_queue[0].buffer, BLE_PACKET_SIZE);
      spi_queue[0].used = true;
      // todo return error?
      svc_enableIRQ(DMA2_Stream0_IRQn);

      return 0;
    }

    svc_enableIRQ(DMA2_Stream0_IRQn);
    return len > BLE_PACKET_SIZE ? BLE_PACKET_SIZE : len;
  }

  svc_enableIRQ(DMA2_Stream0_IRQn);
  return 0;
}
