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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/pmic.h>

#ifdef KERNEL_MODE

// Minimal PMIC driver for boards whose only power-management hardware is a
// GPIO power latch (soft power switch) on the PWR_ON pin.
//
// On boot the device is powered only while the user holds the power button;
// pmic_init() drives PWR_ON high to keep the supply enabled after the button
// is released. pmic_enter_shipmode() releases PWR_ON, cutting the supply and
// turning the device off - the latch's equivalent of ship mode.
//
// There is no battery gauge, charger or measurement hardware, so all such
// operations are no-ops.

bool pmic_init(void) {
  PWR_ON_CLK_EN();

  // Drive the output data register high first, so the pin latches power the
  // moment it is switched to push-pull output mode (avoids a glitch that could
  // briefly release the latch).
  HAL_GPIO_WritePin(PWR_ON_PORT, PWR_ON_PIN, GPIO_PIN_SET);

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = PWR_ON_PIN;
  HAL_GPIO_Init(PWR_ON_PORT, &GPIO_InitStructure);

  return true;
}

void pmic_deinit(void) {
  // Intentionally leave the latch engaged so the device stays powered.
}

bool pmic_enter_shipmode(void) {
  // Release the latch to cut the power supply and turn the device off.
  HAL_GPIO_WritePin(PWR_ON_PORT, PWR_ON_PIN, GPIO_PIN_RESET);
  return true;
}

uint8_t pmic_restart_cause(void) { return 0; }

bool pmic_suspend(void) { return true; }
bool pmic_resume(void) { return true; }
bool pmic_is_suspended(void) { return false; }

bool pmic_measure(pmic_report_callback_t callback, void* context) {
  (void)callback;
  (void)context;
  // No measurement hardware.
  return false;
}

bool pmic_measure_sync(pmic_report_t* report) {
  if (report != NULL) {
    memset(report, 0, sizeof(*report));
  }
  return false;
}

bool pmic_set_charging(bool enable) {
  (void)enable;
  return false;
}

bool pmic_set_charging_limit(int i_charge) {
  (void)i_charge;
  return false;
}

int pmic_get_charging_limit(void) { return 0; }

bool pmic_set_buck_mode(pmic_buck_mode_t buck_mode) {
  (void)buck_mode;
  return false;
}

bool pmic_clear_charger_errors(void) { return false; }

#endif  // KERNEL_MODE
