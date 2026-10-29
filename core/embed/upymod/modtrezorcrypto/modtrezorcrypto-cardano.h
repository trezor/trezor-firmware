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

#if !BITCOIN_ONLY

#include "py/objstr.h"

#include "../trezorobj.h"
#include "hdnode.h"

#include "bip39.h"
#include "cardano.h"
#include "curves.h"
#include "memzero.h"

/// package: trezorcrypto.cardano
/// from trezorcrypto.bip32 import HDNode

/// from trezorcrypto import secbytes

static mp_obj_t cardano_node(mp_obj_t source, uint32_t mode) {
  vault_request_t r = {.op = VAULT_CARDANO, .arg = mode};
  if (mp_obj_is_type(source, &mod_trezorcrypto_secbytes_type)) {
    r.arg |= 0x100;
    r.blob = secbytes_blob(MP_OBJ_TO_PTR(source));
  } else {
    mp_buffer_info_t input = {0};
    mp_get_buffer_raise(source, &input, MP_BUFFER_READ);
    if (!input.len || input.len > VAULT_DATA_SIZE)
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid Cardano input"));
    r.length = input.len;
    memcpy(r.data, input.buf, input.len);
  }
  mp_obj_HDNode_t *o = hdnode_new();
  vault_response_t out = {0};
  vault_raise(&r, &out);
  hdnode_set_blob(o, &out.blob);
  o->fingerprint = hdnode_fingerprint(hdnode_require(o));
  return MP_OBJ_FROM_PTR(o);
}

/// def derive_icarus(
///     binary_mnemonic: bytes | None,
///     passphrase: str,
///     trezor_derivation: bool,
///     callback: Callable[[int, int], None] | None = None,
/// ) -> secbytes:
///     """Derive a sealed Cardano master secret; None reads protected
///     storage."""
static mp_obj_t mod_trezorcrypto_cardano_derive_icarus(size_t n_args,
                                                       const mp_obj_t *args) {
  vault_request_t r = {
      .op = VAULT_CARDANO, .arg = 4, .child_num = mp_obj_is_true(args[2])};
  mp_buffer_info_t phrase = {0};
  mp_get_buffer_raise(args[1], &phrase, MP_BUFFER_READ);
  if (phrase.len > 200)
    mp_raise_ValueError(MP_ERROR_TEXT("Passphrase too long"));
  if (args[0] != mp_const_none) {
    mp_buffer_info_t binary = {0};
    mp_get_buffer_raise(args[0], &binary, MP_BUFFER_READ);
    if (binary.len > 33) mp_raise_ValueError(MP_ERROR_TEXT("Invalid mnemonic"));
    r.arg = 3;
    r.data[0] = binary.len;
    memcpy(r.data + 1, binary.buf, binary.len);
    r.length = binary.len + 1;
  }
  memcpy(r.data + r.length, phrase.buf, phrase.len);
  r.length += phrase.len;
  mp_obj_secbytes_t *value = secbytes_new(96);
  vault_response_t out = {0};
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_cardano_derive_icarus_obj, 3, 4,
    mod_trezorcrypto_cardano_derive_icarus);

/// def from_secret(secret: AnyBytes | secbytes) -> HDNode:
///     """Create a protected Cardano HD node from a master secret."""
static mp_obj_t mod_trezorcrypto_from_secret(mp_obj_t secret) {
  return cardano_node(secret, 0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_from_secret_obj,
                                 mod_trezorcrypto_from_secret);

/// def from_seed_slip23(seed: AnyBytes | secbytes) -> HDNode:
///     """Create a protected Cardano node via SLIP-23."""
static mp_obj_t mod_trezorcrypto_from_seed_slip23(mp_obj_t seed) {
  return cardano_node(seed, 1);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_from_seed_slip23_obj,
                                 mod_trezorcrypto_from_seed_slip23);

/// def from_seed_ledger(seed: AnyBytes | secbytes) -> HDNode:
///     """Create a protected Cardano node via Ledger derivation."""
static mp_obj_t mod_trezorcrypto_from_seed_ledger(mp_obj_t seed) {
  return cardano_node(seed, 2);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_from_seed_ledger_obj,
                                 mod_trezorcrypto_from_seed_ledger);

static const mp_rom_map_elem_t mod_trezorcrypto_cardano_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cardano)},
    {MP_ROM_QSTR(MP_QSTR_derive_icarus),
     MP_ROM_PTR(&mod_trezorcrypto_cardano_derive_icarus_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_secret),
     MP_ROM_PTR(&mod_trezorcrypto_from_secret_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_seed_slip23),
     MP_ROM_PTR(&mod_trezorcrypto_from_seed_slip23_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_seed_ledger),
     MP_ROM_PTR(&mod_trezorcrypto_from_seed_ledger_obj)},
};
static MP_DEFINE_CONST_DICT(mod_trezorcrypto_cardano_globals,
                            mod_trezorcrypto_cardano_globals_table);

static const mp_obj_module_t mod_trezorcrypto_cardano_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_cardano_globals,
};

#endif  // !BITCOIN_ONLY
