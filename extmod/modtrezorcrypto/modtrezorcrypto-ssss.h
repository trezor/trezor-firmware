/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/bignum.h"
#include "ssss.h"

typedef struct _mp_obj_SSSS_t {
    mp_obj_base_t base;
} mp_obj_SSSS_t;

STATIC mp_obj_t mod_TrezorCrypto_SSSS_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_SSSS_t *o = m_new_obj(mp_obj_SSSS_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.crypto.ssss.split(m: int, n: int, secret: bytes) -> tuple:
///     '''
///     Split secret to (M of N) shares using Shamir's Secret Sharing Scheme
///     '''
STATIC mp_obj_t mod_TrezorCrypto_SSSS_split(size_t n_args, const mp_obj_t *args) {
    mp_int_t m = mp_obj_get_int(args[1]);
    mp_int_t n = mp_obj_get_int(args[2]);
    mp_buffer_info_t secret;
    mp_get_buffer_raise(args[3], &secret, MP_BUFFER_READ);
    if (secret.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Length of the secret has to be 256 bits"));
    }
    if (m < 1 || n < 1 || m > 15 || n > 15 || m > n) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid number of shares"));
    }
    bignum256 sk;
    bignum256 shares[n];
    bn_read_be(secret.buf, &sk);
    if (!ssss_split(&sk, m, n, shares)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Error splitting secret"));
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
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_SSSS_split_obj, 4, 4, mod_TrezorCrypto_SSSS_split);

/// def trezor.crypto.ssss.combine(shares: tuple) -> bytes:
///     '''
///     Combine M shares of Shamir's Secret Sharing Scheme into secret
///     '''
STATIC mp_obj_t mod_TrezorCrypto_SSSS_combine(mp_obj_t self, mp_obj_t shares) {
    mp_uint_t n;
    mp_obj_t *share;
    if (MP_OBJ_IS_TYPE(shares, &mp_type_tuple)) {
        mp_obj_tuple_get(shares, &n, &share);
    } else
    if (MP_OBJ_IS_TYPE(shares, &mp_type_list)) {
        mp_obj_list_get(shares, &n, &share);
    } else {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "List or tuple expected"));
    }
    if (n < 1 || n > 15) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid number of shares"));
    }
    bignum256 bnshares[n];
    for (mp_uint_t i = 0; i < n; i++) {
        if (MP_OBJ_IS_TYPE(share[i], &mp_type_bytes)) {
            mp_buffer_info_t s;
            mp_get_buffer_raise(share[i], &s, MP_BUFFER_READ);
            bn_read_be(s.buf, &bnshares[n]);
        } else {
            memset(&bnshares[i], 0, sizeof(bignum256));
        }
    }
    bignum256 sk;
    if (!ssss_combine(bnshares, n, &sk)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Error combining secret"));
    }
    vstr_t vstr;
    vstr_init_len(&vstr, 32);
    bn_write_be(&sk, (uint8_t *)vstr.buf);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_SSSS_combine_obj, mod_TrezorCrypto_SSSS_combine);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_SSSS_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_split), MP_ROM_PTR(&mod_TrezorCrypto_SSSS_split_obj) },
    { MP_ROM_QSTR(MP_QSTR_combine), MP_ROM_PTR(&mod_TrezorCrypto_SSSS_combine_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_SSSS_locals_dict, mod_TrezorCrypto_SSSS_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_SSSS_type = {
    { &mp_type_type },
    .name = MP_QSTR_SSSS,
    .make_new = mod_TrezorCrypto_SSSS_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_SSSS_locals_dict,
};
