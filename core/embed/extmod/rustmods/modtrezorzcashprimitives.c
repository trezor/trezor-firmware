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

#include "py/runtime.h"

#include "librust.h"

#if MICROPY_PY_TREZORPALLAS
MP_REGISTER_MODULE(MP_QSTR_trezorpallas, mp_module_trezorpallas,
                   MICROPY_PY_TREZORPALLAS);
#endif  // MICROPY_PY_TREZORPALLAS

#if MICROPY_PY_TREZORPOSEIDON
MP_REGISTER_MODULE(MP_QSTR_trezorposeidon, mp_module_trezorposeidon,
                   MICROPY_PY_TREZORPOSEIDON);
#endif  // MICROPY_PY_TREZORPOSEIDON
