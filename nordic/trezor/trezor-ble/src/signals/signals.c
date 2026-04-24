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

#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include <signals/signals.h>

#define LOG_MODULE_NAME signals
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static const struct gpio_dt_spec stay_in_bootloader_btn =
    GPIO_DT_SPEC_GET(DT_ALIAS(stay_in_bootloader), gpios);
static const struct gpio_dt_spec reserved_output =
    GPIO_DT_SPEC_GET(DT_ALIAS(reserved_output), gpios);

static K_SEM_DEFINE(signals_ok, 0, 1);

static bool out_reserved = false;

bool signals_init(void) {
  int err;

  err = gpio_pin_configure_dt(&stay_in_bootloader_btn, GPIO_INPUT);
  if (err) {
    LOG_ERR("Cannot configure bootloader button (err: %d)", err);
    return false;
  }

  err = gpio_pin_configure_dt(&reserved_output, GPIO_OUTPUT_INACTIVE);
  if (err) {
    LOG_ERR("Cannot configure reserved output (err: %d)", err);
    return false;
  }

  k_sem_give(&signals_ok);

  return true;
}

bool signals_is_stay_in_bootloader(void) {
  return gpio_pin_get_dt(&stay_in_bootloader_btn) > 0;
}

void signals_set_reserved(bool set) {
  int rc = gpio_pin_set_dt(&reserved_output, set);
  if (rc < 0) {
    LOG_ERR("Failed to set reserved output: %d", rc);
    return;
  }
  out_reserved = set;
}

bool signals_out_get_reserved(void) { return out_reserved; }
