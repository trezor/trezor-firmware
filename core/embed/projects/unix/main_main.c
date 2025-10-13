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
#include <sec/secret.h>
#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <util/flash.h>
#include <util/flash_otp.h>
#include <util/rsod.h>
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

#ifdef USE_SECP256K1_ZKP
#include "zkp_context.h"
#endif

#include <SDL.h>

static applet_t coreapp;

static void drivers_init() {
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
  tropic_init();
#endif

  usb_configure(NULL);
}

static int sdl_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_QUIT:
      systask_exit(&coreapp.task, 0);
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          systask_exit(&coreapp.task, 0);
          return 0;
        case SDLK_s:
          display_save("emu");
          return 0;
      }
      break;
  }
  return 1;
}

// Kernel task main loop
//
// Returns when the coreapp task is terminated
static void kernel_loop(applet_t *coreapp) {
  do {
    sysevents_t awaited = {0};
    sysevents_t signalled = {0};

    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

  } while (applet_is_alive(coreapp));
}

int main(int argc, char **argv) {
  system_init(&rsod_panic_handler);

#ifdef LOCKABLE_BOOTLOADER
  secret_lock_bootloader();
#endif

#ifdef USE_SECP256K1_ZKP
  ensure(sectrue * (zkp_context_init() == 0), NULL);
#endif

  drivers_init();

  SDL_SetEventFilter(sdl_event_filter, NULL);

  if (!coreapp_init(&coreapp, argc, argv)) {
    error_shutdown("Cannot start coreapp");
  }

  applet_run(&coreapp);

  kernel_loop(&coreapp);

  // !@#
  return coreapp.task.pminfo.exit.code;
}

// Initialize the system and drivers for running tests in the Rust code.
// The function is called from the Rust before the test main function is run.
void rust_tests_c_setup(void) {
  system_init(NULL);
  drivers_init();
}
