/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
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

/// def trezor.crypto.bip39.generate(strength: int) -> tuple
///
/// Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits)
///
STATIC mp_obj_t mod_TrezorCrypto_Bip39_generate(mp_obj_t self, mp_obj_t strength) {
    int bits = mp_obj_get_int(strength);
    if (bits % 32 || bits < 128 || bits > 256) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid bit strength (only 128, 160, 192, 224 and 256 values are allowed)"));
    }
    int words = bits / 32 * 3;
    const char * const *wordlist = mnemonic_wordlist();
    const uint16_t *mnemo = mnemonic_generate_indexes(bits);
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(words, NULL));
    for (int i = 0; i < words; i++) {
        vstr_t vstr;
        vstr_init_len(&vstr, strlen(wordlist[mnemo[i]]));
        strcpy(vstr.buf, wordlist[mnemo[i]]);
        tuple->items[i] = mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
    }
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_generate_obj, mod_TrezorCrypto_Bip39_generate);

/// def trezor.crypto.bip39.from_data(data: bytes) -> tuple
///
/// Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes)
///
STATIC mp_obj_t mod_TrezorCrypto_Bip39_from_data(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t bin;
    mp_get_buffer_raise(data, &bin, MP_BUFFER_READ);
    if (bin.len % 4 || bin.len < 16 || bin.len > 32) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid data length (only 16, 20, 24, 28 and 32 bytes are allowed)"));
    }
    int words = bin.len / 4 * 3;
    const char * const *wordlist = mnemonic_wordlist();
    const uint16_t *mnemo = mnemonic_from_data_indexes(bin.buf, bin.len);
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(words, NULL));
    for (int i = 0; i < words; i++) {
        vstr_t vstr;
        vstr_init_len(&vstr, strlen(wordlist[mnemo[i]]));
        strcpy(vstr.buf, wordlist[mnemo[i]]);
        tuple->items[i] = mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
    }
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_from_data_obj, mod_TrezorCrypto_Bip39_from_data);

/// def trezor.crypto.bip39.check(mnemonic: str) -> bool
///
/// Check whether given mnemonic is valid
///
STATIC mp_obj_t mod_TrezorCrypto_Bip39_check(mp_obj_t self, mp_obj_t mnemonic) {
    mp_buffer_info_t text;
    mp_get_buffer_raise(mnemonic, &text, MP_BUFFER_READ);
    return mnemonic_check(text.buf) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Bip39_check_obj, mod_TrezorCrypto_Bip39_check);

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Bip39_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_generate), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_generate_obj) },
    { MP_ROM_QSTR(MP_QSTR_from_data), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_from_data_obj) },
    { MP_ROM_QSTR(MP_QSTR_check), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_check_obj) },
//    { MP_ROM_QSTR(MP_QSTR_seed), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_seed_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Bip39_locals_dict, mod_TrezorCrypto_Bip39_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Bip39_type = {
    { &mp_type_type },
    .name = MP_QSTR_Bip39,
    .make_new = mod_TrezorCrypto_Bip39_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Bip39_locals_dict,
};
