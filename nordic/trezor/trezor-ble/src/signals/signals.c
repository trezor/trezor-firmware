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

#define OUT_RESERVED DK_LED1

#define IN_STAY_IN_BOOTLOADER DK_BTN1_MSK

static K_SEM_DEFINE(signals_ok, 0, 1);

static bool out_reserved = false;

void button_changed(uint32_t button_state, uint32_t has_changed) {}

static void configure_gpio(void) {
  int err;

  err = dk_buttons_init(button_changed);
  if (err) {
    LOG_ERR("Cannot init INPUT (err: %d)", err);
  }

  err = dk_leds_init();
  if (err) {
    LOG_ERR("Cannot init OUTPUT (err: %d)", err);
  }
}

bool signals_is_stay_in_bootloader(void) {
  return (dk_get_buttons() & IN_STAY_IN_BOOTLOADER) != 0;
}

bool signals_init(void) {
  configure_gpio();

  k_sem_give(&signals_ok);

  return true;
}

void signals_set_reserved(bool set) {
  out_reserved = set;
  dk_set_led(OUT_RESERVED, set);
}

bool signals_out_get_reserved(void) { return out_reserved; }
