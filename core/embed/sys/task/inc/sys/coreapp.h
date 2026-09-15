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

#pragma once

#ifdef KERNEL_MODE

#include <trezor_types.h>

#include <sys/applet.h>
#include <sys/mpu.h>

// Coreapp entry point
typedef void (*coreapp_startup_t)(const char* args, uint32_t random);

// Applet header found at the beginning of the coreapp binary
typedef struct {
  // Applet entry point
  coreapp_startup_t startup;
  // Stack area
  mpu_area_t stack;
  // TLS area
  mpu_area_t tls;
  // Entry point Core runs on behalf of a newly loaded app (see
  // `coreapp_get_app_entry()`)
  void* app_entry;
  // Unprivileged SAES input buffer
  void* saes_input;
  // Unprivileged SAES output buffer
  void* saes_output;
  // Unprivileged SAES callback
  void* saes_callback;
} coreapp_header_t;

#ifdef TREZOR_EMULATOR

// Initializes the coreapp and prepares it for execution from its entry point.
//
// Coreapp does not start immediately, it needs to be run by
// `applet_run()` after calling this function.
//
// Returns `true` if the applet was successfully initialized.
bool coreapp_init(applet_t* applet, int argc, char** argv);

#else

// Initializes the coreapp and prepares it for execution from its entry point.
//
// Coreapp does not start immediately, it needs to be run by
// `applet_run()` after calling this function.
//
// Returns `true` if the applet was successfully initialized.
bool coreapp_init(applet_t* applet, uint32_t cmd, const void* arg,
                  size_t arg_size);

mpu_area_t coreapp_get_code_area(void);

mpu_area_t coreapp_get_tls_area(void);

#endif  // TREZOR_EMULATOR

#ifdef USE_APP_LOADING
// Returns the coreapp function that a loaded app's task is started on.
//
// The loader does not jump into the app's own `applet_main` directly.
// Instead it schedules this coreapp function, passing `applet_main` to it as
// its only argument. That inversion lets Core run per-launch setup -- most
// importantly claiming the app's heap for the Rust global allocator the app
// allocates from -- before any app code executes, and it is Core, not the
// loader, that hands the API getter to `applet_main`.
void* coreapp_get_app_entry(void);
#endif

#endif  // KERNEL_MODE
