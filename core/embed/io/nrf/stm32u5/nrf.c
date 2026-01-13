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
#include <io/tsqueue.h>
#include <sec/secret_keys.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/rng.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef USE_SUSPEND
#include <sys/suspend.h>
#endif

#include "../crc8.h"
#include "../nrf_internal.h"

#define CTS_PULSE_RESEND_PERIOD_US 2000

nrf_driver_t g_nrf_driver = {0};

void nrf_start(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  tsqueue_reset(&drv->tx_queue);

  drv->comm_running = true;

  if (HAL_GPIO_ReadPin(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN) ==
      GPIO_PIN_SET) {
    nrf_prepare_spi_data(drv);
  }
}

void nrf_complete_current_request(nrf_driver_t *drv, nrf_status_t status) {
  if (drv->tx_request_id >= 0) {
    if (drv->tx_request.callback != NULL) {
      drv->tx_request.callback(status, drv->tx_request.context);
    }
    drv->tx_request_id = -1;
    memset(&drv->tx_request, 0, sizeof(nrf_tx_request_t));
  }
}

static void nrf_abort_comm(nrf_driver_t *drv) {
  HAL_SPI_Abort(&drv->spi);
  drv->pending_spi_transaction = false;

  nrf_complete_current_request(drv, NRF_STATUS_ERROR);

  while (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_request,
                         sizeof(nrf_tx_request_t), NULL, NULL)) {
    if (drv->tx_request.callback != NULL) {
      drv->tx_request.callback(NRF_STATUS_ERROR, drv->tx_request.context);
    }
  }

  memset(&drv->tx_request, 0, sizeof(nrf_tx_request_t));

  tsqueue_reset(&drv->tx_queue);
}

void nrf_stop(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  // nrf_signal_off();
  irq_key_t key = irq_lock();
  drv->comm_running = false;
  nrf_abort_comm(drv);
  irq_unlock(key);
}

void nrf_management_rx_cb(const uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  switch (data[0]) {
    case MGMT_RESP_INFO:
      drv->info_valid = true;
      memcpy(&drv->info, &data[1], MIN(len - 1, sizeof(nrf_info_t)));
      break;
    case MGMT_RESP_AUTH_RESPONSE:
      drv->auth_data_valid = true;
      memcpy(&drv->auth_data, &data[1], MIN(len - 1, sizeof(drv->auth_data)));
      break;
    default:
      break;
  }
}

void nrf_timer_callback(void *context) {
  nrf_driver_t *drv = (nrf_driver_t *)context;
  if (drv->initialized && drv->pending_spi_transaction) {
    nrf_signal_data_ready();
    systick_delay_us(1);
    nrf_signal_no_data();
    systimer_set(drv->timer, 2000);
  }
}

void nrf_init(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    return;
  }

  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  memset(drv, 0, sizeof(*drv));
  tsqueue_init(&drv->tx_queue, drv->tx_queue_entries,
               (uint8_t *)drv->tx_buffers, sizeof(nrf_tx_request_t),
               TX_QUEUE_SIZE);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // synchronization signals
  NRF_OUT_RESET_CLK_ENA();
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_RESET_PIN;
  HAL_GPIO_Init(NRF_OUT_RESET_PORT, &GPIO_InitStructure);

  NRF_IN_RESERVED_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_RESERVED_PIN;
  HAL_GPIO_Init(NRF_IN_RESERVED_PORT, &GPIO_InitStructure);

  NRF_OUT_SPI_READY_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_SPI_READY_PIN;
  HAL_GPIO_Init(NRF_OUT_SPI_READY_PORT, &GPIO_InitStructure);

  NRF_OUT_STAY_IN_BLD_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_STAY_IN_BLD_PIN;
  HAL_GPIO_Init(NRF_OUT_STAY_IN_BLD_PORT, &GPIO_InitStructure);

  NRF_IN_SPI_REQUEST_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_SPI_REQUEST_PIN;
  HAL_GPIO_Init(NRF_IN_SPI_REQUEST_PORT, &GPIO_InitStructure);

  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NRF_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NRF_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&drv->exti, &EXTI_Config);
  __HAL_GPIO_EXTI_CLEAR_FLAG(NRF_EXTI_INTERRUPT_PIN);

#ifdef USE_SMP
  nrf_uart_init(drv);
#endif

  nrf_spi_init(drv);

  drv->tx_request_id = -1;

  drv->initialized = true;

  nrf_register_listener(NRF_SERVICE_MANAGEMENT, nrf_management_rx_cb);

  drv->timer = systimer_create(nrf_timer_callback, drv);
  nrf_start();

#ifdef USE_SMP
  NVIC_SetPriority(USART3_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(USART3_IRQn);
#endif
  NVIC_SetPriority(GPDMA1_Channel1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_SetPriority(GPDMA1_Channel2_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_SetPriority(SPI1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(SPI1_IRQn);
  NVIC_SetPriority(NRF_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(NRF_EXTI_INTERRUPT_NUM);

  if (HAL_GPIO_ReadPin(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN) ==
      GPIO_PIN_SET) {
    nrf_prepare_spi_data(drv);
  }
}

static void nrf_deinit_common(nrf_driver_t *drv) {
  nrf_stop();

  systimer_delete(drv->timer);

#ifdef USE_SMP
  NVIC_DisableIRQ(USART3_IRQn);
#endif
  NVIC_DisableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_DisableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_DisableIRQ(SPI1_IRQn);

  HAL_GPIO_DeInit(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN);
  HAL_GPIO_DeInit(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN);
  HAL_GPIO_DeInit(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN);
  HAL_GPIO_DeInit(NRF_IN_RESERVED_PORT, NRF_IN_RESERVED_PIN);

  // UART Pins
#ifdef USE_SMP
  nrf_uart_deinit();
#endif

  nrf_spi_deinit();

  drv->pending_spi_transaction = false;
}

void nrf_suspend(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  uint8_t data[1] = {MGMT_CMD_SUSPEND};
  nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL);

  systick_delay_ms(2);

  nrf_deinit_common(drv);

  drv->wakeup = true;
}

void nrf_resume(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  drv->timer = systimer_create(nrf_timer_callback, drv);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  NRF_OUT_RESET_CLK_ENA();
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_RESET_PIN;
  HAL_GPIO_Init(NRF_OUT_RESET_PORT, &GPIO_InitStructure);

  NRF_IN_RESERVED_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_RESERVED_PIN;
  HAL_GPIO_Init(NRF_IN_RESERVED_PORT, &GPIO_InitStructure);

  NRF_OUT_SPI_READY_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_SPI_READY_PIN;
  HAL_GPIO_Init(NRF_OUT_SPI_READY_PORT, &GPIO_InitStructure);

  NRF_OUT_STAY_IN_BLD_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_STAY_IN_BLD_PIN;
  HAL_GPIO_Init(NRF_OUT_STAY_IN_BLD_PORT, &GPIO_InitStructure);

#ifdef USE_SMP
  nrf_uart_init(drv);
#endif

  nrf_spi_init(drv);

#ifdef USE_SMP
  NVIC_EnableIRQ(USART3_IRQn);
#endif
  NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_EnableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_EnableIRQ(SPI1_IRQn);

  nrf_start();

  uint8_t data[1] = {MGMT_CMD_RESUME};
  nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL);
}

void nrf_deinit(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    NVIC_DisableIRQ(NRF_EXTI_INTERRUPT_NUM);

    HAL_GPIO_DeInit(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN);
    HAL_EXTI_ClearConfigLine(&drv->exti);

    nrf_deinit_common(drv);
    drv->initialized = false;
  }
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

void NRF_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;

#ifdef USE_SUSPEND
  if (drv->wakeup) {
    // Inform the power manager module about nrf/ble wakeup
    wakeup_flags_set(WAKEUP_FLAG_BLE);
    drv->wakeup = false;
  }
#endif

  if (drv->initialized && drv->comm_running) {
    if (HAL_GPIO_ReadPin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN) == 0) {
      nrf_prepare_spi_data(drv);
    }
  }
  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(NRF_EXTI_INTERRUPT_PIN);

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

/// GPIO communication
/// ---------------------------------------------------------
bool nrf_force_reset(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);
  return true;
}

bool nrf_reboot_to_bootloader(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);

  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_SET);

  systick_delay_ms(50);

  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);

  systick_delay_ms(100);

  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_RESET);

  return true;
}

void nrf_stay_in_bootloader(bool set) {
  if (set) {
    HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                      GPIO_PIN_SET);
  } else {
    HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                      GPIO_PIN_RESET);
  }
}

bool nrf_in_reserved(void) {
  return HAL_GPIO_ReadPin(NRF_IN_RESERVED_PORT, NRF_IN_RESERVED_PIN) != 0;
}

void nrf_reboot(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_RESET);
  systick_delay_ms(50);
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
}

void nrf_signal_data_ready(void) {
  HAL_GPIO_WritePin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN,
                    GPIO_PIN_SET);
}

void nrf_signal_no_data(void) {
  HAL_GPIO_WritePin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN,
                    GPIO_PIN_RESET);
}

bool nrf_is_running(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  // todo

  return drv->comm_running;
}

bool nrf_get_info(nrf_info_t *info) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  drv->info_valid = false;

  uint8_t data[1] = {MGMT_CMD_INFO};
  if (nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL) < 0) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (drv->info_valid) {
      memcpy(info, &drv->info, sizeof(nrf_info_t));
      return true;
    }
  }

  return false;
}

uint32_t nrf_get_version(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  drv->info_valid = false;

  uint8_t data[1] = {MGMT_CMD_INFO};
  if (nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL) < 0) {
    return 0;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (drv->info_valid) {
      uint32_t version = 0;
      version |= drv->info.version_major << 24;
      version |= drv->info.version_minor << 16;
      version |= drv->info.version_patch << 8;
      version |= drv->info.version_tweak;
      return version;
    }
  }

  return 0;
}

bool nrf_system_off(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  uint8_t data[1] = {MGMT_CMD_SYSTEM_OFF};
  if (!nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  bool finished = false;

  while (!ticks_expired(timeout) && !finished) {
    irq_key_t key = irq_lock();
    finished = tsqueue_empty(&drv->tx_queue) && !drv->pending_spi_transaction;
    irq_unlock(key);
    __WFI();
  }

  return true;
}

bool nrf_authenticate(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  uint32_t timeout = ticks_timeout(5000);

  // check that nRF communication is running prior to auth check
  while (!ticks_expired(timeout)) {
    if (nrf_get_info(&drv->info)) {
      break;
    }
  }

  drv->info_valid = false;

  uint32_t challenge[8] = {0};

  uint8_t data[1 + sizeof(challenge)] = {MGMT_CMD_AUTH_CHALLENGE};

  // generate random challenge
  rng_fill_buffer(challenge, sizeof(challenge));

  memcpy(data + 1, challenge, sizeof(challenge));

  drv->auth_data_valid = false;
  memset(drv->auth_data, 0, sizeof(drv->auth_data));

  if (nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, sizeof(data), NULL, NULL) <
      0) {
    return false;
  }

  timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (drv->auth_data_valid) {
      secbool auth =
          secret_validate_nrf_pairing((uint8_t *)challenge, sizeof(challenge),
                                      drv->auth_data, SHA256_DIGEST_LENGTH);
      return sectrue == auth;
    }
  }

  return false;
}

#endif
