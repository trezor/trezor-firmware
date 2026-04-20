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

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <io/display.h>
#include <sys/bootutils.h>

void ensure_compatible_display_settings_for_bootloader(void) {
  // We are going to jump directly to the bootloader, so we need to
  // ensure that the device is in a compatible state. Following lines
  // ensure the display is properly deinitialized, CPU frequency is
  // properly set and we are running in privileged thread mode.
  display_deinit(DISPLAY_RESET_CONTENT);
}

void ensure_compatible_display_settings(void) {
  // Ensure the display is properly deinitialized, CPU frequency is
  // properly set. It's needed for backward compatibility with the older
  // firmware.
  display_deinit(DISPLAY_JUMP_BEHAVIOR);
}

#endif  // KERNEL_MODE
