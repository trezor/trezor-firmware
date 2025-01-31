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

#include <sys/systick.h>
#include <sys/types.h>
#include <util/flash_utils.h>
#include <util/image.h>

#ifdef USE_STORAGE_HWKEY
#include <sec/secret.h>
#endif

#include "bootui.h"
#include "workflow.h"

workflow_result_t workflow_empty_device(void) {
  ui_set_initial_setup(true);

#ifdef USE_STORAGE_HWKEY
  secret_bhk_regenerate();
#endif
  ensure(erase_storage(NULL), NULL);

  // keep the model screen up for a while
#ifndef USE_BACKLIGHT
  systick_delay_ms(1500);
#else
  // backlight fading takes some time so the explicit delay here is
  // shorter
  systick_delay_ms(1000);
#endif

  workflow_result_t res = WF_CANCELLED;
  while (res == WF_CANCELLED) {
    res = workflow_host_control(NULL, NULL, ui_screen_welcome);
  }
  return res;
}
