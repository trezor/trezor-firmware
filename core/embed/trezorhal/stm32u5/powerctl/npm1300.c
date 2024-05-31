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

#include TREZOR_BOARD

#include <math.h>
#include <stdbool.h>
#include <stdint.h>

#include "i2c.h"
#include "npm1300.h"
#include "pmic.h"

// Default timeout for all I2C operations
#define NPM1300_I2C_TIMEOUT 10

static bool npm1300_set_reg(uint16_t addr, uint8_t value) {
  uint8_t tx_data[] = {addr >> 8, addr & 0xFF, value};

  return (HAL_OK == i2c_transmit(NPM1300_I2C_INSTANCE, NPM1300_I2C_ADDRESS,
                                 tx_data, sizeof(tx_data),
                                 NPM1300_I2C_TIMEOUT));
}

static bool npm1300_get_reg(uint16_t addr, uint8_t* data) {
  uint8_t tx_data[] = {addr >> 8, addr & 0xFF};

  if (HAL_OK != i2c_transmit(NPM1300_I2C_INSTANCE, NPM1300_I2C_ADDRESS, tx_data,
                             sizeof(tx_data), NPM1300_I2C_TIMEOUT)) {
    return false;
  }

  return (HAL_OK == i2c_receive(NPM1300_I2C_INSTANCE, NPM1300_I2C_ADDRESS, data,
                                sizeof(*data), NPM1300_I2C_TIMEOUT));
}

static bool npm1300_initialize(uint16_t i_charge, uint16_t i_limit) {
  uint16_t bchg_iset = i_charge / 2;                     // 2mA steps
  uint16_t bchg_iset_discharge = (i_limit * 100) / 323;  // 3.23mA steps
  uint16_t die_temp_stop = 360;                          // 110°C
  uint16_t die_temp_resume = 372;                        // 100°C
  uint16_t ntc_cold = 749;                               // 0°C
  uint16_t ntc_cool = 658;                               // 10°C
  uint16_t ntc_warm = 337;                               // 45°C
  uint16_t ntc_hot = 237;                                // 60°C

  struct {
    uint16_t addr;
    uint8_t value;
  } table[] = {
      {NPM1300_SCRATCH0, 0x00},
      {NPM1300_SCRATCH1, 0x00},
      // SYSREG
      {NPM1300_VBUSINILIM0, NPM1300_VBUSINILIM0_500MA},
      {NPM1300_VBUSSUSPEND, 0x00},
      {NPM1300_TASKUPDATEILIMSW, NPM1300_TASKUPDATEILIM_SELVBUSILIM0},
      // LOADSW/LDO
      {NPM1300_LDSW1GPISEL, 0x00},
      {NPM1300_LDSW2GPISEL, 0x00},
      {NPM1300_TASKLDSW1CLR, 0x01},
      {NPM1300_TASKLDSW2CLR, 0x01},
      // BUCK regulators
      //   TODO
      // ADC settings
      {NPM1300_ADCNTCRSEL, NPM1300_ADCNTCRSEL_10K},
      {NPM1300_ADCCONFIG, 0x00},
      {NPM1300_ADCIBATMEASEN, NPM1300_ADCIBATMEASEN_IBATMEASENABLE},
      // Charger settings
      {NPM1300_BCHGVTERM, NPM1300_BCHGVTERM_3V65},
      {NPM1300_BCHGVTERMR, NPM1300_BCHGVTERM_3V60},
      {NPM1300_BCHGVTRICKLESEL, NPM1300_BCHGVTRICKLESEL_2V5},
      {NPM1300_BCHGITERMSEL, NPM1300_BCHGITERMSEL_SEL10},
      {NPM1300_BCHGISETMSB, bchg_iset >> 1},
      {NPM1300_BCHGISETLSB, bchg_iset & 1},
      {NPM1300_BCHGISETDISCHARGEMSB, bchg_iset_discharge >> 1},
      {NPM1300_BCHGISETDISCHARGELSB, bchg_iset_discharge & 1},
      {NPM1300_BCHGDISABLECLR, NPM1300_BCHGDISABLECLR_USENTC},
      {NPM1300_BCHGDISABLECLR, NPM1300_BCHGDISABLECLR_ENABLERCHRG},
      {NPM1300_BCHGCONFIG, 0},
      // NTC thresholds
      {NPM1300_NTCCOLD, ntc_cold >> 2},
      {NPM1300_NTCCOLDLSB, ntc_cold & 0x3},
      {NPM1300_NTCCOOL, ntc_cool >> 2},
      {NPM1300_NTCCOOLLSB, ntc_cool & 0x3},
      {NPM1300_NTCWARM, ntc_warm >> 2},
      {NPM1300_NTCWARMLSB, ntc_warm & 0x3},
      {NPM1300_NTCHOT, ntc_hot >> 2},
      {NPM1300_NTCHOTLSB, ntc_hot & 0x3},
      // Die tempererature thresholds
      {NPM1300_DIETEMPSTOP, die_temp_stop >> 2},
      {NPM1300_DIETEMPSTOPLSB, die_temp_stop & 0x03},
      {NPM1300_DIETEMPRESUME, die_temp_resume >> 2},
      {NPM1300_DIETEMPRESUMELSB, die_temp_resume & 0x03},
      // LEDS
      {NPM1300_LEDDRV0MODESEL, NPM1300_LEDDRVMODESEL_ERROR},
      {NPM1300_LEDDRV1MODESEL, NPM1300_LEDDRVMODESEL_CHARGING},
      {NPM1300_LEDDRV2MODESEL, NPM1300_LEDDRVMODESEL_NOTUSED},
      // GPIO
      {NPM1300_GPIOMODE0, NPM1300_GPIOMODE_GPIINPUT},
      {NPM1300_GPIOMODE1, NPM1300_GPIOMODE_GPIINPUT},
      {NPM1300_GPIOMODE2, NPM1300_GPIOMODE_GPIINPUT},
      {NPM1300_GPIOMODE3, NPM1300_GPIOMODE_GPIINPUT},
      {NPM1300_GPIOMODE4, NPM1300_GPIOMODE_GPIINPUT},
      // POF
      {NPM1300_POFCONFIG, 0x00},
      // TIMER
      {NPM1300_TIMERCLR, 0x01},
      // Ship and hibernate mode
      // {NPM1300_SHPHLDCONFIG, .. },
      // {NPM1300_TASKSHPHLDCFGSTROBE, 0x01},

      // TODO automatic temp measurement during charging
  };

  for (int i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
    if (!npm1300_set_reg(table[i].addr, table[i].value)) {
      return false;
    }
  }

  return true;
}

// PMIC driver state
typedef struct {
  // Set if the PMIC driver is initialized
  bool initialized;
  // Content of RTSCAUSE register
  uint8_t restart_cause;

  // Charge current limit [mA]
  uint16_t i_charge;
  // Discharge current limit [mA]
  uint16_t i_limit;

} pmic_driver_t;

// PMIC driver instance
pmic_driver_t g_pmic_driver = {
    .initialized = false,
};

bool pmic_init(void) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (drv->initialized) {
    return true;
  }

  drv->i_charge = 180;  // mA  (32-800mA)
  drv->i_limit = 500;   // mA  (268mA-1340mA)

  if (!npm1300_initialize(drv->i_charge, drv->i_limit)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_RSTCAUSE, &drv->restart_cause)) {
    return false;
  }

  drv->initialized = true;
  return drv->initialized;
}

void pmic_deinit(void) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return;
  }

  // TODO

  drv->initialized = false;
}

bool pmic_shipmode(void) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return false;
  }

  // TODO

  return true;
}

bool pmic_measure_trigger(void) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!npm1300_set_reg(NPM1300_TASKVBATMEASURE, 1)) {
    return false;
  }

  if (!npm1300_set_reg(NPM1300_TASKVSYSMEASURE, 1)) {
    return false;
  }

  if (!npm1300_set_reg(NPM1300_TASKNTCMEASURE, 1)) {
    return false;
  }

  if (!npm1300_set_reg(NPM1300_TASKTEMPMEASURE, 1)) {
    return false;
  }

  return true;
}

bool pmic_measure(pmic_report_t* report) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return false;
  }

  uint8_t lsb = 0;
  uint8_t msb = 0;

  if (!npm1300_get_reg(NPM1300_ADCGP0RESULTLSBS, &lsb)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_ADCVBATRESULTMSB, &msb)) {
    return false;
  }

  uint16_t vbat_adc = (msb << 2) + (lsb & 0x03);

  if (!npm1300_get_reg(NPM1300_ADCNTCRESULTMSB, &msb)) {
    return false;
  }

  uint16_t ntc_adc = (msb << 2) + ((lsb >> 2) & 0x3);

  if (!npm1300_get_reg(NPM1300_ADCTEMPRESULTMSB, &msb)) {
    return false;
  }

  uint16_t die_adc = (msb << 2) + ((lsb >> 4) & 0x3);

  if (!npm1300_get_reg(NPM1300_ADCVSYSRESULTMSB, &msb)) {
    return false;
  }

  uint16_t vsys_adc = (msb << 2) + ((lsb >> 6) & 0x03);

  if (!npm1300_get_reg(NPM1300_ADCGP1RESULTLSBS, &lsb)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_ADCVBAT2RESULTMSB, &msb)) {
    return false;
  }

  uint16_t ibat_adc = (msb << 2) + ((lsb >> 4) & 0x03);

  uint8_t ibat_meas_status = 0;

  if (!npm1300_get_reg(NPM1300_ADCIBATMEASSTATUS, &ibat_meas_status)) {
    return false;
  }

  // ibat_meas_status:
  // 00100 - discharge
  // 01000 - usb powered, not charging
  // 01100 - charge trickle
  // 01110 - charge cool
  // 01111 - charge normal
  // 1XXXX - invalid value, start measure again

  // bool ibat_invalid = (ibat_meas_status & 0x10) != 0;
  bool ibat_discharging = ((ibat_meas_status >> 2) & 0x03) == 1;
  bool ibat_charging = ((ibat_meas_status >> 2) & 0x03) == 3;

  if (ibat_discharging) {
    report->ibat = ((int)ibat_adc * drv->i_limit) / 1250;
  } else if (ibat_charging) {
    report->ibat = -((int)ibat_adc * drv->i_charge) / 800;
  } else {
    report->ibat = 0;
  }

  report->vbat = (vbat_adc * 5.0) / 1023;
  float beta = 3380;
  report->ntc_temp =
      1 / (1 / 298.15 - (1 / beta) * logf(1024.0 / ntc_adc - 1)) - 298.15 +
      25.0;
  report->die_temp = 394.67 - 0.7926 * die_adc;
  report->vsys = (vsys_adc * 6.375) / 1023;
  report->ibat_meas_status = ibat_meas_status;

  uint8_t status = 0;

  if (!npm1300_get_reg(NPM1300_BCHGILIMSTATUS, &status)) {
    return false;
  }

  report->ilim_status = status;

  if (!npm1300_get_reg(NPM1300_NTCSTATUS, &status)) {
    return false;
  }

  report->ntc_status = status;

  if (!npm1300_get_reg(NPM1300_DIETEMPSTATUS, &status)) {
    return false;
  }

  report->die_temp_status = status;

  if (!npm1300_get_reg(NPM1300_BCHGCHARGESTATUS, &status)) {
    return false;
  }

  report->charge_status = status;

  if (!npm1300_get_reg(NPM1300_USBCDETECTSTATUS, &report->usb_status)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_VBUSINSTATUS, &report->vbus_status)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSADCCLR, &report->events_adc)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSBCHARGER0CLR, &report->events_bcharger0)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSBCHARGER1CLR, &report->events_bcharger1)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSBCHARGER2CLR, &report->events_bcharger2)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSSHPHLDCLR, &report->events_shphld)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSVBUSIN0CLR, &report->events_vbusin0)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSVBUSIN1CLR, &report->events_vbusin1)) {
    return false;
  }

  if (!npm1300_get_reg(NPM1300_EVENTSGPIOCLR, &report->events_gpio)) {
    return false;
  }

  return true;
}

bool pmic_charge_enable(bool enable) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (enable) {
    return npm1300_set_reg(NPM1300_BCHGENABLESET,
                           NPM1300_BCHGENABLESET_ENABLECHG);
  } else {
    return npm1300_set_reg(NPM1300_BCHGENABLECLR,
                           NPM1300_BCHGENABLECLR_DISABLECHG);
  }
}

uint8_t pmic_restart_cause(void) {
  pmic_driver_t* drv = &g_pmic_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->restart_cause;
}
