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

#ifndef TREZORHAL_POWERCTL_PMIC_H
#define TREZORHAL_POWERCTL_PMIC_H

#include <stdbool.h>

// Initialize PMIC driver
bool pmic_init(void);

// Deinitialize PMIC driver
void pmic_deinit(void);

//
bool pmic_shipmode(void);

typedef struct {
  float vbat;
  // float vbus;
  float vsys;
  float ibat;
  float ntc_temp;
  float die_temp;
  uint8_t ibat_meas_status;
  uint8_t ilim_status;
  uint8_t ntc_status;
  uint8_t die_temp_status;
  uint8_t charge_status;
  uint8_t usb_status;
  uint8_t vbus_status;

  uint8_t events_adc;
  uint8_t events_bcharger0;
  uint8_t events_bcharger1;
  uint8_t events_bcharger2;
  uint8_t events_shphld;
  uint8_t events_vbusin0;
  uint8_t events_vbusin1;
  uint8_t events_gpio;
} pmic_report_t;

bool pmic_measure_trigger(void);

//
bool pmic_measure(pmic_report_t* report);

bool pmic_charge_enable(bool enable);

//
uint8_t pmic_restart_cause(void);

#endif  // TREZORHAL_POWERCTL_PMIC_H
