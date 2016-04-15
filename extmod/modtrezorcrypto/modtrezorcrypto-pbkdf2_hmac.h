/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "py/objstr.h"

#include "mbedtls/pkcs5.h"
#include "mbedtls/md_internal.h"

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

    const mbedtls_md_info_t *info = 0;
    if (hash_name.len == 6 && memcmp(hash_name.buf, "sha256", hash_name.len) == 0) {
        info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    } else
    if (hash_name.len == 6 && memcmp(hash_name.buf, "sha512", hash_name.len) == 0) {
        info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA512);
    }
    if (info == 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid hash_name"));
    }

    if (dklen == 0) {
        dklen = info->size;
    }
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    if (mbedtls_md_setup(&ctx, info, 1) == 0) {
        vstr_t vstr;
        vstr_init_len(&vstr, dklen);
        mbedtls_pkcs5_pbkdf2_hmac(&ctx, password.buf, password.len, salt.buf, salt.len, iterations, dklen, (uint8_t *)vstr.buf);
        mbedtls_md_free(&ctx);
        return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
    } else {
        mbedtls_md_free(&ctx);
        nlr_raise(mp_obj_new_exception_msg(&mp_type_RuntimeError, "mbedtls_md_setup failed"));
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorCrypto_pbkdf2_hmac_obj, 4, 5, mod_TrezorCrypto_pbkdf2_hmac);
