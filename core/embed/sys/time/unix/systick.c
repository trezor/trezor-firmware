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

#include <time.h>
#include <unistd.h>

#include <sys/systick.h>

// Systick driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Instant time [us] of driver initialization
  uint64_t initial_time;
  // Instant time [us] of driver deinitialization
  uint64_t final_time;

} systick_driver_t;

static systick_driver_t g_systick_driver = {
    .initialized = false,
};

// Returns number of microseconds since the os started
static uint64_t get_monotonic_clock(void) {
  struct timespec tp;

  clock_gettime(CLOCK_MONOTONIC, &tp);
  return tp.tv_sec * 1000000UL + tp.tv_nsec / 1000;
}

void systick_init(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(systick_driver_t));
  drv->initial_time = get_monotonic_clock();
  drv->initialized = true;
}

void systick_deinit(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    return;
  }

  // This will ensure that the time return by `systick_ms()` and
  // `systick_us()` will not be reset to 0 after the `systick_deinit()` call.
  drv->final_time = get_monotonic_clock();

  drv->initialized = false;
}

void systick_update_freq(void){};

uint32_t systick_ms() {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    systick_init();  // temporary workaround required by rust unit tests
    // return drv->final_time / 1000;
  }

  return (get_monotonic_clock() - drv->initial_time) / 1000;
}

uint64_t systick_us(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    systick_init();  // temporary workaround required by rust unit tests
    // return drv->final_time;
  }

  return get_monotonic_clock() - drv->initial_time;
}

void systick_delay_us(uint64_t us) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    systick_init();  // temporary workaround required by rust unit tests
    // return;
  }

  struct timespec tp;
  tp.tv_sec = us / 1000000;
  tp.tv_nsec = (us % 1000000) * 1000;
  nanosleep(&tp, NULL);
}

void systick_delay_ms(uint32_t ms) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    systick_init();  // temporary workaround required by rust unit tests
    // return;
  }

  struct timespec tp;
  tp.tv_sec = ms / 1000;
  tp.tv_nsec = (ms % 1000) * 1000000;
  nanosleep(&tp, NULL);
}
