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

#if MICROPY_PY_TREZORSTORAGE

#include "librust.h"

// Register all the modules for storage

MP_REGISTER_MODULE(MP_QSTR_trezorstoragedevice, mp_module_trezorstoragedevice,
                   MICROPY_PY_TREZORSTORAGE);

MP_REGISTER_MODULE(MP_QSTR_trezorstoragerecovery,
                   mp_module_trezorstoragerecovery,
                   MICROPY_PY_TREZORSTORAGE);

MP_REGISTER_MODULE(MP_QSTR_trezorstoragerecoveryshares,
                   mp_module_trezorstoragerecoveryshares,
                   MICROPY_PY_TREZORSTORAGE);

MP_REGISTER_MODULE(MP_QSTR_trezorstorageresidentcredentials,
                   mp_module_trezorstorageresidentcredentials,
                   MICROPY_PY_TREZORSTORAGE);

#endif  // MICROPY_PY_TREZORSTORAGE
