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

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "common.h"

#include "py/runtime.h"

#if MICROPY_PY_TREZORCRYPTO

static mp_obj_t ui_wait_callback = mp_const_none;

static void wrapped_ui_wait_callback(uint32_t current, uint32_t total) {
  if (mp_obj_is_callable(ui_wait_callback)) {
    mp_call_function_2_protected(ui_wait_callback, mp_obj_new_int(current),
                                 mp_obj_new_int(total));
  }
}

#include "modtrezorcrypto-aes.h"
#include "modtrezorcrypto-bech32.h"
#include "modtrezorcrypto-bip32.h"
#ifdef USE_SECP256K1_ZKP
#include "modtrezorcrypto-bip340.h"
#endif
#include "modtrezorcrypto-bip39.h"
#include "modtrezorcrypto-blake256.h"
#include "modtrezorcrypto-blake2b.h"
#include "modtrezorcrypto-blake2s.h"
#include "modtrezorcrypto-chacha20poly1305.h"
#include "modtrezorcrypto-crc.h"
#include "modtrezorcrypto-curve25519.h"
#include "modtrezorcrypto-ed25519.h"
#include "modtrezorcrypto-groestl.h"
#include "modtrezorcrypto-hmac.h"
#include "modtrezorcrypto-nist256p1.h"
#include "modtrezorcrypto-pbkdf2.h"
#include "modtrezorcrypto-random.h"
#include "modtrezorcrypto-ripemd160.h"
#include "modtrezorcrypto-secp256k1.h"
#include "modtrezorcrypto-sha1.h"
#include "modtrezorcrypto-sha256.h"
#include "modtrezorcrypto-sha3-256.h"
#include "modtrezorcrypto-sha3-512.h"
#include "modtrezorcrypto-sha512.h"
#include "modtrezorcrypto-shamir.h"
#include "modtrezorcrypto-slip39.h"
#if !BITCOIN_ONLY
#include "modtrezorcrypto-cardano.h"
#include "modtrezorcrypto-monero.h"
#include "modtrezorcrypto-nem.h"
#endif

STATIC const mp_rom_map_elem_t mp_module_trezorcrypto_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorcrypto)},
    {MP_ROM_QSTR(MP_QSTR_aes), MP_ROM_PTR(&mod_trezorcrypto_AES_type)},
    {MP_ROM_QSTR(MP_QSTR_bech32), MP_ROM_PTR(&mod_trezorcrypto_bech32_module)},
    {MP_ROM_QSTR(MP_QSTR_bip32), MP_ROM_PTR(&mod_trezorcrypto_bip32_module)},
    {MP_ROM_QSTR(MP_QSTR_bip39), MP_ROM_PTR(&mod_trezorcrypto_bip39_module)},
    {MP_ROM_QSTR(MP_QSTR_blake256),
     MP_ROM_PTR(&mod_trezorcrypto_Blake256_type)},
    {MP_ROM_QSTR(MP_QSTR_blake2b), MP_ROM_PTR(&mod_trezorcrypto_Blake2b_type)},
    {MP_ROM_QSTR(MP_QSTR_blake2s), MP_ROM_PTR(&mod_trezorcrypto_Blake2s_type)},
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_cardano),
     MP_ROM_PTR(&mod_trezorcrypto_cardano_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_chacha20poly1305),
     MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305_type)},
    {MP_ROM_QSTR(MP_QSTR_crc), MP_ROM_PTR(&mod_trezorcrypto_crc_module)},
    {MP_ROM_QSTR(MP_QSTR_curve25519),
     MP_ROM_PTR(&mod_trezorcrypto_curve25519_module)},
    {MP_ROM_QSTR(MP_QSTR_ed25519),
     MP_ROM_PTR(&mod_trezorcrypto_ed25519_module)},
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_monero), MP_ROM_PTR(&mod_trezorcrypto_monero_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_nist256p1),
     MP_ROM_PTR(&mod_trezorcrypto_nist256p1_module)},
    {MP_ROM_QSTR(MP_QSTR_groestl512),
     MP_ROM_PTR(&mod_trezorcrypto_Groestl512_type)},
    {MP_ROM_QSTR(MP_QSTR_hmac), MP_ROM_PTR(&mod_trezorcrypto_Hmac_type)},
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_nem), MP_ROM_PTR(&mod_trezorcrypto_nem_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_pbkdf2), MP_ROM_PTR(&mod_trezorcrypto_Pbkdf2_type)},
    {MP_ROM_QSTR(MP_QSTR_random), MP_ROM_PTR(&mod_trezorcrypto_random_module)},
    {MP_ROM_QSTR(MP_QSTR_ripemd160),
     MP_ROM_PTR(&mod_trezorcrypto_Ripemd160_type)},
    {MP_ROM_QSTR(MP_QSTR_secp256k1),
     MP_ROM_PTR(&mod_trezorcrypto_secp256k1_module)},
#if USE_SECP256K1_ZKP
    {MP_ROM_QSTR(MP_QSTR_bip340), MP_ROM_PTR(&mod_trezorcrypto_bip340_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_sha1), MP_ROM_PTR(&mod_trezorcrypto_Sha1_type)},
    {MP_ROM_QSTR(MP_QSTR_sha256), MP_ROM_PTR(&mod_trezorcrypto_Sha256_type)},
    {MP_ROM_QSTR(MP_QSTR_sha512), MP_ROM_PTR(&mod_trezorcrypto_Sha512_type)},
    {MP_ROM_QSTR(MP_QSTR_sha3_256),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256_type)},
    {MP_ROM_QSTR(MP_QSTR_sha3_512),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_512_type)},
    {MP_ROM_QSTR(MP_QSTR_shamir), MP_ROM_PTR(&mod_trezorcrypto_shamir_module)},
    {MP_ROM_QSTR(MP_QSTR_slip39), MP_ROM_PTR(&mod_trezorcrypto_slip39_module)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorcrypto_globals,
                            mp_module_trezorcrypto_globals_table);

const mp_obj_module_t mp_module_trezorcrypto = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorcrypto_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorcrypto, mp_module_trezorcrypto);

#ifdef USE_SECP256K1_ZKP
void secp256k1_default_illegal_callback_fn(const char *str, void *data) {
  (void)data;
  mp_raise_ValueError(str);
  return;
}

void secp256k1_default_error_callback_fn(const char *str, void *data) {
  (void)data;
  __fatal_error(NULL, str, __FILE__, __LINE__, __func__);
  return;
}
#endif

#endif  // MICROPY_PY_TREZORCRYPTO
