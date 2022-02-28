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

#if MICROPY_PY_TREZORCRYPTO

#include "librust.h"

STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_diag, orchardlib_diag);


/// def derive_full_viewing_key(spending_key: bytes, internal: bool) -> bytes:
/// """Returns a raw Orchard Full Viewing Key."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_derive_full_viewing_key, orchardlib_derive_full_viewing_key);

/// def derive_internal_full_viewing_key(full_viewing_key: bytes) -> bytes:
/// """Returns a raw internal Orchard Full Viewing Key."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_orchardlib_derive_internal_full_viewing_key, orchardlib_derive_internal_full_viewing_key);

/// def derive_incoming_viewing_key(full_viewing_key: bytes, internal: bool) -> bytes:
/// """Returns a raw Orchard Incoming Viewing Key."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_derive_incoming_viewing_key, orchardlib_derive_incoming_viewing_key);

/// def derive_outgoing_viewing_key(full_viewing_key: bytes, internal: bool) -> bytes:
/// """Returns a raw Orchard Outgoing Viewing Key."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_derive_outgoing_viewing_key, orchardlib_derive_outgoing_viewing_key);

/// def derive_address(
///     full_viewing_key: bytes,
///     diversifier_index: int,
///     internal: bool,
/// ) -> bytes:
/// """Returns a raw Orchard address."""
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_orchardlib_derive_address, orchardlib_derive_address);

/// def f4jumble(message: bytearray) -> None:
///     """Mutates a message by F4Jumble permutation."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_orchardlib_f4jumble, orchardlib_f4jumble);

/// def f4jumble_inv(message: bytearray) -> None:
///     """Mutates a message by F4Jumble inverse permutation."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_orchardlib_f4jumble_inv, orchardlib_f4jumble_inv);

/// def shuffle(
///     list,
///     rng_config,
/// ):
/// """Shuffles a list."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_shuffle, orchardlib_shuffle);

/// def shield(
///     action_info,
///     rng_config,
/// ):
/// """Returns an action descripription as serialized in the ledger
///    and attached alpha randomizer."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_orchardlib_shield, orchardlib_shield);

/// def sign(
///     spending_key: bytes,
///     alpha: bytes,
///     sighash: bytes,
/// ):
/// """reddsa spend signature of over pallas
///  
/// # Args:
///     `spending_key` - spending key
///     `alpha` - randomizer (pallas scalar)
///     `sighash` - message digest
/// """
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_orchardlib_sign, orchardlib_sign);

STATIC const mp_rom_map_elem_t mp_module_trezororchardlib_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezororchardlib)},
    {MP_ROM_QSTR(MP_QSTR_diag),     MP_ROM_PTR(&mod_orchardlib_diag)},
    {MP_ROM_QSTR(MP_QSTR_derive_full_viewing_key),  MP_ROM_PTR(&mod_orchardlib_derive_full_viewing_key)},
    {MP_ROM_QSTR(MP_QSTR_derive_internal_full_viewing_key),  MP_ROM_PTR(&mod_orchardlib_derive_internal_full_viewing_key)},
    {MP_ROM_QSTR(MP_QSTR_derive_incoming_viewing_key),  MP_ROM_PTR(&mod_orchardlib_derive_incoming_viewing_key)},
    {MP_ROM_QSTR(MP_QSTR_derive_outgoing_viewing_key),  MP_ROM_PTR(&mod_orchardlib_derive_outgoing_viewing_key)},
    {MP_ROM_QSTR(MP_QSTR_derive_address), MP_ROM_PTR(&mod_orchardlib_derive_address)},
    {MP_ROM_QSTR(MP_QSTR_f4jumble), MP_ROM_PTR(&mod_orchardlib_f4jumble)},
    {MP_ROM_QSTR(MP_QSTR_f4jumble_inv), MP_ROM_PTR(&mod_orchardlib_f4jumble_inv)},
    {MP_ROM_QSTR(MP_QSTR_shield), MP_ROM_PTR(&mod_orchardlib_shield)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_orchardlib_sign)},
    {MP_ROM_QSTR(MP_QSTR_shuffle), MP_ROM_PTR(&mod_orchardlib_shuffle)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezororchardlib_globals,
                            mp_module_trezororchardlib_globals_table);

const mp_obj_module_t mp_module_trezororchardlib = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezororchardlib_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezororchardlib, mp_module_trezororchardlib,
                   MICROPY_PY_TREZORCRYPTO);

#endif  // MICROPY_PY_TREZOCRYPTO
