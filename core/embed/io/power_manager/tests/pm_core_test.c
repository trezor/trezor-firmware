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

// Host test of the pure power-manager core: drives pm_core with a fake clock,
// a fake fuel gauge (SoC and brownout set directly by the test) and a fake
// charger that records what it was told, and checks the states the policy
// reaches and the actions it asks the glue for.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/pm_core.h"
#include "../fuel_gauge/battery.h"
#include "../pmic/pmic_charger.h"

// --- Fake fuel gauge ---------------------------------------------------------
// The test owns the SoC and the brownout verdict, so the policy can be walked
// through its thresholds without a battery model.

static struct {
  bool locked;
  float soc;
  float P;
  bool critical;
  int feed_samples;
  int compensations;
} fg;

void bat_init(void) { memset(&fg, 0, sizeof(fg)); }
ts_t bat_fg_set_soc(float soc, float P) {
  fg.soc = soc;
  fg.P = P;
  fg.locked = true;
  return TS_OK;
}
ts_t bat_fg_feed_sample(float v, float i, float t) {
  fg.feed_samples++;
  return TS_OK;
}
ts_t bat_fg_initial_guess(void) {
  fg.locked = true;
  return TS_OK;
}
bool bat_fg_is_locked(void) { return fg.locked; }
ts_t bat_fg_get_state(bat_fg_state_t* s) {
  s->soc = fg.soc;
  s->soc_latched = fg.soc;
  s->P = fg.P;
  return TS_OK;
}
ts_t bat_fg_update(uint32_t dt_ms, float v, float i, float t) { return TS_OK; }
ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s, float i, float t) {
  fg.compensations++;
  *soc -= 0.01f;  // any visible change will do
  return TS_OK;
}
bool bat_eval_critical(bool currently, float v, float i, float t) {
  return fg.critical;
}
float bat_fetch_cycle_increment(void) { return 0.0f; }
float bat_soc_to_ocv(float soc, float t, bool d) { return 3.2f + 0.4f * soc; }
float bat_meas_to_ocv(float v, float i, float t) { return v; }

// --- Fake charger ------------------------------------------------------------

static struct {
  int limit_ma;
  bool on;
  int set_limit_calls;
  int set_charging_calls;
  int clear_errors_calls;
} chg;

int pmic_charging_limit_min(void) { return 32; }
int pmic_get_charging_limit(void) { return chg.limit_ma; }
bool pmic_set_charging_limit(int i) {
  chg.limit_ma = i;
  chg.set_limit_calls++;
  return true;
}
bool pmic_set_charging(bool on) {
  chg.on = on;
  chg.set_charging_calls++;
  return true;
}
bool pmic_clear_charger_errors(void) {
  chg.clear_errors_calls++;
  return true;
}

// --- Harness -----------------------------------------------------------------

static int failures;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      failures++;                                                              \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #cond); \
    }                                                                          \
  } while (0)

static const pm_config_t cfg = {
    .low_soc_percent = 15,
    .power_save_backlight = 130,
    .suspend_current_ma = 0.032f,
    .hibernation_current_ma = 0.004f,
};

static pm_core_t core;
static uint32_t now_ms;
static pm_sample_t sample;

// Default healthy sample: on battery, 3.3 V, no external power.
static void sample_reset(void) {
  memset(&sample, 0, sizeof(sample));
  sample.pmic.vbat = 3.3f;
  sample.pmic.vsys = 3.3f;
  sample.pmic.ibat = 50.0f;
  sample.pmic.ibat_valid = true;
  sample.pmic.ntc_present = true;
  sample.pmic.ntc_temp = 25.0f;
  sample.pmic.die_temp = 30.0f;
}

// One sampling tick: advance the clock by the nominal period and feed the
// current sample. Returns the actions the glue would have to carry out.
static pm_actions_t tick(void) {
  pm_actions_t a;
  now_ms += PM_TIMER_PERIOD_MS;
  pm_core_sample(&core, &sample, now_ms, &a);
  return a;
}

static pm_actions_t request(pm_request_t r) {
  pm_actions_t a;
  pm_core_request(&core, r, now_ms, &a);
  return a;
}

// Runs the charger glue the way power_manager.c would.
static void apply_charging(const pm_actions_t* a) { pm_charging_apply(a); }

static void fresh_core(bool inherit, const pm_recovery_data_t* rec,
                       uint32_t elapsed_s) {
  bat_init();
  memset(&chg, 0, sizeof(chg));
  now_ms = 1000;
  sample_reset();
  pm_core_reset(&core);
  pm_core_init(&core, &cfg, inherit, rec, elapsed_s);
}

// --- Tests -------------------------------------------------------------------

static void test_cold_boot_turn_on_and_low_battery(void) {
  fresh_core(false, NULL, 0);
  CHECK(core.state == PM_STATE_HIBERNATE);
  CHECK(fg.locked);  // no recovery -> initial guess

  // First sample: nothing to act on yet (no source), but the snapshot is live.
  fg.soc = 0.80f;
  pm_actions_t a = tick();
  CHECK(a.sample_complete);
  CHECK(core.stabilized);
  CHECK(core.has_sample);
  CHECK(!a.power_off);
  CHECK(core.state == PM_STATE_HIBERNATE);

  // Boot finished: turn on. HIBERNATE -> POWER_SAVE -> ACTIVE in one run,
  // ending with the unlimited backlight.
  a = request(PM_REQ_TURN_ON);
  CHECK(core.state == PM_STATE_ACTIVE);
  CHECK(a.set_backlight && a.backlight_level == 255);

  pm_state_t st;
  pm_core_get_state(&core, &st);
  CHECK(st.power_status == PM_STATE_ACTIVE);
  CHECK(st.soc == 80);
  CHECK(st.charging_status == PM_BATTERY_DISCHARGING);
  CHECK(st.ntc_connected);
  CHECK(st.battery_connected);

  // Battery drops to the low threshold -> POWER_SAVE with the capped backlight
  fg.soc = 0.15f;
  a = tick();
  CHECK(core.battery_low);
  CHECK(core.state == PM_STATE_POWER_SAVE);
  CHECK(a.set_backlight && a.backlight_level == cfg.power_save_backlight);

  // Recovers above the threshold -> back to ACTIVE
  fg.soc = 0.16f;
  a = tick();
  CHECK(core.state == PM_STATE_ACTIVE);
  CHECK(a.set_backlight && a.backlight_level == 255);
}

static void test_brownout_shutdown_timeout(void) {
  fresh_core(false, NULL, 0);
  fg.soc = 0.10f;
  tick();
  request(PM_REQ_TURN_ON);
  CHECK(core.state == PM_STATE_POWER_SAVE);

  // Gauge declares brownout -> SHUTTING_DOWN, deadline armed
  fg.critical = true;
  pm_actions_t a = tick();
  CHECK(core.battery_critical);
  CHECK(core.state == PM_STATE_SHUTTING_DOWN);
  CHECK(!a.power_off);

  // Stays there until the timeout...
  for (uint32_t t = 0; t + PM_TIMER_PERIOD_MS < PM_SHUTDOWN_TIMEOUT_MS;
       t += PM_TIMER_PERIOD_MS) {
    a = tick();
    CHECK(core.state == PM_STATE_SHUTTING_DOWN);
    CHECK(!a.power_off);
  }
  // ...then hibernates, asking the glue to persist and power off.
  a = tick();
  CHECK(core.state == PM_STATE_HIBERNATE);
  CHECK(a.power_off);

  // Recovery snapshot carries the brownout latch
  pm_recovery_data_t rec = {0};
  pm_core_recovery(&core, &rec);
  CHECK(rec.bat_critical);
  CHECK(rec.bootloader_exit_state == PM_STATE_HIBERNATE);
}

static void test_brownout_cleared_by_usb(void) {
  fresh_core(false, NULL, 0);
  fg.soc = 0.05f;
  fg.critical = true;
  tick();
  request(PM_REQ_TURN_ON);
  CHECK(core.state == PM_STATE_SHUTTING_DOWN);

  // USB appears: never brownout-critical on external power, and with a source
  // present the device goes straight back to ACTIVE.
  sample.pmic.vbus_present = true;
  pm_actions_t a = tick();
  CHECK(a.power_source_changed);
  CHECK(!core.battery_critical);
  CHECK(core.state == PM_STATE_ACTIVE);
  CHECK(!a.power_off);
}

static void test_charging_from_hibernate(void) {
  fresh_core(false, NULL, 0);
  fg.soc = 0.50f;

  // Plugged in while hibernated: CHARGING, charger on at the pack maximum.
  sample.pmic.vbus_present = true;
  pm_actions_t a = tick();
  CHECK(core.state == PM_STATE_CHARGING);
  CHECK(a.apply_charging);
  CHECK(a.charging_on);
  CHECK(a.charging_limit_ma == 180);
  apply_charging(&a);
  CHECK(chg.on && chg.limit_ma == 180);

  pm_state_t st;
  pm_core_get_state(&core, &st);
  CHECK(st.charging_status == PM_BATTERY_CHARGING);
  CHECK(st.usb_connected);

  // A hibernate request while charging is ignored (stays CHARGING, no reboot)
  a = request(PM_REQ_HIBERNATE);
  CHECK(core.state == PM_STATE_CHARGING);
  CHECK(!a.power_off);

  // Hot battery: the thermal limiter derates to 50 % and reports itself.
  sample.pmic.ntc_temp = 44.0f;
  a = tick();
  CHECK(a.charging_limit_ma == 90);
  CHECK(core.chg.temp_control_active);
  pm_core_get_state(&core, &st);
  CHECK(st.temp_control_active);

  // Charger fault while charging: the glue is asked to clear it.
  sample.pmic.charger_fault = true;
  a = tick();
  CHECK(a.clear_charger_errors);
  apply_charging(&a);
  CHECK(chg.clear_errors_calls == 1);

  // Charger says full: SoC snaps to 100 %, charging stops.
  sample.pmic.charger_fault = false;
  sample.pmic.charge_complete = true;
  a = tick();
  CHECK(core.fully_charged);
  CHECK(fg.soc == 1.0f);
  CHECK(!pm_charging_active(&core));

  // Unplug: back to HIBERNATE and power off
  sample.pmic.vbus_present = false;
  sample.pmic.charge_complete = false;
  a = tick();
  CHECK(a.power_source_changed);
  CHECK(core.state == PM_STATE_HIBERNATE);
  CHECK(a.power_off);
}

static void test_charging_api(void) {
  fresh_core(false, NULL, 0);
  fg.soc = 0.50f;
  sample.pmic.vbus_present = true;
  tick();
  request(PM_REQ_TURN_ON);
  CHECK(core.state == PM_STATE_ACTIVE);

  // Out-of-range limits are rejected, in-range ones clamp the target
  CHECK(!pm_charging_set_max_limit(&core, 181));
  CHECK(!pm_charging_set_max_limit(&core, 31));
  CHECK(pm_charging_set_max_limit(&core, 100));
  pm_actions_t a = tick();
  CHECK(a.charging_limit_ma == 100);

  // Disabling stops the charger at once
  pm_charging_set_enabled(&core, false);
  memset(&a, 0, sizeof(a));
  pm_charging_step(&core, &a);
  CHECK(a.apply_charging && !a.charging_on && a.charging_limit_ma == 0);
  // ...and a second step with nothing to change asks for nothing
  memset(&a, 0, sizeof(a));
  pm_charging_step(&core, &a);
  CHECK(!a.apply_charging);
}

static void test_suspend_cycle(void) {
  fresh_core(false, NULL, 0);
  fg.soc = 0.60f;
  tick();
  request(PM_REQ_TURN_ON);
  CHECK(core.state == PM_STATE_ACTIVE);

  request(PM_REQ_SUSPEND);
  CHECK(core.state == PM_STATE_SUSPEND);
  CHECK(!core.request_suspend);

  // Back from 10 minutes of suspend: the next sample compensates the gauge
  // instead of running the estimator, and the snapshot is stale until then.
  pm_core_resume(&core, 600);
  CHECK(!core.stabilized);
  int before = fg.compensations;
  pm_actions_t a = tick();
  CHECK(fg.compensations == before + 1);
  CHECK(core.stabilized);
  CHECK(!core.woke_up_from_suspend);

  a = request(PM_REQ_EXIT_SUSPEND);
  CHECK(core.state == PM_STATE_ACTIVE);
  CHECK(a.set_backlight);
}

static void test_recovery_and_inherit(void) {
  // Bootloader cold boot with a snapshot: SoC restored and compensated
  pm_recovery_data_t rec = {
      .version = PM_RECOVERY_DATA_VERSION,
      .soc = 0.42f,
      .P = 0.5f,
      .bat_critical = false,
      .bootloader_exit_state = PM_STATE_ACTIVE,
  };
  fresh_core(false, &rec, 3600);
  CHECK(fg.locked);
  CHECK(fg.compensations == 1);
  CHECK(fg.P == 0.5f);
  CHECK(core.state == PM_STATE_HIBERNATE);

  // Kernel inheriting the bootloader's state: no compensation, state carried
  fresh_core(true, &rec, 0);
  CHECK(fg.compensations == 0);
  CHECK(core.state == PM_STATE_ACTIVE);

  // Kernel without a snapshot: lowest active state
  fresh_core(true, NULL, 0);
  CHECK(core.state == PM_STATE_POWER_SAVE);
}

static void test_chargerless_report(void) {
  // A PMIC without current sense or NTC (npm2100-like): no NTC fault, and
  // "discharging" rather than "idle" when on battery.
  fresh_core(false, NULL, 0);
  fg.soc = 0.70f;
  sample.pmic.ibat_valid = false;
  sample.pmic.ibat = 0.0f;
  sample.pmic.ntc_present = false;
  sample.pmic.ntc_disconnected = false;
  tick();
  request(PM_REQ_TURN_ON);

  pm_state_t st;
  pm_core_get_state(&core, &st);
  CHECK(st.ntc_connected);
  CHECK(st.charging_status == PM_BATTERY_DISCHARGING);
  CHECK(core.state == PM_STATE_ACTIVE);
}

int main(void) {
  test_cold_boot_turn_on_and_low_battery();
  test_brownout_shutdown_timeout();
  test_brownout_cleared_by_usb();
  test_charging_from_hibernate();
  test_charging_api();
  test_suspend_cycle();
  test_recovery_and_inherit();
  test_chargerless_report();

  if (failures != 0) {
    fprintf(stderr, "pm_core_test: %d check(s) FAILED\n", failures);
    return EXIT_FAILURE;
  }
  printf("pm_core_test: all checks passed\n");
  return EXIT_SUCCESS;
}
