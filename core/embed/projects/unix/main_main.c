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
#include <sys/bootutils.h>
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

#ifdef USE_BLE
#include <io/ble.h>
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

#ifdef USE_TROPIC
static uint16_t get_tropic_model_port(void) {
  char *port_str = getenv("TROPIC_MODEL_PORT");
  if (port_str != NULL) {
    char *endptr;
    long port_long = strtol(port_str, &endptr, 10);
    if (*endptr != '\0' || port_long < 0 || port_long > 65535) {
      printf("FATAL: invalid TROPIC_MODEL_PORT\n");
      exit(1);
    }
    return (uint16_t)port_long;
  }
  return 28992;
}
#endif

static void drivers_deinit(void) { flash_deinit(); }

static void drivers_init(void) {
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
  tropic_init(get_tropic_model_port());
#endif

  usb_configure(NULL);

#ifdef USE_BLE
  ble_init();
#endif
}

// Throws MicroPython SystemExit exception in the context of the given task
static void throw_exit_exception(systask_t *task, int code) {
  extern void coreapp_throw_exit_exception(int code);
  // Push call to the task
  systask_push_call(task, (void *)coreapp_throw_exit_exception, code, 0, 0);
  // Yield to the task and throw the exception
  systask_yield_to(task);
  // We are back and the task should be terminated by now
}

static int sdl_event_filter(void *userdata, SDL_Event *event) {
  applet_t *coreapp = (applet_t *)userdata;

  switch (event->type) {
    case SDL_QUIT:
      throw_exit_exception(&coreapp->task, 0);
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          throw_exit_exception(&coreapp->task, 0);
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

  applet_t coreapp;

  // Initialize coreapp task
  if (!coreapp_init(&coreapp, argc, argv)) {
    error_shutdown("Cannot start coreapp");
  }

  // Set SDL event filter to catch quit events
  SDL_SetEventFilter(sdl_event_filter, &coreapp);

  // Run the coreapp task
  applet_run(&coreapp);

  // Loop until the coreapp task is terminated
  kernel_loop(&coreapp);

  // Show RSOD if the coreapp task did not exit cleanly
  if (coreapp.task.pminfo.reason != TASK_TERM_REASON_EXIT) {
    rsod_gui(&coreapp.task.pminfo);
    reboot_or_halt_after_rsod();
  }

  drivers_deinit();

  return coreapp.task.pminfo.exit.code;
}
