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

#if MICROPY_PY_TREZORUI2

#include "librust.h"

#if TREZOR_MODEL == T
/// def layout_new_example(text: str) -> None:
///     """Example layout."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui2_layout_new_example_obj,
                                 ui_layout_new_example);
#elif TREZOR_MODEL == 1
/// def layout_new_confirm_action(
///     title: str | None,
///     action: str | None,
///     description: str | None,
///     verb: str | None,
///     verb_cancel: str | None,
///     hold: bool | None,
///     reverse: bool,
/// ) -> int:
///     """Confirm generic action. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_action_obj,
                                  0, ui_layout_new_confirm_action);

/// def layout_new_confirm_reset(
///     prompt: str,
/// ) -> int:
///     """Confirm device setup. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_reset_obj, 0,
                                  ui_layout_new_confirm_reset);

/// def layout_new_path_warning(
///     path: str,
///     title: str,
/// ) -> int:
///     """Show invalid derivation path warning. All arguments must be passed as
///     kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_path_warning_obj, 0,
                                  ui_layout_new_path_warning);

/// def layout_new_show_address(
///     title: str,
///     address: str,
///     network: str | None,
///     extra: str | None,
/// ) -> int:
///     """Show address. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_show_address_obj, 0,
                                  ui_layout_new_show_address);

/// def layout_new_show_modal(
///     title: str | None,
///     subtitle: str | None,
///     content: str,
///     button_confirm: str | None,
///     button_cancel: str | None,
/// ) -> int:
///     """Show success/error/warning. All arguments must be passed as
///     kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_show_modal_obj, 0,
                                  ui_layout_new_show_modal);

/// def layout_new_confirm_output(
///     title: str,
///     subtitle: str | None,
///     address: str,
///     amount: str,
/// ) -> int:
///     """Confirm output/recipient. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_output_obj,
                                  0, ui_layout_new_confirm_output);

/// def layout_new_confirm_total(
///     title: str,
///     label1: str,
///     amount1: str,
///     label2: str,
///     amount2: str,
/// ) -> int:
///     """Final tx confirm. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_total_obj, 0,
                                  ui_layout_new_confirm_total);

/// def layout_new_confirm_metadata(
///     title: str,
///     content: str,
///     show_continue: bool,
/// ) -> int:
///     """Confirm tx metadata. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_metadata_obj,
                                  0, ui_layout_new_confirm_metadata);

/// def layout_new_confirm_blob(
///     title: str,
///     description: str | None,
///     data: str,
/// ) -> int:
///     """Confirm arbitrary data. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_blob_obj, 0,
                                  ui_layout_new_confirm_blob);

/// def layout_new_confirm_modify_fee(
///     title: str,
///     sign: int,
///     user_fee_change: str,
///     total_fee_new: str,
/// ) -> int:
///     """Confirm fee change. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(
    mod_trezorui2_layout_new_confirm_modify_fee_obj, 0,
    ui_layout_new_confirm_modify_fee);

/// def layout_new_confirm_coinjoin(
///     title: str,
///     fee_per_anonymity: str | None,
///     total_fee: str,
/// ) -> int:
///     """Confirm coinjoin. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_coinjoin_obj,
                                  0, ui_layout_new_confirm_coinjoin);
#endif

STATIC const mp_rom_map_elem_t mp_module_trezorui2_globals_table[] = {
#if TREZOR_MODEL == T
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorui2)},

    {MP_ROM_QSTR(MP_QSTR_layout_new_example),
     MP_ROM_PTR(&mod_trezorui2_layout_new_example_obj)},
#elif TREZOR_MODEL == 1
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_action),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_action_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_reset),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_reset_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_path_warning),
     MP_ROM_PTR(&mod_trezorui2_layout_new_path_warning_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_show_address),
     MP_ROM_PTR(&mod_trezorui2_layout_new_show_address_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_show_modal),
     MP_ROM_PTR(&mod_trezorui2_layout_new_show_modal_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_output),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_output_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_total),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_total_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_metadata),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_metadata_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_blob),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_blob_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_modify_fee),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_modify_fee_obj)},
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_coinjoin),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_coinjoin_obj)},
#endif

};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorui2_globals,
                            mp_module_trezorui2_globals_table);

const mp_obj_module_t mp_module_trezorui2 = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorui2_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorui2, mp_module_trezorui2,
                   MICROPY_PY_TREZORUI2);

#endif  // MICROPY_PY_TREZORUI2
