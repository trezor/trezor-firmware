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

#include <math.h>

#include <io/pmic.h>
#include <sys/i2c_bus.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systimer.h>

#ifdef USE_SUSPEND
#include <io/suspend.h>
#endif

#include "npm1300_defs.h"

#ifdef KERNEL_MODE

// Default timeout for all I2C operations
#define NPM1300_I2C_TIMEOUT 10

// Maximum number of consecutive I2C errors after we report a fatal error
#define NPM1300_I2C_ERROR_LIMIT 3

// Delay inserted between the ADC trigger and the readout [ms]
#define NPM1300_ADC_READOUT_DELAY 80

// NPM1300 FSM states
typedef enum {
  NPM1300_STATE_IDLE = 0,
  NPM1300_STATE_CLEAR_EVENTS,
  NPM1300_STATE_CHARGING_ENABLE,
  NPM1300_STATE_CHARGING_DISABLE,
  NPM1300_STATE_CHARGING_LIMIT,
  NPM1300_STATE_BUCK_MODE_SET,
  NPM1300_STATE_ENTER_SHIPMODE,
  NPM1300_STATE_ADC_TRIGGER,
  NPM1300_STATE_ADC_WAIT,
  NPM1300_STATE_ADC_READOUT,
} npm1300_fsm_state_t;

typedef struct {
  uint8_t adc_gp0_result_lsbs;
  uint8_t adc_vbat_result_msb;
  uint8_t adc_nt_result_msb;
  uint8_t adc_temp_result_msb;
  uint8_t adc_vsys_result_msb;
  uint8_t adc_gp1_result_lsbs;
  uint8_t adc_vbat2_result_msb;
  uint8_t adc_ibat_meas_status;
  uint8_t charging_status;
  uint8_t charging_err;
  uint8_t charging_sensor_err;
  uint8_t buck_status;
  uint8_t usb_status;
} npm1300_adc_regs_t;

typedef struct {
  uint8_t bchg_iset_msb;
  uint8_t bchg_iset_lsb;

} npm1300_chlimit_regs_t;

typedef struct {
  uint8_t vbusin;

} npm1300_event_regs_t;

// NPM1300 PMIC driver state
typedef struct {
  // Set if the PMIC driver is initialized
  bool initialized;

  // EXTI handle
  EXTI_HandleTypeDef exti_handle;

  // I2C bus where the PMIC is connected
  i2c_bus_t* i2c_bus;
  // Number of consecutive I2C errors
  int i2c_errors;
  // Storage for the pending I2C packet
  i2c_packet_t pending_i2c_packet;

  // Timer used for waiting for the ADC conversion
  systimer_t* timer;

  // Content of RTSCAUSE register read during driver initialization
  uint8_t restart_cause;

  // Current state of the FSM
  npm1300_fsm_state_t state;

  // Set if the driver was requested to suspend background operations.
  // IF so, the driver waits until the last operation is finished,
  // then enters suspended mode.
  bool suspending;

  // Set if the driver's background operations are suspended.
  // In suspended mode, the driver does not start any new operations.
  bool suspended;

  // ADC register (global buffer used for ADC measurements)
  npm1300_adc_regs_t adc_regs;
  // Charging limit registers (global buffer used for charging limit)
  npm1300_chlimit_regs_t chlimit_regs;
  // Event registers (global buffer used for events readout)
  npm1300_event_regs_t event_regs;

  // Discharge current limit [mA]
  uint16_t i_limit;

  // Charge current limit [mA]
  uint16_t i_charge;            // written value
  uint16_t i_charge_requested;  // requested value
  uint16_t i_charge_set;        // value beeing written

  // Set if the charging is enabled
  bool charging;
  bool charging_requested;

  // Buck voltage regulator mode
  pmic_buck_mode_t buck_mode;            // written value
  pmic_buck_mode_t buck_mode_requested;  // requested value
  pmic_buck_mode_t buck_mode_set;        // value beeing written

  // Enter ship mode
  bool shipmode_requested;

  // Request flags for ADC measurements
  bool adc_trigger_requested;
  bool adc_readout_requested;

  // Request flag for clearing events and releasing INT line
  bool clear_events_requested;

  // Report callback used for asynchronous measurements
  pmic_report_callback_t report_callback;
  void* report_callback_context;

} npm1300_driver_t;

// PMIC driver instance
npm1300_driver_t g_npm1300_driver = {
    .initialized = false,
};

// forward declarations
static void npm1300_timer_callback(void* context);
static void npm1300_i2c_callback(void* context, i2c_packet_t* packet);
static void npm1300_fsm_continue(npm1300_driver_t* drv);

// Writes a value to the NPM1300 register
//
// This function is used only during driver initialization because
// it's synchronous and blocks the execution.
static bool npm1300_set_reg(i2c_bus_t* bus, uint16_t addr, uint8_t value) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 3,
          .data = {addr >> 8, addr & 0xFF, value},
      },
  };

  i2c_packet_t pkt = {
      .address = NPM1300_I2C_ADDRESS,
      .timeout = NPM1300_I2C_TIMEOUT,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return false;
  }

  return true;
}

// Reads a value from the NPM1300 register
//
// This function is used only during driver initialization because
// it's synchronous and blocks the execution.
static bool npm1300_get_reg(i2c_bus_t* bus, uint16_t addr, uint8_t* data) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {addr >> 8, addr & 0xFF},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = sizeof(*data),
          .ptr = data,
      },
  };

  i2c_packet_t pkt = {
      .address = NPM1300_I2C_ADDRESS,
      .timeout = NPM1300_I2C_TIMEOUT,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return false;
  }

  return true;
}

// Initializes the NPM1300 driver to the default state
static bool npm1300_initialize(i2c_bus_t* bus, uint16_t i_charge,
                               uint16_t i_limit) {
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
      {NPM1300_VBUSINILIMSTARTUP, NPM1300_VBUSINILIM0_500MA},
      {NPM1300_VBUSSUSPEND, 0x00},
      {NPM1300_TASKUPDATEILIMSW, NPM1300_TASKUPDATEILIM_SELVBUSILIM0},
      // LOADSW/LDO
      {NPM1300_LDSW1GPISEL, 0x00},
      {NPM1300_LDSW2GPISEL, 0x00},
      {NPM1300_TASKLDSW1CLR, 0x01},
      {NPM1300_TASKLDSW2CLR, 0x01},
      // BUCK regulators

      // NOTE: NPM1300 ERRATA #27
      // this settings adds 900uA on VBAT in case the BUCK1NORMVOUT selected
      // the same voltage as it is selected by external resistor.
      {NPM1300_BUCK1NORMVOUT, 19},  // 2.9V
      {NPM1300_BUCKSWCTRLSEL, 1},

      // Buck auto mode, Pull downs disabled
      {NPM1300_BUCKCTRL0, 0},  // Auto mode
      //
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
      // Disable charging
      {NPM1300_BCHGENABLECLR, NPM1300_BCHGENABLECLR_DISABLECHG},
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
      {NPM1300_LEDDRV0MODESEL, NPM1300_LEDDRVMODESEL_NOTUSED},
      {NPM1300_LEDDRV1MODESEL, NPM1300_LEDDRVMODESEL_NOTUSED},
      {NPM1300_LEDDRV2MODESEL, NPM1300_LEDDRVMODESEL_NOTUSED},
      // GPIO0
      {NPM1300_GPIOMODE0, NPM1300_GPIOMODE_GPOIRQ},  // GPIO0 as IRQ
      {NPM1300_GPIODRIVE0, 0x00},                    // 1mA
      {NPM1300_GPIOOPENDRAIN0, 0x00},                // Push-pull output
      // GPIO1-4
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
      // Clear all events
      {NPM1300_EVENTSADCCLR, 0xFF},
      {NPM1300_EVENTSBCHARGER0CLR, 0x3F},
      {NPM1300_EVENTSBCHARGER1CLR, 0x3F},
      {NPM1300_EVENTSBCHARGER2CLR, 0x07},
      {NPM1300_EVENTSSHPHLDCLR, 0x0F},
      {NPM1300_EVENTSVBUSIN0CLR, 0x3F},
      {NPM1300_EVENTSVBUSIN1CLR, 0x3F},
      {NPM1300_EVENTSGPIOCLR, 0x1F},
      // Disable all interrupts
      {NPM1300_INTENEVENTSADCCLR, 0xFF},
      {NPM1300_INTENEVENTSBCHARGER0CLR, 0x3F},
      {NPM1300_INTENEVENTSBCHARGER1CLR, 0x3F},
      {NPM1300_INTENEVENTSBCHARGER2CLR, 0x07},
      {NPM1300_INTENEVENTSSHPHLDCLR, 0x0F},
      {NPM1300_INTENEVENTSVBUSIN0CLR, 0x3F},
      {NPM1300_INTENEVENTSVBUSIN1CLR, 0x3F},
      {NPM1300_INTENEVENTSGPIOCLR, 0x1F},
      // Enable interrupts we are interested in
      {NPM1300_INTENEVENTSVBUSIN0SET, 0x01},  // VBUS detected

      // TODO automatic temp measurement during charging
  };

  for (int i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
    if (!npm1300_set_reg(bus, table[i].addr, table[i].value)) {
      return false;
    }
  }

  return true;
}

bool pmic_init(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(npm1300_driver_t));

  drv->i_charge = PMIC_CHARGING_LIMIT_DEFAULT;  // mA
  drv->i_limit = 500;                           // mA  (268mA-1340mA)

  drv->i_charge_set = drv->i_charge;
  drv->i_charge_requested = drv->i_charge;

  drv->buck_mode_requested = PMIC_BUCK_MODE_AUTO;
  drv->buck_mode_set = PMIC_BUCK_MODE_AUTO;
  drv->buck_mode = PMIC_BUCK_MODE_AUTO;

  drv->i2c_bus = i2c_bus_open(NPM1300_I2C_INSTANCE);
  if (drv->i2c_bus == NULL) {
    goto cleanup;
  }

  drv->timer = systimer_create(npm1300_timer_callback, drv);
  if (drv->timer == NULL) {
    goto cleanup;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // INT pin, active low, external pull-up
  NPM1300_INT_PIN_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NPM1300_INT_PIN;
  HAL_GPIO_Init(NPM1300_INT_PORT, &GPIO_InitStructure);

  // Setup interrupt line for the NPM1300
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NPM1300_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NPM1300_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&drv->exti_handle, &EXTI_Config);

  if (!npm1300_get_reg(drv->i2c_bus, NPM1300_RSTCAUSE, &drv->restart_cause)) {
    goto cleanup;
  }

  if (!npm1300_initialize(drv->i2c_bus, drv->i_charge, drv->i_limit)) {
    goto cleanup;
  }

  // Enable interrupt line
  NVIC_SetPriority(NPM1300_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_FLAG(NPM1300_INT_PIN);
  NVIC_EnableIRQ(NPM1300_EXTI_INTERRUPT_NUM);

  drv->initialized = true;

  return true;

cleanup:
  pmic_deinit();
  return false;
}

void pmic_deinit(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  NVIC_DisableIRQ(NPM1300_EXTI_INTERRUPT_NUM);
  HAL_EXTI_ClearConfigLine(&drv->exti_handle);

  i2c_bus_close(drv->i2c_bus);
  systimer_delete(drv->timer);

  memset(drv, 0, sizeof(npm1300_driver_t));
}

bool pmic_suspend(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->suspending = true;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_resume(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->suspending = false;
  drv->suspended = false;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_is_suspended(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  bool is_suspended;

  irq_key_t irq_key = irq_lock();
  is_suspended = drv->suspended;
  irq_unlock(irq_key);

  return is_suspended;
}

bool pmic_enter_shipmode(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->shipmode_requested = true;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

int pmic_get_charging_limit(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->i_charge_requested;
}

bool pmic_set_charging_limit(int i_charge) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  if (i_charge < PMIC_CHARGING_LIMIT_MIN ||
      i_charge > PMIC_CHARGING_LIMIT_MAX) {
    // The value is out of range
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->i_charge_requested = i_charge;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_set_charging(bool enable) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->charging_requested = enable;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_set_buck_mode(pmic_buck_mode_t buck_mode) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->buck_mode_requested = buck_mode;
  npm1300_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

uint8_t pmic_restart_cause(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->restart_cause;
}

bool pmic_measure(pmic_report_callback_t callback, void* context) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  if (drv->report_callback != NULL && callback != NULL) {
    // Cannot start another measurement while the previous one is in progress
    irq_unlock(irq_key);
    return false;
  }

  drv->report_callback = callback;
  drv->report_callback_context = context;

  if (drv->report_callback != NULL) {
    drv->adc_trigger_requested = true;
    npm1300_fsm_continue(drv);
  }

  irq_unlock(irq_key);

  return true;
}

// Synchronous measurement context structure
// (used internally within the `npm1300_measure_sync` function)
typedef struct {
  // Set when the measurement is done
  volatile bool done;
  // Report structure where the measurement is stored
  pmic_report_t* report;
} npm1300_sync_measure_t;

// Callback for the synchronous measurement
static void npm1300_sync_measure_callback(void* context,
                                          pmic_report_t* report) {
  npm1300_sync_measure_t* ctx = (npm1300_sync_measure_t*)context;
  *ctx->report = *report;
  ctx->done = true;
}

bool pmic_measure_sync(pmic_report_t* report) {
  npm1300_sync_measure_t measure = {
      .done = false,
      .report = report,
  };

  // Start asynchronous measurement
  if (!pmic_measure(npm1300_sync_measure_callback, &measure)) {
    return false;
  }

  // Wait for the measurement to finish
  while (!measure.done) {
    __WFI();
  }

  return true;
}

// Prepares PMIC report from the last readout of the ADC values
// stored in `drv->adc_regs`
//
// This function is called in the irq context.
static void npm1300_calculate_report(npm1300_driver_t* drv,
                                     pmic_report_t* report) {
  memset(report, 0, sizeof(pmic_report_t));

  npm1300_adc_regs_t* r = &drv->adc_regs;

  // Gather measured values from the ADC registers

  uint16_t vbat_adc =
      (r->adc_vbat_result_msb << 2) + (r->adc_gp0_result_lsbs & 0x03);

  uint16_t ntc_adc =
      (r->adc_nt_result_msb << 2) + ((r->adc_gp0_result_lsbs >> 2) & 0x3);

  uint16_t die_adc =
      (r->adc_temp_result_msb << 2) + ((r->adc_gp0_result_lsbs >> 4) & 0x3);

  uint16_t vsys_adc =
      (r->adc_vsys_result_msb << 2) + ((r->adc_gp0_result_lsbs >> 6) & 0x03);

  uint16_t ibat_adc =
      (r->adc_vbat2_result_msb << 2) + ((r->adc_gp1_result_lsbs >> 4) & 0x03);
  // IBAT_MEAS_STATUS register isn't well documented in the NPM1300 datasheet.
  // The following is based partially on observation.
  //
  // 00100 - discharge
  // 01000 - usb powered, not charging
  // 01100 - charge trickle
  // 01110 - charge cool
  // 01111 - charge normal
  // 1XXXX - invalid value, start measure again

  // bool ibat_invalid = (ibat_meas_status & 0x10) != 0;
  bool ibat_discharging = ((r->adc_ibat_meas_status >> 2) & 0x03) == 1;
  bool ibat_charging = ((r->adc_ibat_meas_status >> 2) & 0x03) == 3;

  // Calculate the battery current based on the ADC reading and operating state.
  // If discharging, use the discharge current limit (i_limit).
  // If charging, use the charge current limit (i_charge).
  // See the NPM1300 datasheet for details.
  if (ibat_discharging) {
    report->ibat = ((int)ibat_adc * drv->i_limit) / 1250.0;
  } else if (ibat_charging) {
    report->ibat = -((int)ibat_adc * drv->i_charge) / 800.0;
  } else {
    report->ibat = 0;
  }

  // Calculate the battery voltage (VBAT) from the ADC value.
  // VBAT is scaled by the voltage divider ratio and ADC resolution.
  report->vbat = (vbat_adc * 5.0) / 1023.0;

  // Calculate the temperature from the NTC (thermistor).
  // Beta value for the thermistor is specified as 3380.
  // The equation is derived from the NPM1300 datasheet.
  float beta = 3380;
  report->ntc_temp =
      1 / (1 / 298.15 - (1 / beta) * logf(1024.0 / ntc_adc - 1)) - 298.15 +
      25.0;

  // Calculate the die temperature from the die ADC reading.
  // The equation is derived from the NPM1300 datasheet.
  report->die_temp = 394.67 - 0.7926 * die_adc;

  // Calculate the system voltage (VSYS) from the ADC value.
  // VSYS is scaled based on the system voltage divider ratio and ADC
  // resolution.
  report->vsys = (vsys_adc * 6.375) / 1023.0;

  // Populate measurement and status flags from the raw data
  report->ibat_meas_status = r->adc_ibat_meas_status;
  report->buck_status = r->buck_status;
  report->usb_status = r->usb_status;
  report->charge_status = r->charging_status;
  report->charge_err = r->charging_err;
  report->charge_sensor_err = r->charging_sensor_err;
}

// I2C operation for writing constant value to the npm1300 register
#define NPM_WRITE_CONST(reg, value)                                    \
  {                                                                    \
    .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START, .size = 3, \
    .data = {(reg) >> 8, (reg) & 0xFF, (value)},                       \
  }

// I2C operations for the value of specified uint8_t field
// in `g_npm1300_driver` structure into npm1300 register
#define NPM_WRITE_FIELD(reg, field)                                  \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 2,                                                     \
      .data = {(reg) >> 8, (reg) & 0xFF},                            \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_TX, .size = 1, .ptr = &g_npm1300_driver.field, \
  }

// I2C operations for reading npm1300 register into the specified
// field in `g_npm1300_driver` structure
#define NPM_READ_FIELD(reg, field)                                   \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 2,                                                     \
      .data = {(reg) >> 8, (reg) & 0xFF},                            \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_RX, .size = 1, .ptr = &g_npm1300_driver.field, \
  }

// I2C operations for enabling of the charging
static const i2c_op_t npm1300_ops_charging_enable[] = {
    NPM_WRITE_CONST(NPM1300_BCHGENABLESET, NPM1300_BCHGENABLESET_ENABLECHG),
};

// I2C operations for disabling of the charging
static const i2c_op_t npm1300_ops_charging_disable[] = {
    NPM_WRITE_CONST(NPM1300_BCHGENABLECLR, NPM1300_BCHGENABLECLR_DISABLECHG),
};

// I2C operations for setting of the charging limit from
// `g_npm1300_driver.chlimit_regs` structure
static const i2c_op_t npm1300_ops_charging_limit[] = {
    NPM_WRITE_FIELD(NPM1300_BCHGISETMSB, chlimit_regs.bchg_iset_msb),
    NPM_WRITE_FIELD(NPM1300_BCHGISETLSB, chlimit_regs.bchg_iset_lsb),
};

static const i2c_op_t npm1300_ops_buck_auto[] = {
    NPM_WRITE_CONST(NPM1300_BUCKCTRL0, 0),
    NPM_WRITE_CONST(NPM1300_BUCK1PWMCLR, 1),
};

static const i2c_op_t npm1300_ops_buck_pwm[] = {
    NPM_WRITE_CONST(NPM1300_BUCKCTRL0, 0),
    NPM_WRITE_CONST(NPM1300_BUCK1PWMSET, 1),
};

static const i2c_op_t npm1300_ops_buck_pfm[] = {
    NPM_WRITE_CONST(NPM1300_BUCK1PWMCLR, 1),
    NPM_WRITE_CONST(NPM1300_BUCKCTRL0, 1),  // Auto mode
};

static const i2c_op_t npm1300_ops_enter_shipmode[] = {
    NPM_WRITE_CONST(NPM1300_TASKENTERSHIPMODE, 1),
};

// I2C operations for setting of the charging limit from
// `g_npm1300_driver.chlimit_regs` structure together with
// disabling and re-enabling of the charging
static const i2c_op_t npm1300_ops_charging_limit_reenable[] = {
    NPM_WRITE_CONST(NPM1300_BCHGENABLECLR, NPM1300_BCHGENABLECLR_DISABLECHG),
    NPM_WRITE_FIELD(NPM1300_BCHGISETMSB, chlimit_regs.bchg_iset_msb),
    NPM_WRITE_FIELD(NPM1300_BCHGISETLSB, chlimit_regs.bchg_iset_lsb),
    NPM_WRITE_CONST(NPM1300_BCHGENABLESET, NPM1300_BCHGENABLESET_ENABLECHG),
};

// I2C operations for triggering of the ADC measurements
static const i2c_op_t npm1300_ops_adc_trigger[] = {
    NPM_WRITE_CONST(NPM1300_TASKVBATMEASURE, 1),
    NPM_WRITE_CONST(NPM1300_TASKVSYSMEASURE, 1),
    NPM_WRITE_CONST(NPM1300_TASKNTCMEASURE, 1),
    NPM_WRITE_CONST(NPM1300_TASKTEMPMEASURE, 1),
};

// I2C operations for readout of the ADC values into the
// `g_npm1300_driver.adc_regs` structure
static const i2c_op_t npm1300_ops_adc_readout[] = {
    NPM_READ_FIELD(NPM1300_ADCGP0RESULTLSBS, adc_regs.adc_gp0_result_lsbs),
    NPM_READ_FIELD(NPM1300_ADCVBATRESULTMSB, adc_regs.adc_vbat_result_msb),
    NPM_READ_FIELD(NPM1300_ADCNTCRESULTMSB, adc_regs.adc_nt_result_msb),
    NPM_READ_FIELD(NPM1300_ADCTEMPRESULTMSB, adc_regs.adc_temp_result_msb),
    NPM_READ_FIELD(NPM1300_ADCVSYSRESULTMSB, adc_regs.adc_vsys_result_msb),
    NPM_READ_FIELD(NPM1300_ADCGP1RESULTLSBS, adc_regs.adc_gp1_result_lsbs),
    NPM_READ_FIELD(NPM1300_ADCVBAT2RESULTMSB, adc_regs.adc_vbat2_result_msb),
    NPM_READ_FIELD(NPM1300_ADCIBATMEASSTATUS, adc_regs.adc_ibat_meas_status),
    NPM_READ_FIELD(NPM1300_BCHGCHARGESTATUS, adc_regs.charging_status),
    NPM_READ_FIELD(NPM1300_BCHGERRREASON, adc_regs.charging_err),
    NPM_READ_FIELD(NPM1300_BCHGERRSENSOR, adc_regs.charging_sensor_err),
    NPM_READ_FIELD(NPM1300_BUCKSTATUS, adc_regs.buck_status),
    NPM_READ_FIELD(NPM1300_USBCDETECTSTATUS, adc_regs.usb_status),
};

// I2C operation that read & clears event flags and releases INT line
static const i2c_op_t npm1300_ops_clear_events[] = {
    NPM_READ_FIELD(NPM1300_VBUSINSTATUS, event_regs.vbusin),
    NPM_WRITE_CONST(NPM1300_EVENTSVBUSIN0CLR, 0x3F),
};

// Clear charger errors and release charging from error state
static const i2c_op_t npm1300_ops_clear_charger_errors[] = {
    NPM_WRITE_CONST(NPM1300_TASKCLEARCHGERR, 1),
    NPM_WRITE_CONST(NPM1300_TASKRELEASEERR, 1),
};

#define npm1300_i2c_submit(drv, ops) \
  _npm1300_i2c_submit(drv, ops, ARRAY_LENGTH(ops))

// helper function for submitting I2C operations
static void _npm1300_i2c_submit(npm1300_driver_t* drv, const i2c_op_t* ops,
                                size_t op_count) {
  i2c_packet_t* pkt = &drv->pending_i2c_packet;

  memset(pkt, 0, sizeof(i2c_packet_t));
  pkt->address = NPM1300_I2C_ADDRESS;
  pkt->context = drv;
  pkt->callback = npm1300_i2c_callback;
  pkt->timeout = NPM1300_I2C_TIMEOUT;
  pkt->ops = (i2c_op_t*)ops;
  pkt->op_count = op_count;

  i2c_status_t status = i2c_bus_submit(drv->i2c_bus, pkt);

  if (status != I2C_STATUS_OK) {
    // This should never happen
    error_shutdown("npm1300 I2C submit error");
  }
}

bool pmic_clear_charger_errors(void) {
  npm1300_driver_t* drv = &g_npm1300_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  npm1300_i2c_submit(drv, npm1300_ops_clear_charger_errors);
  irq_unlock(irq_key);

  return true;
}

// npm1300 driver timer callback invoked when `drv->timer` expires.
//
// This function is called in the irq context.
static void npm1300_timer_callback(void* context) {
  npm1300_driver_t* drv = (npm1300_driver_t*)context;

  switch (drv->state) {
    case NPM1300_STATE_ADC_WAIT:
      // The ADC conversion is done, read the values
      drv->adc_readout_requested = true;
      drv->state = NPM1300_STATE_IDLE;
      break;

    default:
      // we should never get here
      drv->state = NPM1300_STATE_IDLE;
      break;
  }

  npm1300_fsm_continue(drv);
}

// npm1300 driver I2C completion callback invoked when
// `drv->pending_i2c_packet` is completed
//
// This function is called in the irq context.
static void npm1300_i2c_callback(void* context, i2c_packet_t* packet) {
  npm1300_driver_t* drv = (npm1300_driver_t*)context;

  if (packet->status != I2C_STATUS_OK) {
    drv->i2c_errors++;

    if (drv->i2c_errors > NPM1300_I2C_ERROR_LIMIT) {
      error_shutdown("npm1300 I2C error");
    }

    drv->state = NPM1300_STATE_IDLE;

    // I2C operation will be retried until it succeeds or
    // the error limit is reached
    npm1300_fsm_continue(drv);
    return;
  }

  // If the I2C operation was successful, reset the error counter
  drv->i2c_errors = 0;

  switch (drv->state) {
    case NPM1300_STATE_CLEAR_EVENTS:
      drv->clear_events_requested = false;
      drv->state = NPM1300_STATE_IDLE;
#ifdef USE_SUSPEND
      wakeup_flags_set(WAKEUP_FLAG_POWER);
#endif
      break;

    case NPM1300_STATE_CHARGING_ENABLE:
      drv->charging = true;
      drv->state = NPM1300_STATE_IDLE;
      break;

    case NPM1300_STATE_CHARGING_DISABLE:
      drv->charging = false;
      drv->state = NPM1300_STATE_IDLE;
      break;

    case NPM1300_STATE_CHARGING_LIMIT:
      drv->i_charge = drv->i_charge_set;
      drv->state = NPM1300_STATE_IDLE;
      break;

    case NPM1300_STATE_BUCK_MODE_SET:
      drv->buck_mode = drv->buck_mode_set;
      drv->state = NPM1300_STATE_IDLE;
      break;

    case NPM1300_STATE_ENTER_SHIPMODE:
      drv->state = NPM1300_STATE_IDLE;
      break;

    case NPM1300_STATE_ADC_TRIGGER:
      drv->adc_trigger_requested = false;
      systimer_set(drv->timer, NPM1300_ADC_READOUT_DELAY);
      drv->state = NPM1300_STATE_ADC_WAIT;
      break;

    case NPM1300_STATE_ADC_READOUT:
      drv->adc_readout_requested = false;

      pmic_report_t report;
      npm1300_calculate_report(drv, &report);

      // Invoke report callback
      pmic_report_callback_t report_callback = drv->report_callback;
      void* report_callback_context = drv->report_callback_context;

      // Clear the report callback before invoking it
      // to allow the new measurement to be scheduled in the callback
      drv->report_callback = NULL;
      drv->report_callback_context = NULL;

      if (report_callback != NULL) {
        report_callback(report_callback_context, &report);
      }

      drv->state = NPM1300_STATE_IDLE;
      break;

    default:
      // we should never get here
      drv->state = NPM1300_STATE_IDLE;
      break;
  }

  npm1300_fsm_continue(drv);
}

void NPM1300_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  npm1300_driver_t* drv = &g_npm1300_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(NPM1300_INT_PIN);

  if (!drv->initialized) {
    mpu_restore(mpu_mode);
    IRQ_LOG_EXIT();
    return;
  }

  drv->clear_events_requested = true;
  npm1300_fsm_continue(drv);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

// npm1300 driver FSM continuation function that decides what to do next
//
// This function is called in the irq context or when interrupts are disabled.
static void npm1300_fsm_continue(npm1300_driver_t* drv) {
  if (drv->state != NPM1300_STATE_IDLE || drv->suspended) {
    return;
  }

  // The order of the following conditions defines the priority

  if (drv->clear_events_requested) {
    npm1300_i2c_submit(drv, npm1300_ops_clear_events);
    drv->state = NPM1300_STATE_CLEAR_EVENTS;
  } else if (drv->i_charge != drv->i_charge_requested) {
    // Change charging limit
    uint16_t bchg_iset = drv->i_charge / 2;  // 2mA steps
    drv->chlimit_regs.bchg_iset_msb = bchg_iset >> 1;
    drv->chlimit_regs.bchg_iset_lsb = bchg_iset & 1;
    drv->i_charge_set = drv->i_charge_requested;

    if (drv->charging) {
      // When charging is enabled, we need to disable it first
      // and then re-enable it after changing the limit
      npm1300_i2c_submit(drv, npm1300_ops_charging_limit_reenable);
    } else {
      npm1300_i2c_submit(drv, npm1300_ops_charging_limit);
    }
    drv->state = NPM1300_STATE_CHARGING_LIMIT;
  } else if (drv->charging != drv->charging_requested) {
    // Change charging state
    if (drv->charging_requested) {
      npm1300_i2c_submit(drv, npm1300_ops_charging_enable);
      drv->state = NPM1300_STATE_CHARGING_ENABLE;
    } else {
      npm1300_i2c_submit(drv, npm1300_ops_charging_disable);
      drv->state = NPM1300_STATE_CHARGING_DISABLE;
    }
  } else if (drv->buck_mode != drv->buck_mode_requested) {
    drv->buck_mode_set = drv->buck_mode_requested;
    if (drv->buck_mode_set == PMIC_BUCK_MODE_PWM) {
      npm1300_i2c_submit(drv, npm1300_ops_buck_pwm);
    } else if (drv->buck_mode_set == PMIC_BUCK_MODE_PFM) {
      npm1300_i2c_submit(drv, npm1300_ops_buck_pfm);
    } else {
      npm1300_i2c_submit(drv, npm1300_ops_buck_auto);
    }
    drv->state = NPM1300_STATE_BUCK_MODE_SET;
  } else if (drv->adc_readout_requested) {
    // Read ADC values
    npm1300_i2c_submit(drv, npm1300_ops_adc_readout);
    drv->state = NPM1300_STATE_ADC_READOUT;
  } else if (drv->adc_trigger_requested) {
    // Trigger ADC conversion
    npm1300_i2c_submit(drv, npm1300_ops_adc_trigger);
    drv->state = NPM1300_STATE_ADC_TRIGGER;
  } else if (drv->shipmode_requested) {
    npm1300_i2c_submit(drv, npm1300_ops_enter_shipmode);
    drv->shipmode_requested = false;
    drv->state = NPM1300_STATE_ENTER_SHIPMODE;
  }

  // After processing all requests, check if we need to
  // suspend the driver
  if (drv->state == NPM1300_STATE_IDLE) {
    // No more requests to process
    if (drv->suspending) {
      drv->suspending = false;
      drv->suspended = true;
    }
  }
}

#endif  // KERNEL_MODE
