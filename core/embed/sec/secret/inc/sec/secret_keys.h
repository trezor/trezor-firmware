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

#ifdef USE_OPTIGA

#define OPTIGA_PAIRING_SECRET_SIZE 32
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]);

#endif

#ifdef USE_TROPIC

#include <ed25519-donna/ed25519.h>

secbool secret_key_tropic_public(curve25519_key dest);

secbool secret_key_tropic_pairing(curve25519_key dest);
#endif

#endif
