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

#ifdef KERNEL_MODE

// Charger leaf of the managed power-manager policy for a PMIC without a
// charger (e.g. the npm2100 boost regulator for primary cells). Every entry
// point is a no-op or a rejection, so the rest of the policy can call the
// charger leaf unconditionally. Selected by build.rs when USE_CHARGER is not
// set; power_charging.c is the real implementation.

#include <trezor_rtl.h>

#include "pm_core.h"

void pm_charging_init(pm_core_t* core) {
  memset(&core->chg, 0, sizeof(core->chg));
}

void pm_charging_step(pm_core_t* core, pm_actions_t* actions) {
  (void)core;
  (void)actions;
}

bool pm_charging_active(const pm_core_t* core) {
  (void)core;
  return false;
}

void pm_charging_update_limited(pm_core_t* core) {
  core->chg.limited_start_ms = 0U;
  core->chg.limited_latched = false;
}

// Enabling/disabling and the SoC target are accepted and ignored: there is
// nothing to act on. A current limit is rejected rather than reported as
// applied, because it never would be.

bool pm_charging_set_enabled(pm_core_t* core, bool enabled) {
  (void)core;
  (void)enabled;
  return true;
}

bool pm_charging_set_max_limit(pm_core_t* core, uint16_t current_ma) {
  (void)core;
  (void)current_ma;
  return false;
}

bool pm_charging_set_soc_target(pm_core_t* core, uint8_t target) {
  (void)core;
  (void)target;
  return true;
}

void pm_charging_apply(const pm_actions_t* actions) { (void)actions; }

#endif  // KERNEL_MODE
