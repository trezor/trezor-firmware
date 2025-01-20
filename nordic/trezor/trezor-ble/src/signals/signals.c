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
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <zephyr/types.h>

#include <signals/signals.h>

#include <dk_buttons_and_leds.h>

#define LOG_MODULE_NAME signals
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define RUN_STATUS_LED DK_LED1
#define RUN_LED_BLINK_INTERVAL 1000

#define FW_RUNNING_SIG DK_LED2

static K_SEM_DEFINE(led_init_ok, 0, 1);

void button_changed(uint32_t button_state, uint32_t has_changed) {}

static void configure_gpio(void) {
  int err;

  err = dk_buttons_init(button_changed);
  if (err) {
    LOG_ERR("Cannot init buttons (err: %d)", err);
  }

  err = dk_leds_init();
  if (err) {
    LOG_ERR("Cannot init LEDs (err: %d)", err);
  }
}

bool signals_is_trz_ready(void) {
  return (dk_get_buttons() & DK_BTN2_MSK) != 0;
}

bool signals_init(void) {
  configure_gpio();

  k_sem_give(&led_init_ok);

  return true;
}

void signals_fw_running(bool set) { dk_set_led(FW_RUNNING_SIG, set); }

void led_thread(void) {
  //  bool connected = false;
  int blink_status = 0;
  /* Don't go any further until BLE is initialized */
  k_sem_take(&led_init_ok, K_FOREVER);

  for (;;) {
    blink_status++;
    dk_set_led(RUN_STATUS_LED, (blink_status) % 2);

    //    connected = is_connected();
    //
    //    if (connected) {
    //      dk_set_led_on(CON_STATUS_LED);
    //    } else {
    //      if (is_advertising() && !is_advertising_whitelist()) {
    //        dk_set_led(CON_STATUS_LED, (blink_status) % 2);
    //      } else {
    //        dk_set_led_off(CON_STATUS_LED);
    //      }
    //    }

    k_sleep(K_MSEC(RUN_LED_BLINK_INTERVAL));
  }
}

K_THREAD_DEFINE(led_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE, led_thread,
                NULL, NULL, NULL, 7, 0, 0);
