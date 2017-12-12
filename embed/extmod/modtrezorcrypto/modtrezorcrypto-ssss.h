/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "bignum.h"
#include "ssss.h"

/// def split(m: int, n: int, secret: bytes) -> tuple:
///     '''
///     Split secret to (M of N) shares using Shamir's Secret Sharing Scheme.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ssss_split(mp_obj_t m_obj, mp_obj_t n_obj, mp_obj_t secret_obj) {
    mp_int_t m = mp_obj_get_int(m_obj);
    mp_int_t n = mp_obj_get_int(n_obj);
    mp_buffer_info_t secret;
    mp_get_buffer_raise(secret_obj, &secret, MP_BUFFER_READ);
    if (secret.len != 32) {
        mp_raise_ValueError("Length of the secret has to be 256 bits");
    }
    if (m < 1 || n < 1 || m > 15 || n > 15 || m > n) {
        mp_raise_ValueError("Invalid number of shares");
    }
    bignum256 sk;
    bignum256 shares[n];
    bn_read_be(secret.buf, &sk);
    if (!ssss_split(&sk, m, n, shares)) {
        mp_raise_ValueError("Error splitting secret");
    }
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(n, NULL));
    vstr_t vstr[n];
    for (int i = 0; i < n; i++) {
        vstr_init_len(&vstr[i], secret.len);
        bn_write_be(&shares[i], secret.buf);
        tuple->items[i] = mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr[i]);
    }
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_ssss_split_obj, mod_trezorcrypto_ssss_split);

/// def combine(shares: tuple) -> bytes:
///     '''
///     Combine M shares of Shamir's Secret Sharing Scheme into secret.
///     '''
STATIC mp_obj_t mod_trezorcrypto_ssss_combine(mp_obj_t shares_obj) {
    size_t n;
    mp_obj_t *share;
    mp_obj_get_array(shares_obj, &n, &share);
    if (n < 1 || n > 15) {
        mp_raise_ValueError("Invalid number of shares");
    }
    bignum256 bnshares[n];
    for (size_t i = 0; i < n; i++) {
        if (MP_OBJ_IS_TYPE(share[i], &mp_type_bytes)) {
            mp_buffer_info_t s;
            mp_get_buffer_raise(share[i], &s, MP_BUFFER_READ);
            if (s.len != 32) {
                mp_raise_ValueError("Length of share has to be 256 bits");
            }
            bn_read_be(s.buf, &bnshares[n]);
        } else {
            memset(&bnshares[i], 0, sizeof(bignum256));
        }
    }
    bignum256 sk;
    if (!ssss_combine(bnshares, n, &sk)) {
        mp_raise_ValueError("Error combining secret");
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    bn_write_be(&sk, (uint8_t *)vstr.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_ssss_combine_obj, mod_trezorcrypto_ssss_combine);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_ssss_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ssss) },
    { MP_ROM_QSTR(MP_QSTR_split), MP_ROM_PTR(&mod_trezorcrypto_ssss_split_obj) },
    { MP_ROM_QSTR(MP_QSTR_combine), MP_ROM_PTR(&mod_trezorcrypto_ssss_combine_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_ssss_globals, mod_trezorcrypto_ssss_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_ssss_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_ssss_globals,
};
