/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"

#include "trezor-crypto/bip39.h"

typedef struct _mp_obj_Bip39_t {
    mp_obj_base_t base;
} mp_obj_Bip39_t;

STATIC mp_obj_t mod_TrezorCrypto_Bip39_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Bip39_t *o = m_new_obj(mp_obj_Bip39_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.crypto.bip39.generate(strength: int) -> str:
///     '''
///     Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits)
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Bip39_generate(mp_obj_t self, mp_obj_t strength) {
    int bits = mp_obj_get_int(strength);
    if (bits % 32 || bits < 128 || bits > 256) {
        mp_raise_ValueError("Invalid bit strength (only 128, 160, 192, 224 and 256 values are allowed)");
    }
    const char *mnemo = mnemonic_generate(bits);
    vstr_t vstr;
    vstr_init_len(&vstr, strlen(mnemo));
    strcpy(vstr.buf, mnemo);
    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_generate_obj, mod_TrezorCrypto_Bip39_generate);

/// def trezor.crypto.bip39.from_data(data: bytes) -> str:
///     '''
///     Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes)
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Bip39_from_data(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t bin;
    mp_get_buffer_raise(data, &bin, MP_BUFFER_READ);
    if (bin.len % 4 || bin.len < 16 || bin.len > 32) {
        mp_raise_ValueError("Invalid data length (only 16, 20, 24, 28 and 32 bytes are allowed)");
    }
    const char *mnemo = mnemonic_from_data(bin.buf, bin.len);
    vstr_t vstr;
    vstr_init_len(&vstr, strlen(mnemo));
    strcpy(vstr.buf, mnemo);
    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_from_data_obj, mod_TrezorCrypto_Bip39_from_data);

/// def trezor.crypto.bip39.check(mnemonic: str) -> bool:
///     '''
///     Check whether given mnemonic is valid
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Bip39_check(mp_obj_t self, mp_obj_t mnemonic) {
    mp_buffer_info_t text;
    mp_get_buffer_raise(mnemonic, &text, MP_BUFFER_READ);
    return (text.len > 0 && mnemonic_check(text.buf)) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_check_obj, mod_TrezorCrypto_Bip39_check);

/// def trezor.crypto.bip39.seed(mnemonic: str, passphrase: str) -> bytes:
///     '''
///     Generate seed from mnemonic and passphrase
///     '''
STATIC mp_obj_t mod_TrezorCrypto_Bip39_seed(mp_obj_t self, mp_obj_t mnemonic, mp_obj_t passphrase) {
    mp_buffer_info_t mnemo;
    mp_buffer_info_t phrase;
    mp_get_buffer_raise(mnemonic, &mnemo, MP_BUFFER_READ);
    mp_get_buffer_raise(passphrase, &phrase, MP_BUFFER_READ);
    vstr_t vstr;
    vstr_init_len(&vstr, 64);
    const char *pmnemonic = mnemo.len > 0 ? mnemo.buf : "";
    const char *ppassphrase = phrase.len > 0 ? phrase.buf : "";
    mnemonic_to_seed(pmnemonic, ppassphrase, (uint8_t *)vstr.buf, NULL); // no callback for now
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorCrypto_Bip39_seed_obj, mod_TrezorCrypto_Bip39_seed);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Bip39_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_generate), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_generate_obj) },
    { MP_ROM_QSTR(MP_QSTR_from_data), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_from_data_obj) },
    { MP_ROM_QSTR(MP_QSTR_check), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_check_obj) },
    { MP_ROM_QSTR(MP_QSTR_seed), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_seed_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Bip39_locals_dict, mod_TrezorCrypto_Bip39_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Bip39_type = {
    { &mp_type_type },
    .name = MP_QSTR_Bip39,
    .make_new = mod_TrezorCrypto_Bip39_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Bip39_locals_dict,
};
