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

// anti-glitch
static volatile secbool continue_to_firmware = secfalse;
static volatile secbool continue_to_firmware_backup = secfalse;

secbool jump_is_allowed_1(void) { return continue_to_firmware; }
secbool jump_is_allowed_2(void) { return continue_to_firmware_backup; }

void jump_allow_1(void) { continue_to_firmware = sectrue; }
void jump_allow_2(void) { continue_to_firmware_backup = sectrue; }

void jump_reset(void) {
  continue_to_firmware_backup = secfalse;
  continue_to_firmware = secfalse;
}
