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

#if MICROPY_PY_TREZORPROTO

#include "librust.h"

/// from trezor.protobuf import MessageType
/// T = TypeVar("T", bound=MessageType)

/// def type_for_name(name: str) -> Type[MessageType]:
///     """Find the message definition for the given protobuf name."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_protobuf_type_for_name_obj,
                                 protobuf_type_for_name);

/// def type_for_wire(wire_type: int) -> Type[MessageType]:
///     """Find the message definition for the given wire type (numeric
///     identifier)."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_protobuf_type_for_wire_obj,
                                 protobuf_type_for_wire);

/// def decode(
///     buffer: bytes,
///     msg_type: Type[T],
///     enable_experimental: bool,
/// ) -> T:
///     """Decode data in the buffer into the specified message type."""
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorutils_protobuf_decode_obj,
                                 protobuf_decode);

/// def encoded_length(msg: MessageType) -> int:
///     """Calculate length of encoding of the specified message."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_protobuf_encoded_length_obj,
                                 protobuf_len);

/// def encode(buffer: bytearray, msg: MessageType) -> int:
///     """Encode the message into the specified buffer. Return length of
///     encoding."""
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorutils_protobuf_encode_obj,
                                 protobuf_encode);

STATIC const mp_rom_map_elem_t mp_module_trezorproto_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorproto)},

    {MP_ROM_QSTR(MP_QSTR_type_for_name),
     MP_ROM_PTR(&mod_trezorutils_protobuf_type_for_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_type_for_wire),
     MP_ROM_PTR(&mod_trezorutils_protobuf_type_for_wire_obj)},
    {MP_ROM_QSTR(MP_QSTR_decode),
     MP_ROM_PTR(&mod_trezorutils_protobuf_decode_obj)},
    {MP_ROM_QSTR(MP_QSTR_encoded_length),
     MP_ROM_PTR(&mod_trezorutils_protobuf_encoded_length_obj)},
    {MP_ROM_QSTR(MP_QSTR_encode),
     MP_ROM_PTR(&mod_trezorutils_protobuf_encode_obj)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorproto_globals,
                            mp_module_trezorproto_globals_table);

const mp_obj_module_t mp_module_trezorproto = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorproto_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorproto, mp_module_trezorproto,
                   MICROPY_PY_TREZORPROTO);

#endif  // MICROPY_PY_TREZORPROTO
