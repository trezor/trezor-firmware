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

#include "aes/aes.h"
#include "memzero.h"

/// class AES:
///     '''
///     AES context.
///     '''
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

enum {
    ECB = 0x00,
    CBC = 0x01,
    CFB = 0x02,
    OFB = 0x03,
    CTR = 0x04,
    Encrypt = 0x40,
    Decrypt = 0x80,
};

#define AESModeMask 0x3F
#define AESDirMask  0xC0

/// def __init__(self, mode: int, key: bytes, iv: bytes = None) -> None:
///     '''
///     Initialize AES context.
///     '''
STATIC mp_obj_t mod_trezorcrypto_AES_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    mp_obj_AES_t *o = m_new_obj(mp_obj_AES_t);
    o->base.type = type;
    o->mode = mp_obj_get_int(args[0]);
    if ((o->mode & AESModeMask) > 0x04) {
        mp_raise_ValueError("Invalid AES mode");
    }
    mp_buffer_info_t key;
    mp_get_buffer_raise(args[1], &key, MP_BUFFER_READ);
    if (key.len != 16 && key.len != 24 && key.len != 32) {
        mp_raise_ValueError("Invalid length of key (has to be 128, 192 or 256 bits)");
    }
    if (n_args > 2) {
        mp_buffer_info_t iv;
        mp_get_buffer_raise(args[2], &iv, MP_BUFFER_READ);
        if (iv.len != AES_BLOCK_SIZE) {
            mp_raise_ValueError("Invalid length of initialization vector (has to be 128 bits)");
        }
        memcpy(o->iv, iv.buf, AES_BLOCK_SIZE);
    } else {
        memset(o->iv, 0, AES_BLOCK_SIZE);
    }
    memset(o->ctr, 0, AES_BLOCK_SIZE);
    switch (key.len) {
        case 16:
            if (o->mode == (ECB | Decrypt) || o->mode == (CBC | Decrypt)) {
                aes_decrypt_key128(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key128(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
        case 24:
            if (o->mode == (ECB | Decrypt) || o->mode == (CBC | Decrypt)) {
                aes_decrypt_key192(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key192(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
        case 32:
            if (o->mode == (ECB | Decrypt) || o->mode == (CBC |Decrypt)) {
                aes_decrypt_key256(key.buf, &(o->ctx.decrypt_ctx));
            } else {
                aes_encrypt_key256(key.buf, &(o->ctx.encrypt_ctx));
            }
            break;
    }
    return MP_OBJ_FROM_PTR(o);
}

/// def update(self, data: bytes) -> bytes:
///     '''
///     Update AES context with data.
///     '''
STATIC mp_obj_t mod_trezorcrypto_AES_update(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
    if (buf.len == 0) {
        return mp_const_empty_bytes;
    }
    vstr_t vstr;
    vstr_init_len(&vstr, buf.len);
    mp_obj_AES_t *o = MP_OBJ_TO_PTR(self);
    switch (o->mode & AESModeMask) {
        case ECB:
            if (buf.len & (AES_BLOCK_SIZE - 1)) {
                mp_raise_ValueError("Invalid data length");
            }
            if ((o->mode & AESDirMask) == Encrypt) {
                aes_ecb_encrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, &(o->ctx.encrypt_ctx));
            } else {
                aes_ecb_decrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, &(o->ctx.decrypt_ctx));
            }
            break;
        case CBC:
            if (buf.len & (AES_BLOCK_SIZE - 1)) {
                mp_raise_ValueError("Invalid data length");
            }
            if ((o->mode & AESDirMask) == Encrypt) {
                aes_cbc_encrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            } else {
                aes_cbc_decrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->iv, &(o->ctx.decrypt_ctx));
            }
            break;
        case CFB:
            if ((o->mode & AESDirMask) == Encrypt) {
                aes_cfb_encrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            } else {
                aes_cfb_decrypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            }
            break;
        case OFB: // (encrypt == decrypt)
            aes_ofb_crypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->iv, &(o->ctx.encrypt_ctx));
            break;
        case CTR: // (encrypt == decrypt)
            aes_ctr_crypt(buf.buf, (uint8_t *)vstr.buf, buf.len, o->ctr, aes_ctr_cbuf_inc, &(o->ctx.encrypt_ctx));
            break;
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AES_update_obj, mod_trezorcrypto_AES_update);

STATIC mp_obj_t mod_trezorcrypto_AES___del__(mp_obj_t self) {
    mp_obj_AES_t *o = MP_OBJ_TO_PTR(self);
    memzero(&(o->ctx), sizeof(aes_encrypt_ctx));
    memzero(o->iv, AES_BLOCK_SIZE);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_AES___del___obj, mod_trezorcrypto_AES___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_AES_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_trezorcrypto_AES_update_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorcrypto_AES___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_ECB), MP_OBJ_NEW_SMALL_INT(ECB) },
    { MP_ROM_QSTR(MP_QSTR_CBC), MP_OBJ_NEW_SMALL_INT(CBC) },
    { MP_ROM_QSTR(MP_QSTR_CFB), MP_OBJ_NEW_SMALL_INT(CFB) },
    { MP_ROM_QSTR(MP_QSTR_OFB), MP_OBJ_NEW_SMALL_INT(OFB) },
    { MP_ROM_QSTR(MP_QSTR_CTR), MP_OBJ_NEW_SMALL_INT(CTR) },
    { MP_ROM_QSTR(MP_QSTR_Encrypt), MP_OBJ_NEW_SMALL_INT(Encrypt) },
    { MP_ROM_QSTR(MP_QSTR_Decrypt), MP_OBJ_NEW_SMALL_INT(Decrypt) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_AES_locals_dict, mod_trezorcrypto_AES_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_AES_type = {
    { &mp_type_type },
    .name = MP_QSTR_AES,
    .make_new = mod_trezorcrypto_AES_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_AES_locals_dict,
};
