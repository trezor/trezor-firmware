/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
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
#include "py/objstr.h"

#if MICROPY_PY_TREZORUTILS

/// def trezor.utils.memcpy(dst: bytearray, dst_ofs: int,
///                         src: bytearray, src_ofs: int,
//                          n: int) -> int:
///     '''
///     Copies at most `n` bytes from `src` at offset `src_ofs` to
///     `dst` at offset `dst_ofs`.  Returns the number of actually
///     copied bytes.
///     '''
STATIC mp_obj_t mod_TrezorUtils_memcpy(size_t n_args, const mp_obj_t *args) {
    mp_arg_check_num(n_args, 0, 5, 5, false);

    mp_buffer_info_t dst;
    mp_get_buffer_raise(args[0], &dst, MP_BUFFER_WRITE);
    int dst_ofs = mp_obj_get_int(args[1]);
    if (dst_ofs < 0) {
        mp_raise_ValueError("Invalid dst offset (has to be >= 0)");
    }

    mp_buffer_info_t src;
    mp_get_buffer_raise(args[2], &src, MP_BUFFER_READ);
    int src_ofs = mp_obj_get_int(args[3]);
    if (src_ofs < 0) {
        mp_raise_ValueError("Invalid src offset (has to be >= 0)");
    }

    int n = mp_obj_get_int(args[4]);
    if (n < 0) {
        mp_raise_ValueError("Invalid byte count (has to be >= 0)");
    }
    size_t dst_rem = (dst_ofs < dst.len) ? dst.len - dst_ofs : 0;
    size_t src_rem = (src_ofs < src.len) ? src.len - src_ofs : 0;
    size_t ncpy = MIN(n, MIN(src_rem, dst_rem));

    memmove(((char*)dst.buf) + dst_ofs, ((const char*)src.buf) + src_ofs, ncpy);

    return mp_obj_new_int(ncpy);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUtils_memcpy_obj, 5, 5, mod_TrezorUtils_memcpy);

STATIC const mp_rom_map_elem_t mp_module_TrezorUtils_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorUtils) },
    { MP_ROM_QSTR(MP_QSTR_memcpy), MP_ROM_PTR(&mod_TrezorUtils_memcpy_obj) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorUtils_globals, mp_module_TrezorUtils_globals_table);

const mp_obj_module_t mp_module_TrezorUtils = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorUtils_globals,
};

#endif // MICROPY_PY_TREZORUTILS
