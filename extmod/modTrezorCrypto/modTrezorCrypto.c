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

#include "modTrezorCrypto-base58.h"
#include "modTrezorCrypto-ripemd160.h"
#include "modTrezorCrypto-sha256.h"
#include "modTrezorCrypto-sha512.h"

// module stuff

STATIC const mp_rom_map_elem_t mp_module_TrezorCrypto_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorCrypto) },
    { MP_ROM_QSTR(MP_QSTR_Base58), MP_ROM_PTR(&mod_TrezorCrypto_Base58_type) },
    { MP_ROM_QSTR(MP_QSTR_Ripemd160), MP_ROM_PTR(&mod_TrezorCrypto_Ripemd160_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha256), MP_ROM_PTR(&mod_TrezorCrypto_Sha256_type) },
    { MP_ROM_QSTR(MP_QSTR_Sha512), MP_ROM_PTR(&mod_TrezorCrypto_Sha512_type) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorCrypto_globals, mp_module_TrezorCrypto_globals_table);

const mp_obj_module_t mp_module_TrezorCrypto = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorCrypto,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorCrypto_globals,
};

#endif // MICROPY_PY_TREZORCRYPTO
