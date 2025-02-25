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

#include <sys/systick.h>
#ifdef KERNEL_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/nrf.h>

#include "../nrf_internal.h"

typedef enum {
  PRODTEST_CMD_SPI_DATA = 0x00,
  PRODTEST_CMD_UART_DATA = 0x01,
  PRODTEST_CMD_SET_OUTPUT = 0x02,
} prodtest_cmd_t;

typedef enum {
  PRODTEST_RESP_SPI = 0x00,
  PRODTEST_RESP_UART = 0x01,
} prodtest_resp_t;

typedef struct {
  bool answered_spi;
  bool answered_uart;

} nrf_test_t;

static nrf_test_t g_nrf_test;

void nrf_test_cb(const uint8_t *data, uint32_t len) {
  switch (data[0]) {
    case PRODTEST_RESP_SPI:
      g_nrf_test.answered_spi = true;
      break;
    case PRODTEST_RESP_UART:
      g_nrf_test.answered_uart = true;
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

  g_nrf_test.answered_uart = false;

  uint8_t data[1] = {PRODTEST_CMD_UART_DATA};

  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, 1, NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (g_nrf_test.answered_uart) {
      return true;
    }
  }

  return false;
}

bool nrf_test_reboot_to_bootloader(void) {
  bool result = false;

  if (!nrf_firmware_running()) {
    return false;
  }

  if (!nrf_reboot_to_bootloader()) {
    return false;
  }

  uint32_t timeout = ticks_timeout(10);

  while (!ticks_expired(timeout)) {
    if (!nrf_firmware_running()) {
      result = true;
      break;
    }
  }

  systick_delay_ms(10);

  // todo test UART communication with MCUboot

  if (!nrf_reboot()) {
    return false;
  }

  timeout = ticks_timeout(1000);
  while (!ticks_expired(timeout)) {
    if (nrf_firmware_running()) {
      return result;
    }
  }

  return false;
}

bool nrf_test_gpio_trz_ready(void) {
  bool result = false;
  nrf_signal_running();
  systick_delay_ms(10);

  nrf_info_t info = {0};
  if (!nrf_get_info(&info)) {
    result = false;
    goto cleanup;
  }

  if (!info.in_trz_ready) {
    result = false;
    goto cleanup;
  }

  nrf_signal_off();
  systick_delay_ms(10);
  if (!nrf_get_info(&info)) {
    result = false;
    goto cleanup;
  }

  if (info.in_trz_ready) {
    result = false;
    goto cleanup;
  }

  result = true;

cleanup:
  nrf_signal_running();
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

  if (nrf_in_reserved_gpio()) {
    result = false;
    goto cleanup;
  }

  data[1] = 1;
  if (!nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL)) {
    result = false;
    goto cleanup;
  }

  systick_delay_ms(10);

  if (!nrf_in_reserved_gpio()) {
    result = false;
    goto cleanup;
  }

  result = true;

cleanup:
  data[1] = 0;
  nrf_send_msg(NRF_SERVICE_PRODTEST, data, sizeof(data), NULL, NULL);
  return result;
}

#endif
