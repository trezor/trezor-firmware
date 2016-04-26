/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/pbkdf2.h"

// def pbkdf2_hmac(hash_name: str, password: bytes, salt: bytes, iterations: int, dklen:int=None) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_pbkdf2_hmac(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t hash_name;
    mp_get_buffer_raise(args[0], &hash_name, MP_BUFFER_READ);
    mp_buffer_info_t password;
    mp_get_buffer_raise(args[1], &password, MP_BUFFER_READ);
    mp_buffer_info_t salt;
    mp_get_buffer_raise(args[2], &salt, MP_BUFFER_READ);
    mp_int_t iterations = mp_obj_get_int(args[3]);
    mp_int_t dklen = (n_args > 4) ? mp_obj_get_int(args[4]) : 0;

    int digestsize = 0;
    if (hash_name.len == 6 && memcmp(hash_name.buf, "sha256", hash_name.len) == 0) {
        digestsize = 32;
    } else
    if (hash_name.len == 6 && memcmp(hash_name.buf, "sha512", hash_name.len) == 0) {
        digestsize = 64;
    }
    if (digestsize == 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid hash_name"));
    }
    if (dklen == 0) {
        dklen = digestsize;
    }
    vstr_t vstr;
    vstr_init_len(&vstr, dklen);
    if (digestsize == 32) {
        pbkdf2_hmac_sha256(password.buf, password.len, salt.buf, salt.len, iterations, (uint8_t *)vstr.buf, dklen, NULL);
    }
    if (digestsize == 64) {
        pbkdf2_hmac_sha512(password.buf, password.len, salt.buf, salt.len, iterations, (uint8_t *)vstr.buf, dklen, NULL);
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_pbkdf2_hmac_obj, 4, 5, mod_TrezorCrypto_pbkdf2_hmac);
