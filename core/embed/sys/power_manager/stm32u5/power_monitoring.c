
#include <trezor_rtl.h>
#include <sys/systick.h>

#include "power_manager_internal.h"

#include "../../powerctl/npm1300/npm1300.h"
#include "../../powerctl/stwlc38/stwlc38.h"

void pm_monitor_power_sources(void) {
  power_manager_driver_t* drv = &g_power_manager;

  /* Check USB power source status */
  if (drv->pmic_data.usb_status != 0x0) {
    if (!drv->usb_connected) {
      drv->usb_connected = true;
      PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_USB_CONNECTED);
    }
  } else {
    if (drv->usb_connected) {
      drv->usb_connected = false;
      PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_USB_DISCONNECTED);
    }
  }

  /* Check wireless charger status */
  if (drv->wireless_data.vout_ready) {
    if (!drv->wireless_connected) {
      drv->wireless_connected = true;
      PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_WIRELESS_CONNECTED);
    }
  } else {
    if (drv->wireless_connected) {
      drv->wireless_connected = false;
      PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_WIRELESS_DISCONNECTED);
    }
  }

  /* Check battery voltage for critical (undervoltage) threshold */
  if ((drv->pmic_data.vbat < POWER_MANAGER_BATTERY_UNDERVOLT_THRESHOLD_V) &&
      !drv->battery_critical) {
    drv->battery_critical = true;
    PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_BATTERY_CRITICAL);
  } else if (drv->pmic_data.vbat > (POWER_MANAGER_BATTERY_UNDERVOLT_THRESHOLD_V +
                                   POWER_MANAGER_BATTERY_UNDERVOLT_HYSTERESIS_V) &&
             drv->battery_critical) {
    drv->battery_critical = false;
  }

  // Check battery voltage for low threshold
  if (drv->pmic_data.vbat < POWER_MANAGER_BATTERY_LOW_THRESHOLD_V && !drv->battery_low) {
    drv->battery_low = true;
    PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_BATTERY_LOW);
  } else if (drv->pmic_data.vbat > POWER_MANAGER_BATTERY_LOW_RECOVERY_V && drv->battery_low) {
    drv->battery_low = false;
  }

  // Request fresh measurements
  npm1300_measure(pm_pmic_data_ready, NULL);
  drv->pmic_measurement_ready = false;

  /* Process state machine with updated battery and power source information */
  pm_process_state_machine();

}

// PMIC measurement callback
void pm_pmic_data_ready(void* context, npm1300_report_t* report) {
  power_manager_driver_t* drv = &g_power_manager;

  /* Store measurement timestamp */
  drv->pmic_last_update_ms = systick_ms();

  /* Copy PMIC data */
  memcpy(&drv->pmic_data, report, sizeof(npm1300_report_t));

  /* Get wireless charger data */
  if (!stwlc38_get_report(&drv->wireless_data)) {
    PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_ERROR);
  }

  drv->pmic_measurement_ready = true;
}