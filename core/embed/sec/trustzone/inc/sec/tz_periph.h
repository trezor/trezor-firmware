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

#include <trezor_types.h>

#ifdef SECURE_MODE

// The secure monitor locks the TZSC configuration until
// reset at the end of `tz_init()`; a call after the lock is a fatal error,
// so in the secmon layout these may only be used during `tz_init()`. They
// are not available to non-secure builds.

#ifndef SECMON
// Sets unprivileged access to the SAES peripheral.
void tz_set_saes_unpriv(bool unpriv);

// Sets unprivileged access to the TAMP peripheral.
void tz_set_tamper_unpriv(bool unpriv);
#endif

// Sets unprivileged access to the GFXMMU peripheral.
//
// The GFXMMU's privilege attribute is also carried by its own bus-master
// transactions (the LTDC refresh), so the physical frame buffers must be
// unprivileged before the GFXMMU is made unprivileged.
void tz_set_gfxmmu_unpriv(bool unpriv);

#endif  // SECURE_MODE
