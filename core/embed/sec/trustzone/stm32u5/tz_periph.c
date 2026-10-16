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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/tz_periph.h>

// Once the TZSC configuration is locked (the secure monitor does so at the
// end of `tz_init()`), writes to it are silently ignored. Fail loudly instead.
static void tzsc_ensure_unlocked(void) {
  ensure(sectrue * ((GTZC_TZSC1->CR & GTZC_TZSC_CR_LCK_Msk) == 0),
         "TZSC locked");
}

// Not available in the secure monitor: it has no use for them and could only
// call them before the lock anyway.
#ifndef SECMON

void tz_set_saes_unpriv(bool unpriv) {
  tzsc_ensure_unlocked();
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_SAES,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}

void tz_set_tamper_unpriv(bool unpriv) {
  tzsc_ensure_unlocked();
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_TAMP,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}

#endif  // !SECMON

#if defined STM32U5A9xx || defined STM32U5G9xx
void tz_set_gfxmmu_unpriv(bool unpriv) {
  tzsc_ensure_unlocked();
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_GFXMMU,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}
#endif

#endif  // SECURE_MODE
