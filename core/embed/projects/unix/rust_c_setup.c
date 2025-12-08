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

#include <trezor_rtl.h>

#include <io/display.h>
#include <io/usb_config.h>
#include <sys/system.h>
#include <util/flash.h>
#include <util/flash_otp.h>
#include <util/unit_properties.h>

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

// Initialize the system and drivers for running tests in the Rust code.
// The function is called from the Rust before the test main function is run.
void rust_tests_c_setup(void) {
  system_init(NULL);

  flash_init();
  flash_otp_init();

  unit_properties_init();

  display_init(DISPLAY_RESET_CONTENT);

#if USE_TOUCH
  touch_init();
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_TROPIC
  tropic_init(28992);
#endif

  usb_configure(NULL);
}
