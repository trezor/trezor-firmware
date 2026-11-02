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

// Default AddressSanitizer runtime options, picked up by the ASAN runtime
// at startup. ASAN_OPTIONS in the environment still overrides them.
//
// The firmware does not allocate on the heap, so leak detection only
// reports allocations made by third-party libraries (SDL, GTK loaded through
// libdecor on Wayland, fontconfig, ...) that we have no control over.
const char* __asan_default_options(void) { return "detect_leaks=0"; }
