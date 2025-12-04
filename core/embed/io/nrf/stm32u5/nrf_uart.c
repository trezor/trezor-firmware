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

#pragma GCC optimize("O0")

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/irq.h>
#include <sys/mpu.h>

#include "../nrf_internal.h"
#include "rust_smp.h"
#include "sys/systick.h"

#include <string.h>
#include <sys/dbg_console.h>

extern nrf_driver_t g_nrf_driver;

static void nrf_uart_init_peripherals(nrf_driver_t *drv, uint32_t baudrate) {
  __HAL_RCC_USART3_FORCE_RESET();
  __HAL_RCC_USART3_RELEASE_RESET();
  __HAL_RCC_USART3_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  // UART PINS
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART3;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Pin = GPIO_PIN_10 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Pin = GPIO_PIN_11;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_5;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->urt.Init.Mode = UART_MODE_TX_RX;
  drv->urt.Init.BaudRate = baudrate;
  drv->urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  drv->urt.Init.OverSampling = UART_OVERSAMPLING_16;
  drv->urt.Init.Parity = UART_PARITY_NONE;
  drv->urt.Init.StopBits = UART_STOPBITS_1;
  drv->urt.Init.WordLength = UART_WORDLENGTH_8B;
  drv->urt.Instance = USART3;
  HAL_UART_Init(&drv->urt);
}

void nrf_uart_init(nrf_driver_t *drv) {
  nrf_uart_init_peripherals(drv, 1000000);
}

void nrf_uart_deinit(void) {
  __HAL_RCC_USART3_FORCE_RESET();
  __HAL_RCC_USART3_RELEASE_RESET();
  HAL_GPIO_DeInit(GPIOB, GPIO_PIN_10);
  HAL_GPIO_DeInit(GPIOB, GPIO_PIN_1);
  HAL_GPIO_DeInit(GPIOD, GPIO_PIN_11);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_5);
}

void nrf_uart_send(uint8_t data) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  drv->urt_rx_complete = false;
  drv->urt_tx_complete = false;
  drv->urt_rx_byte = false;
  drv->urt_tx_byte = data;

  drv->urt_tx_byte = data;
  HAL_UART_Transmit(&drv->urt, (uint8_t *)&drv->urt_tx_byte, 1, 30);

  // receive the rest of the message, or new message in any case.
  HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
}

uint8_t nrf_uart_get_received(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (!drv->urt_rx_complete) {
    return 0;
  }

  return drv->urt_rx_byte;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
#ifdef USE_SMP
    if (nrf_is_dfu_mode()) {
#if 0
      dbg_printf("%c", drv->urt_rx_byte);
#endif

      smp_process_rx_byte(drv->urt_rx_byte);
      HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
      return;
    }
#endif

    if (drv->dtm_mode && drv->dtm_callback != NULL) {
      // DTM mode, call the callback with the received byte
      drv->dtm_callback(drv->urt_rx_byte);
      HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
    }

    drv->urt_rx_complete = true;
  }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    drv->dfu_tx_pending = false;
    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    drv->dfu_tx_pending = false;
    drv->urt_tx_complete = true;
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

bool nrf_send_uart_data(const uint8_t *data, uint32_t len,
                        uint32_t timeout_ms) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return false;
  }

  uint32_t deadline = ticks_timeout(timeout_ms);
  bool result = false;

  irq_key_t key = irq_lock();

  while (drv->dfu_tx_pending && !ticks_expired(deadline)) {
    // Wait for previous transmission to complete
    irq_unlock(key);
    key = irq_lock();
  }

  if (drv->dfu_tx_pending) {
    // If we are still pending, it means we timed out
    goto cleanup;
  }

  drv->dfu_tx_pending = true;

#if 0
  uint8_t data_temp[100];
  memcpy(data_temp, data, len);
  data_temp[len] = '\0';
  dbg_printf("%s:%s(..) executed, UART data TX: %d %s\n", __FILE_NAME__,
             __func__, len, data_temp);
#endif

  HAL_UART_Transmit_IT(&drv->urt, data, len);

  while (drv->dfu_tx_pending && !ticks_expired(deadline)) {
    // Wait for transmission to complete
    irq_unlock(key);
    key = irq_lock();
  }

  if (drv->dfu_tx_pending) {
    // If we are still pending, it means we timed out
    drv->dfu_tx_pending = false;
    HAL_UART_Abort_IT(&drv->urt);
    goto cleanup;
  }

  result = true;

cleanup:
  irq_unlock(key);
  return result;
}

void nrf_set_dtm_mode(bool set, void (*callback)(uint8_t byte)) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }
  drv->dtm_callback = callback;

  if (set) {
    HAL_UART_DeInit(&drv->urt);
    nrf_uart_init_peripherals(drv, 19200);
    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  } else if (drv->dtm_mode) {
    HAL_UART_DeInit(&drv->urt);
    nrf_uart_init_peripherals(drv, 1000000);
  }
  drv->dtm_mode = set;
}

void nrf_dtm_send_data(const uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }
  if (!drv->dtm_mode) {
    return;
  }
  HAL_UART_Transmit(&drv->urt, (uint8_t *)data, len, 30);
}

void nrf_set_dfu_mode(bool set) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  drv->dfu_mode = set;

  if (set) {
    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

bool nrf_is_dfu_mode(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->dfu_mode;
}

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

#endif
