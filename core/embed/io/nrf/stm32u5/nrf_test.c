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
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/nrf.h>
#include <sec/secret_keys.h>
#include <sys/systick.h>

#include "../nrf_internal.h"
#include "sys/irq.h"

typedef enum {
  PRODTEST_CMD_SPI_DATA = 0x00,
  PRODTEST_CMD_UART_DATA = 0x01,
  PRODTEST_CMD_SET_OUTPUT = 0x02,
  PRODTEST_CMD_PAIR = 0x03,
} prodtest_cmd_t;

typedef enum {
  PRODTEST_RESP_SPI = 0x00,
  PRODTEST_RESP_UART = 0x01,
  PRODTEST_RESP_SUCCESS = 0x02,
  PRODTEST_RESP_FAILURE = 0x03,
} prodtest_resp_t;

typedef struct {
  bool answered_spi;
  bool success;
  bool failure;

} nrf_test_t;

static nrf_test_t g_nrf_test;

void nrf_test_cb(const uint8_t *data, uint32_t len) {
  switch (data[0]) {
    case PRODTEST_RESP_SPI:
      g_nrf_test.answered_spi = true;
      break;
    case PRODTEST_RESP_SUCCESS:
      g_nrf_test.success = true;
      break;
    case PRODTEST_RESP_FAILURE:
      g_nrf_test.failure = true;
      break;
    default:
      break;
  }
}

bool nrf_test_spi_comm(void) {
  nrf_register_listener(NRF_SERVICE_PRODTEST, nrf_test_cb);

  g_nrf_test.answered_spi = false;

  uint8_t data[1] = {PRODTEST_CMD_SPI_DATA};

  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, 1, NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (g_nrf_test.answered_spi) {
      return true;
    }
  }

  return false;
}

bool nrf_test_uart_comm(void) {
  nrf_register_listener(NRF_SERVICE_PRODTEST, nrf_test_cb);

  bool result = true;

  uint8_t data[1] = {MGMT_CMD_START_UART};
  if (!nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL)) {
    return false;
  }

  systick_delay_ms(10);

  nrf_uart_send(0xAB);

  systick_delay_ms(10);

  uint8_t rx = nrf_uart_get_received();

  if (rx != 0xAB) {
    result = false;
    goto cleanup;
  }

cleanup:
  data[0] = MGMT_CMD_STOP_UART;
  if (!nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL)) {
    return false;
  }
  return result;
}

bool nrf_test_reset(void) {
  bool result = false;
  uint8_t data[2] = {PRODTEST_CMD_SET_OUTPUT, 1};
  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL)) {
    return false;
  }

  systick_delay_ms(10);

  if (!nrf_in_reserved()) {
    result = false;
    goto cleanup;
  }

  nrf_stop();
  nrf_reboot();

  systick_delay_ms(10);

  if (nrf_in_reserved()) {
    result = false;
    goto cleanup;
  }

  result = true;

  systick_delay_ms(1000);

cleanup:
  nrf_start();
  return result;
}

bool nrf_test_gpio_stay_in_bld(void) {
  bool result = false;
  nrf_stay_in_bootloader(false);
  systick_delay_ms(10);

  nrf_info_t info = {0};
  if (!nrf_get_info(&info)) {
    result = false;
    goto cleanup;
  }

  if (info.in_stay_in_bootloader) {
    result = false;
    goto cleanup;
  }

  nrf_stay_in_bootloader(true);
  systick_delay_ms(10);
  if (!nrf_get_info(&info)) {
    result = false;
    goto cleanup;
  }

  if (!info.in_stay_in_bootloader) {
    result = false;
    goto cleanup;
  }

  result = true;

cleanup:
  nrf_stay_in_bootloader(false);
  return result;
}

bool nrf_test_gpio_reserved(void) {
  bool result = false;
  uint8_t data[2] = {PRODTEST_CMD_SET_OUTPUT, 0};
  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL)) {
    return false;
  }

  systick_delay_ms(10);

  if (nrf_in_reserved()) {
    result = false;
    goto cleanup;
  }

  data[1] = 1;
  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL)) {
    result = false;
    goto cleanup;
  }

  systick_delay_ms(10);

  if (!nrf_in_reserved()) {
    result = false;
    goto cleanup;
  }

  result = true;

cleanup:
  data[1] = 0;
  nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL);
  return result;
}

#ifdef SECURE_MODE
#ifdef USE_NRF_AUTH
bool nrf_test_pair(void) {
  nrf_register_listener(NRF_SERVICE_PRODTEST, nrf_test_cb);

  g_nrf_test.success = false;
  g_nrf_test.failure = false;

  uint8_t data[NRF_PAIRING_SECRET_SIZE + 1] = {PRODTEST_CMD_PAIR};

  if (sectrue != secret_key_nrf_pairing(&data[1])) {
    return false;
  }

  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    irq_key_t irq_key = irq_lock();
    bool success = g_nrf_test.success;
    bool failure = g_nrf_test.failure;
    irq_unlock(irq_key);

    if (success) {
      return true;
    }
    if (failure) {
      return false;
    }
  }

  return false;
}
#endif
#endif

#endif
