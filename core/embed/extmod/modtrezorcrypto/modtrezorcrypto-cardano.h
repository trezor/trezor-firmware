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

#include "embed/extmod/trezorobj.h"
#include "hdnode.h"

#include "bip39.h"
#include "cardano.h"
#include "curves.h"
#include "memzero.h"

/// package: trezorcrypto.cardano

/// def derive_icarus_trezor(
///     mnemonic: str,
///     passphrase: str,
///     callback: Callable[[int, int], None] | None = None,
/// ) -> bytes:
///     """
///     Derives a Cardano master secret from a mnemonic and passphrase using the
///     Icarus-Trezor derivation scheme. This differs from the Icarus scheme by
///     including checksum if the mnemonic is 24 words.
///     """
STATIC mp_obj_t mod_trezorcrypto_cardano_derive_icarus_trezor(
    size_t n_args, const mp_obj_t *args) {
  mp_buffer_info_t mnemo = {0}, phrase = {0};
  mp_get_buffer_raise(args[0], &mnemo, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &phrase, MP_BUFFER_READ);
  const char *pmnemonic = mnemo.len > 0 ? mnemo.buf : "";
  const char *ppassphrase = phrase.len > 0 ? phrase.buf : "";

  uint8_t mnemonic_bits[64] = {0};
  int mnemonic_bits_len = mnemonic_to_bits(pmnemonic, mnemonic_bits);

  if (mnemonic_bits_len == 0) {
    mp_raise_ValueError("Invalid mnemonic");
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, CARDANO_SECRET_LENGTH);

  void (*callback)(uint32_t current, uint32_t total) = NULL;
  if (n_args > 2) {
    // generate with a progress callback
    ui_wait_callback = args[2];
    callback = wrapped_ui_wait_callback;
  }

  // BEWARE: unlike `derive_icarus`, we are passing the raw result of
  // `mnemonic_bits`, i.e., entropy + checksum bits. More info at
  // https://github.com/trezor/trezor-firmware/issues/1387 and CIP-3
  const int res = secret_from_entropy_cardano_icarus(
      (const uint8_t *)ppassphrase, phrase.len, mnemonic_bits,
      mnemonic_bits_len / 8, (uint8_t *)vstr.buf, callback);

  ui_wait_callback = mp_const_none;

  if (res != 1) {
    mp_raise_msg(&mp_type_RuntimeError,
                 "Unexpected failure in Icarus derivation.");
  }

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_cardano_derive_icarus_trezor_obj, 2, 3,
    mod_trezorcrypto_cardano_derive_icarus_trezor);

/// def from_secret(secret: bytes) -> HDNode:
///     """
///     Creates a Cardano HD node from a master secret.
///     """
STATIC mp_obj_t mod_trezorcrypto_from_secret(mp_obj_t secret) {
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(secret, &bufinfo, MP_BUFFER_READ);
  if (bufinfo.len != CARDANO_SECRET_LENGTH) {
    mp_raise_ValueError("Invalid secret length");
  }

  mp_obj_HDNode_t *o = m_new_obj_with_finaliser(mp_obj_HDNode_t);
  o->base.type = &mod_trezorcrypto_HDNode_type;
  const int res = hdnode_from_secret_cardano(bufinfo.buf, &o->hdnode);
  if (res != 1) {
    mp_raise_msg(&mp_type_RuntimeError,
                 "Unexpected failure in constructing Cardano node.");
  }
  o->fingerprint = hdnode_fingerprint(&o->hdnode);
  return MP_OBJ_FROM_PTR(o);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_from_secret_obj,
                                 mod_trezorcrypto_from_secret);

/// def from_seed_slip23(seed: bytes) -> HDNode:
///    """
///    Creates a Cardano HD node from a seed via SLIP-23 derivation.
///    """
STATIC mp_obj_t mod_trezorcrypto_from_seed_slip23(mp_obj_t seed) {
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(seed, &bufinfo, MP_BUFFER_READ);
  if (bufinfo.len == 0) {
    mp_raise_ValueError("Invalid seed");
  }

  uint8_t secret[CARDANO_SECRET_LENGTH] = {0};
  HDNode hdnode = {0};
  int res = 0;

  res = secret_from_seed_cardano_slip23(bufinfo.buf, bufinfo.len, secret);
  if (res != 1) {
    mp_raise_msg(&mp_type_RuntimeError,
                 "Unexpected failure in SLIP-23 derivation.");
  }
  res = hdnode_from_secret_cardano(secret, &hdnode);
  if (res != 1) {
    mp_raise_msg(&mp_type_RuntimeError,
                 "Unexpected failure in constructing Cardano node.");
  }

  mp_obj_HDNode_t *o = m_new_obj_with_finaliser(mp_obj_HDNode_t);
  o->base.type = &mod_trezorcrypto_HDNode_type;
  o->hdnode = hdnode;
  o->fingerprint = hdnode_fingerprint(&o->hdnode);
  return MP_OBJ_FROM_PTR(o);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_from_seed_slip23_obj,
                                 mod_trezorcrypto_from_seed_slip23);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_cardano_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cardano)},
    {MP_ROM_QSTR(MP_QSTR_derive_icarus_trezor),
     MP_ROM_PTR(&mod_trezorcrypto_cardano_derive_icarus_trezor_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_secret),
     MP_ROM_PTR(&mod_trezorcrypto_from_secret_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_seed_slip23),
     MP_ROM_PTR(&mod_trezorcrypto_from_seed_slip23_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_cardano_globals,
                            mod_trezorcrypto_cardano_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_cardano_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_cardano_globals,
};

#endif  // !BITCOIN_ONLY
