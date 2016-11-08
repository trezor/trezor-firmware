/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/ecdsa.h"
#include "trezor-crypto/nist256p1.h"

typedef struct _mp_obj_Nist256p1_t {
    mp_obj_base_t base;
} mp_obj_Nist256p1_t;

STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Nist256p1_t *o = m_new_obj(mp_obj_Nist256p1_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.crypto.curve.nist256p1.generate_secret() -> bytes:
///     '''
///     Generate secret key.
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_generate_secret(mp_obj_t self) {
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    for (;;) {
        random_buffer((uint8_t *)vstr.buf, 32);
        // check whether secret > 0 && secret < curve_order
        if (0 == memcmp(vstr.buf, "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 32)) continue;
        if (0 <= memcmp(vstr.buf, "\xFF\xFF\xFF\xFF\x00\x00\x00\x00\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xBC\xE6\xFA\xAD\xA7\x17\x9E\x84\xF3\xB9\xCA\xC2\xFC\x63\x25\x51", 32)) continue;
        break;
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_Nist256p1_generate_secret_obj, mod_TrezorCrypto_Nist256p1_generate_secret);

/// def trezor.crypto.curve.nist256p1.publickey(secret_key: bytes, compressed: bool=True) -> bytes:
///     '''
///     Computes public key from secret key.
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_publickey(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t sk;
    mp_get_buffer_raise(args[1], &sk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    bool compressed = n_args < 3 || args[2] == mp_const_true;
    vstr_t vstr;
    if (compressed) {
        vstr_init_len(&vstr, 33);
        ecdsa_get_public_key33(&nist256p1, (const uint8_t *)sk.buf, (uint8_t *)vstr.buf);
    } else {
        vstr_init_len(&vstr, 65);
        ecdsa_get_public_key65(&nist256p1, (const uint8_t *)sk.buf, (uint8_t *)vstr.buf);
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_Nist256p1_publickey_obj, 2, 3, mod_TrezorCrypto_Nist256p1_publickey);

/// def trezor.crypto.curve.nist256p1.sign(secret_key: bytes, digest: bytes) -> bytes:
///     '''
///     Uses secret key to produce the signature of the digest.
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_sign(mp_obj_t self, mp_obj_t secret_key, mp_obj_t digest) {
    mp_buffer_info_t sk, dig;
    mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
    mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    if (dig.len != 32) {
        mp_raise_ValueError("Invalid length of digest");
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 64);
    uint8_t pby;
    if (0 != ecdsa_sign_digest(&nist256p1, (const uint8_t *)sk.buf, (const uint8_t *)dig.buf, (uint8_t *)vstr.buf, &pby, NULL)) {  // TODO: is_canonical
        mp_raise_ValueError("Signing failed");
    }
    (void)pby;
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Nist256p1_sign_obj, mod_TrezorCrypto_Nist256p1_sign);

/// def trezor.crypto.curve.nist256p1.verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
///     '''
///     Uses public key to verify the signature of the digest.
///     Returns True on success.
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_verify(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t pk, sig, dig;
    mp_get_buffer_raise(args[1], &pk, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &sig, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &dig, MP_BUFFER_READ);
    if (pk.len != 33 && pk.len != 65) {
        mp_raise_ValueError("Invalid length of public key");
    }
    if (sig.len != 64) {
        mp_raise_ValueError("Invalid length of signature");
    }
    if (dig.len != 32) {
        mp_raise_ValueError("Invalid length of digest");
    }
    return mp_obj_new_bool(0 == ecdsa_verify_digest(&nist256p1, (const uint8_t *)pk.buf, (const uint8_t *)sig.buf, (const uint8_t *)dig.buf));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_Nist256p1_verify_obj, 4, 4, mod_TrezorCrypto_Nist256p1_verify);

/// def trezor.crypto.curve.nist256p1.multiply(secret_key: bytes, public_key: bytes) -> bytes:
///     '''
///     Multiplies point defined by public_key with scalar defined by secret_key
///     Useful for ECDH
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Nist256p1_multiply(mp_obj_t self, mp_obj_t secret_key, mp_obj_t public_key) {
    mp_buffer_info_t sk, pk;
    mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
    mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
    if (sk.len != 32) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    if (pk.len != 33 && pk.len != 65) {
        mp_raise_ValueError("Invalid length of public key");
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 65);
    if (0 != ecdh_multiply(&nist256p1, (const uint8_t *)sk.buf, (const uint8_t *)pk.buf, (uint8_t *)vstr.buf)) {
        mp_raise_ValueError("Multiply failed");
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Nist256p1_multiply_obj, mod_TrezorCrypto_Nist256p1_multiply);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Nist256p1_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_generate_secret), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_generate_secret_obj) },
    { MP_ROM_QSTR(MP_QSTR_publickey), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_publickey_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_sign_obj) },
    { MP_ROM_QSTR(MP_QSTR_verify), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_verify_obj) },
    { MP_ROM_QSTR(MP_QSTR_multiply), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_multiply_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Nist256p1_locals_dict, mod_TrezorCrypto_Nist256p1_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Nist256p1_type = {
    { &mp_type_type },
    .name = MP_QSTR_Nist256p1,
    .make_new = mod_TrezorCrypto_Nist256p1_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Nist256p1_locals_dict,
};
