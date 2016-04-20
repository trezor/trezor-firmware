/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"

#if MICROPY_PY_TREZORCRYPTO

#include "modtrezorcrypto-pbkdf2_hmac.h"
#include "modtrezorcrypto-ripemd160.h"
#include "modtrezorcrypto-sha256.h"
#include "modtrezorcrypto-sha512.h"
#include "modtrezorcrypto-sha3-256.h"
#include "modtrezorcrypto-sha3-512.h"

// module stuff

STATIC const mp_rom_map_elem_t mp_module_TrezorCrypto_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorCrypto) },
    { MP_ROM_QSTR(MP_QSTR_Ripemd160), MP_ROM_PTR(&mod_TrezorCrypto_Ripemd160_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha256), MP_ROM_PTR(&mod_TrezorCrypto_Sha256_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha512), MP_ROM_PTR(&mod_TrezorCrypto_Sha512_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha3_256), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_256_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha3_512), MP_ROM_PTR(&mod_TrezorCrypto_Sha3_512_type) },
    { MP_ROM_QSTR(MP_QSTR_pbkdf2_hmac), MP_ROM_PTR(&mod_TrezorCrypto_pbkdf2_hmac_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorCrypto_globals, mp_module_TrezorCrypto_globals_table);

const mp_obj_module_t mp_module_TrezorCrypto = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorCrypto,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorCrypto_globals,
};

#endif // MICROPY_PY_TREZORCRYPTO
