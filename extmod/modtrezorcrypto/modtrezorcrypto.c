/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"

#if MICROPY_PY_TREZORCRYPTO

#include "modtrezorcrypto-aes.h"
#include "modtrezorcrypto-bip32.h"
#include "modtrezorcrypto-bip39.h"
#include "modtrezorcrypto-blake2s.h"
#include "modtrezorcrypto-curve25519.h"
#include "modtrezorcrypto-ed25519.h"
#include "modtrezorcrypto-pbkdf2.h"
#include "modtrezorcrypto-random.h"
#include "modtrezorcrypto-ripemd160.h"
#include "modtrezorcrypto-nist256p1.h"
#include "modtrezorcrypto-secp256k1.h"
#include "modtrezorcrypto-sha256.h"
#include "modtrezorcrypto-sha512.h"
#include "modtrezorcrypto-sha3-256.h"
#include "modtrezorcrypto-sha3-512.h"
#include "modtrezorcrypto-ssss.h"

STATIC const mp_rom_map_elem_t mp_module_TrezorCrypto_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorCrypto) },
    { MP_ROM_QSTR(MP_QSTR_AES), MP_ROM_PTR(&mod_TrezorCrypto_AES_type) },
    { MP_ROM_QSTR(MP_QSTR_Bip32), MP_ROM_PTR(&mod_TrezorCrypto_Bip32_type) },
    { MP_ROM_QSTR(MP_QSTR_Bip39), MP_ROM_PTR(&mod_TrezorCrypto_Bip39_type) },
    { MP_ROM_QSTR(MP_QSTR_Blake2s), MP_ROM_PTR(&mod_TrezorCrypto_Blake2s_type) },
    { MP_ROM_QSTR(MP_QSTR_Curve25519), MP_ROM_PTR(&mod_TrezorCrypto_Curve25519_type) },
    { MP_ROM_QSTR(MP_QSTR_Ed25519), MP_ROM_PTR(&mod_TrezorCrypto_Ed25519_type) },
    { MP_ROM_QSTR(MP_QSTR_Nist256p1), MP_ROM_PTR(&mod_TrezorCrypto_Nist256p1_type) },
    { MP_ROM_QSTR(MP_QSTR_Pbkdf2), MP_ROM_PTR(&mod_TrezorCrypto_Pbkdf2_type) },
    { MP_ROM_QSTR(MP_QSTR_Random), MP_ROM_PTR(&mod_TrezorCrypto_Random_type) },
    { MP_ROM_QSTR(MP_QSTR_Ripemd160), MP_ROM_PTR(&mod_TrezorCrypto_Ripemd160_type) },
    { MP_ROM_QSTR(MP_QSTR_Secp256k1), MP_ROM_PTR(&mod_TrezorCrypto_Secp256k1_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha256), MP_ROM_PTR(&mod_TrezorCrypto_Sha256_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha512), MP_ROM_PTR(&mod_TrezorCrypto_Sha512_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha3_256), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_256_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha3_512), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_512_type) },
    { MP_ROM_QSTR(MP_QSTR_SSSS), MP_ROM_PTR(&mod_TrezorCrypto_SSSS_type) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorCrypto_globals, mp_module_TrezorCrypto_globals_table);

const mp_obj_module_t mp_module_TrezorCrypto = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorCrypto_globals,
};

#endif // MICROPY_PY_TREZORCRYPTO
