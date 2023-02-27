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

static UART_HandleTypeDef urt;

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

void ble_int_comm_send(uint8_t *data, uint32_t len, bool internal) {
  uint16_t msg_len = len + 4;
  uint8_t len_hi = msg_len >> 8;
  uint8_t len_lo = msg_len & 0xFF;
  uint8_t eom = 0x55;

  uint8_t init_byte = 0;
  if (internal) {
    init_byte = 0xA0;
  } else {
    init_byte = 0xA1;
  }

  HAL_UART_Transmit(&urt, &init_byte, 1, 1);
  HAL_UART_Transmit(&urt, &len_hi, 1, 1);
  HAL_UART_Transmit(&urt, &len_lo, 1, 1);

  HAL_UART_Transmit(&urt, data, len, 10);
  HAL_UART_Transmit(&urt, &eom, 1, 1);
}

uint32_t ble_int_comm_receive(uint8_t *data, uint32_t len, bool *internal) {
  data[0] = 0;
  if (urt.Instance->SR & USART_SR_RXNE) {
    uint8_t init_byte = 0;
    HAL_UART_Receive(&urt, &init_byte, 1, 1);

    if (init_byte == 0xA0 || init_byte == 0xA1) {
      uint8_t len_hi = 0;
      uint8_t len_lo = 0;
      HAL_UART_Receive(&urt, &len_hi, 1, 1);
      HAL_UART_Receive(&urt, &len_lo, 1, 1);

      uint16_t act_len = (len_hi << 8) | len_lo;

      HAL_StatusTypeDef result = HAL_UART_Receive(&urt, data, act_len - 4, 5);

      if (result != HAL_OK) {
        return 0;
      }

      uint8_t eom = 0;
      HAL_UART_Receive(&urt, &eom, 1, 1);

      if (eom == 0x55) {
        if (init_byte == 0xA0) {
          *internal = true;
        } else {
          *internal = false;
        }
        return act_len - 4;
      }
      return 0;

    } else {
      // disregard byte.
      // todo: flush everything on the line, also for other errors
      return 0;
    }
  }

  return 0;
}
