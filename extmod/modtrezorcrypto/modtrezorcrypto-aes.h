/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/aes.h"

/*
*/

typedef struct _mp_obj_AES_t {
    mp_obj_base_t base;
    union {
        aes_encrypt_ctx encrypt_ctx;
        aes_decrypt_ctx decrypt_ctx;
    } ctx;
    mp_int_t mode;
    uint8_t iv[AES_BLOCK_SIZE];
    uint8_t ctr[AES_BLOCK_SIZE];
} mp_obj_AES_t;

/// def trezor.crypto.aes.AES(mode:int, key: bytes, iv: bytes=None) -> AES
STATIC mp_obj_t mod_TrezorCrypto_AES_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    mp_obj_AES_t *o = m_new_obj(mp_obj_AES_t);
    o->base.type = type;
    o->mode = mp_obj_get_int(args[0]);
    if ((o->mode & 0x7F) > 0x04) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid AES mode"));
    }
    mp_buffer_info_t key;
    mp_get_buffer_raise(args[1], &key, MP_BUFFER_READ);
    if (key.len != 16 && key.len != 24 && key.len != 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of key (has to be 128, 192 or 256 bits)"));
    }
    if (n_args > 2) {
        mp_buffer_info_t iv;
        mp_get_buffer_raise(args[2], &iv, MP_BUFFER_READ);
        if (iv.len != AES_BLOCK_SIZE) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid length of initialization vector (has to be 128 bits)"));
        }
        memcpy(o->iv, iv.buf, AES_BLOCK_SIZE);
    } else {
        memset(o->iv, 0, AES_BLOCK_SIZE);
    }
    memset(o->ctr, 0, AES_BLOCK_SIZE);
    switch (key.len) {
        case 16:
            if (o->mode == 0x80 || o->mode == 0x81) {
                aes_decrypt_key128(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key128(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
        case 24:
            if (o->mode == 0x80 || o->mode == 0x81) {
                aes_decrypt_key192(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key192(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
        case 32:
            if (o->mode == 0x80 || o->mode == 0x81) {
                aes_decrypt_key256(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key256(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
    }
    return MP_OBJ_FROM_PTR(o);
}

/// def AES.crypt(self, data: bytes) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_AES_update(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
    mp_obj_AES_t *o = MP_OBJ_TO_PTR(self);
    vstr_t vstr;
    vstr_init_len(&vstr, buf.len);
    switch (o->mode & 0x7F) {
        case 0x00: // ECB
            if (buf.len & (AES_BLOCK_SIZE - 1)) {
                nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid data length"));
            }
            if ((o->mode & 0x80) == 0x00) {
                aes_ecb_encrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, &(o->ctx.encrypt_ctx));
            } else {
                aes_ecb_decrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, &(o->ctx.decrypt_ctx));
            }
            break;
        case 0x01: // CBC
            if (buf.len & (AES_BLOCK_SIZE - 1)) {
                nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid data length"));
            }
            if ((o->mode & 0x80) == 0x00) {
                aes_cbc_encrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            } else {
                aes_cbc_decrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->iv, &(o->ctx.decrypt_ctx));
            }
            break;
        case 0x02: // CFB
            if ((o->mode & 0x80) == 0x00) {
                aes_cfb_encrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            } else {
                aes_cfb_decrypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            }
            break;
        case 0x03: // OFB (encrypt == decrypt)
            aes_ofb_crypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            break;
        case 0x04: // CTR (encrypt == decrypt)
            aes_ctr_crypt(buf.buf, (unsigned char *)vstr.buf, buf.len, o->ctr, aes_ctr_cbuf_inc, &(o->ctx.encrypt_ctx));
            break;
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_AES_update_obj, mod_TrezorCrypto_AES_update);

STATIC mp_obj_t mod_TrezorCrypto_AES___del__(mp_obj_t self) {
    mp_obj_AES_t *o = MP_OBJ_TO_PTR(self);
    memset(&(o->ctx), 0, sizeof(aes_encrypt_ctx));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorCrypto_AES___del___obj, mod_TrezorCrypto_AES___del__);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_AES_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_TrezorCrypto_AES_update_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_TrezorCrypto_AES___del___obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_AES_locals_dict, mod_TrezorCrypto_AES_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_AES_type = {
    { &mp_type_type },
    .name = MP_QSTR_AES,
    .make_new = mod_TrezorCrypto_AES_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_AES_locals_dict,
};
