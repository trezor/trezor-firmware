/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "py/objstr.h"

#include "ed25519-donna/ed25519.h"
#include "ed25519-donna/ed25519-keccak.h"

#include "rand.h"

/// def generate_secret() -> bytes:
///     '''
///     Generate secret key.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_generate_secret() {
    uint8_t out[32];
    random_buffer(out, 32);
    // taken from https://cr.yp.to/ecdh.html
    out[0] &= 248;
    out[31] &= 127;
    out[31] |= 64;
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_ed25519_generate_secret_obj, mod_trezorcrypto_ed25519_generate_secret);

/// def publickey(secret_key: bytes) -> bytes:
///     '''
///     Computes public key from secret key.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_publickey(mp_obj_t secret_key) {
    mp_buffer_info_t sk;
    mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    uint8_t out[32];
    ed25519_publickey(*(const ed25519_secret_key *)sk.buf, *(ed25519_public_key *)out);
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_ed25519_publickey_obj, mod_trezorcrypto_ed25519_publickey);

/// def sign(secret_key: bytes, message: bytes, hasher: str='') -> bytes:
///     '''
///     Uses secret key to produce the signature of message.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_sign(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t sk, msg;
    mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
    mp_get_buffer_raise(args[1], &msg, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    if (msg.len == 0) {
        mp_raise_ValueError("Empty data to sign");
    }
    ed25519_public_key pk;
    uint8_t out[64];
    mp_buffer_info_t hash_func;

    if (n_args == 3) {
        mp_get_buffer_raise(args[2], &hash_func, MP_BUFFER_READ);
        // if hash_func == 'keccak':
        if (memcmp(hash_func.buf, "keccak", sizeof("keccak")) == 0) {
            ed25519_publickey_keccak(*(const ed25519_secret_key *)sk.buf, pk);
            ed25519_sign_keccak(msg.buf, msg.len, *(const ed25519_secret_key *)sk.buf, pk, *(ed25519_signature *)out);
        } else {
            mp_raise_ValueError("Unknown hash function");
        }
    } else {
        ed25519_publickey(*(const ed25519_secret_key *)sk.buf, pk);
        ed25519_sign(msg.buf, msg.len, *(const ed25519_secret_key *)sk.buf, pk, *(ed25519_signature *)out);
    }

    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_ed25519_sign_obj, 2, 3, mod_trezorcrypto_ed25519_sign);

/// def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
///     '''
///     Uses public key to verify the signature of the message.
///     Returns True on success.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_verify(mp_obj_t public_key, mp_obj_t signature, mp_obj_t message) {
    mp_buffer_info_t pk, sig, msg;
    mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
    mp_get_buffer_raise(signature, &sig, MP_BUFFER_READ);
    mp_get_buffer_raise(message, &msg, MP_BUFFER_READ);
    if (pk.len != 32) {
        mp_raise_ValueError("Invalid length of public key");
    }
    if (sig.len != 64) {
        mp_raise_ValueError("Invalid length of signature");
    }
    if (msg.len == 0) {
        mp_raise_ValueError("Empty data to verify");
    }
    return (0 == ed25519_sign_open(msg.buf, msg.len, *(const ed25519_public_key *)pk.buf, *(const ed25519_signature *)sig.buf)) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_ed25519_verify_obj, mod_trezorcrypto_ed25519_verify);

/// def cosi_combine_publickeys(public_keys: List[bytes]) -> bytes:
///     '''
///     Combines a list of public keys used in COSI cosigning scheme.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_cosi_combine_publickeys(mp_obj_t public_keys) {
    size_t pklen;
    mp_obj_t *pkitems;
    mp_obj_get_array(public_keys, &pklen, &pkitems);
    if (pklen > 15) {
        mp_raise_ValueError("Can't combine more than 15 public keys");
    }
    mp_buffer_info_t buf;
    ed25519_public_key pks[pklen];
    for (int i = 0; i < pklen; i++) {
        mp_get_buffer_raise(pkitems[i], &buf, MP_BUFFER_READ);
        if (buf.len != 32) {
            mp_raise_ValueError("Invalid length of public key");
        }
        memcpy(pks[i], buf.buf, buf.len);
    }
    uint8_t out[32];
    if (0 != ed25519_cosi_combine_publickeys(*(ed25519_public_key *)out, pks, pklen)) {
        mp_raise_ValueError("Error combining public keys");
    }
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_ed25519_cosi_combine_publickeys_obj, mod_trezorcrypto_ed25519_cosi_combine_publickeys);

/// def cosi_combine_signatures(R: bytes, signatures: List[bytes]) -> bytes:
///     '''
///     Combines a list of signatures used in COSI cosigning scheme.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_cosi_combine_signatures(mp_obj_t R, mp_obj_t signatures) {
    mp_buffer_info_t sigR;
    mp_get_buffer_raise(R, &sigR, MP_BUFFER_READ);
    if (sigR.len != 32) {
        mp_raise_ValueError("Invalid length of R");
    }
    size_t siglen;
    mp_obj_t *sigitems;
    mp_obj_get_array(signatures, &siglen, &sigitems);
    if (siglen > 15) {
        mp_raise_ValueError("Can't combine more than 15 COSI signatures");
    }
    mp_buffer_info_t buf;
    ed25519_cosi_signature sigs[siglen];
    for (int i = 0; i < siglen; i++) {
        mp_get_buffer_raise(sigitems[i], &buf, MP_BUFFER_READ);
        if (buf.len != 32) {
            mp_raise_ValueError("Invalid length of COSI signature");
        }
        memcpy(sigs[i], buf.buf, buf.len);
    }
    uint8_t out[64];
    ed25519_cosi_combine_signatures(*(ed25519_signature *)out, *(const ed25519_public_key *)sigR.buf, sigs, siglen);
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_ed25519_cosi_combine_signatures_obj, mod_trezorcrypto_ed25519_cosi_combine_signatures);

/// def cosi_sign(secret_key: bytes, message: bytes, nonce: bytes, sigR: bytes, combined_pubkey: bytes) -> bytes:
///     '''
///     Produce signature of message using COSI cosigning scheme.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ed25519_cosi_sign(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t sk, msg, nonce, sigR, pk;
    mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
    mp_get_buffer_raise(args[1], &msg, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &nonce, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &sigR, MP_BUFFER_READ);
    mp_get_buffer_raise(args[4], &pk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    if (nonce.len != 32) {
        mp_raise_ValueError("Invalid length of nonce");
    }
    if (sigR.len != 32) {
        mp_raise_ValueError("Invalid length of R");
    }
    if (pk.len != 32) {
        mp_raise_ValueError("Invalid length of aggregated public key");
    }
    uint8_t out[32];
    ed25519_cosi_sign(msg.buf, msg.len, *(const ed25519_secret_key *)sk.buf, *(const ed25519_secret_key *)nonce.buf, *(const ed25519_public_key *)sigR.buf, *(const ed25519_secret_key *)pk.buf, *(ed25519_cosi_signature *)out);
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_ed25519_cosi_sign_obj, 5, 5, mod_trezorcrypto_ed25519_cosi_sign);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_ed25519_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ed25519) },
    { MP_ROM_QSTR(MP_QSTR_generate_secret), MP_ROM_PTR(&mod_trezorcrypto_ed25519_generate_secret_obj) },
    { MP_ROM_QSTR(MP_QSTR_publickey), MP_ROM_PTR(&mod_trezorcrypto_ed25519_publickey_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypto_ed25519_sign_obj) },
    { MP_ROM_QSTR(MP_QSTR_verify), MP_ROM_PTR(&mod_trezorcrypto_ed25519_verify_obj) },
    { MP_ROM_QSTR(MP_QSTR_cosi_combine_publickeys), MP_ROM_PTR(&mod_trezorcrypto_ed25519_cosi_combine_publickeys_obj) },
    { MP_ROM_QSTR(MP_QSTR_cosi_combine_signatures), MP_ROM_PTR(&mod_trezorcrypto_ed25519_cosi_combine_signatures_obj) },
    { MP_ROM_QSTR(MP_QSTR_cosi_sign), MP_ROM_PTR(&mod_trezorcrypto_ed25519_cosi_sign_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_ed25519_globals, mod_trezorcrypto_ed25519_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_ed25519_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_ed25519_globals,
};
