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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/applet.h>
#include <sys/mpu.h>
#include <sys/rng.h>
#include <sys/systask.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifdef KERNEL

void applet_init(applet_t* applet, const applet_layout_t* layout,
                 const applet_privileges_t* privileges) {
  memset(applet, 0, sizeof(applet_t));

  applet->layout = *layout;
  applet->privileges = *privileges;
}

#ifdef USE_TRUSTZONE
// Sets unprivileged access to the applet memory regions
// and allows applet to use some specific peripherals.
static void applet_set_unpriv(applet_t* applet, bool unpriv) {
  applet_layout_t* layout = &applet->layout;

  tz_set_sram_unpriv(layout->data1.start, layout->data1.size, unpriv);
  tz_set_sram_unpriv(layout->data2.start, layout->data2.size, unpriv);
  tz_set_flash_unpriv(layout->code1.start, layout->code1.size, unpriv);
  tz_set_flash_unpriv(layout->code2.start, layout->code2.size, unpriv);

  if (applet->privileges.assets_area_access) {
    tz_set_flash_unpriv(ASSETS_START, ASSETS_MAXSIZE, unpriv);
  }

  display_set_unpriv_access(unpriv);
}
#endif  // USE_TRUSTZONE

void applet_run(applet_t* applet) {
#ifdef USE_TRUSTZONE
  applet_set_unpriv(applet, true);
#endif

  systask_yield_to(&applet->task);
}

void applet_stop(applet_t* applet) {
#ifdef USE_TRUSTZONE
  applet_set_unpriv(applet, false);
#endif
}

bool applet_is_alive(applet_t* applet) {
  return systask_is_alive(&applet->task);
}

applet_t* applet_active(void) {
  systask_t* task = systask_active();

  if (task == NULL) {
    return NULL;
  }

  return (applet_t*)task->applet;
}

#endif  // KERNEL
