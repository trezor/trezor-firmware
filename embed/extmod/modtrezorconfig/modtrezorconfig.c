/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/runtime.h"
#include "py/mphal.h"

#if MICROPY_PY_TREZORCONFIG

#include <stdint.h>
#include <string.h>
#include "norcow.h"
#include "flash.h"

#define MAX_WRONG_PINS  15
#define FAIL_SECTOR_LEN 16 * 1024
#define STORAGE_KEY_PIN 0x00

static void pin_fails_reset(uint32_t ofs)
{
    if (ofs + sizeof(uint32_t) >= FAIL_SECTOR_LEN) {
        // ofs points to the last word of the PIN fails area.  Because there is
        // no space left, we recycle the sector (set all words to 0xffffffff).
        // On next unlock attempt, we start counting from the the first word.
        flash_erase_sectors(FLASH_SECTOR_PIN_AREA, FLASH_SECTOR_PIN_AREA, NULL);
    } else {
        // Mark this counter as exhausted.  On next unlock attempt, pinfails_get
        // seeks to the next word.
        flash_unlock();
        flash_write_word_rel(FLASH_SECTOR_PIN_AREA, ofs, 0);
        flash_lock();
    }
}

static bool pin_fails_increase(uint32_t ofs)
{
    uint32_t ctr = ~MAX_WRONG_PINS;
    if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, ofs, &ctr)) {
        return false;
    }
    ctr = ctr << 1;

    flash_unlock();
    if (!flash_write_word_rel(FLASH_SECTOR_PIN_AREA, ofs, ctr)) {
        flash_lock();
        return false;
    }
    flash_lock();

    uint32_t check = 0;
    if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, ofs, &check)) {
        return false;
    }
    return ctr == check;
}

static bool pin_fails_check_max(uint32_t ctr)
{
    if (~ctr >= 1 << MAX_WRONG_PINS) {
        norcow_wipe();
        // TODO: shutdown
        return false;
    }
    return true;
}

static bool pin_fails_get(uint32_t *ofs, uint32_t *ctr)
{
    if (!ofs || !ctr) {
        return false;
    }
    for (uint32_t o = 0; o < FAIL_SECTOR_LEN; o += sizeof(uint32_t)) {
        uint32_t c = 0;
        if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, o, &c)) {
            return false;
        }
        if (c != 0) {
            *ofs = o;
            *ctr = c;
            return true;
        }
    }
    return false;
}

static bool const_cmp(const uint8_t *pub, size_t publen, const uint8_t *sec, size_t seclen)
{
    size_t diff = seclen - publen;
    for (size_t i = 0; i < publen; i++) {
        diff |= pub[i] ^ sec[i];
    }
    return diff == 0;
}

static bool pin_check(const uint8_t *pin, size_t pinlen)
{
    const void *st_pin;
    uint16_t st_pinlen;
    if (!norcow_get(STORAGE_KEY_PIN, &st_pin, &st_pinlen)) {
        return false;
    }
    return const_cmp(pin, pinlen, st_pin, (size_t)st_pinlen);
}

static bool pin_unlock(const uint8_t *pin, size_t pinlen)
{
    uint32_t ofs;
    uint32_t ctr;
    if (!pin_fails_get(&ofs, &ctr)) {
        return false;
    }
    pin_fails_check_max(ctr);

    // Sleep for ~ctr seconds before checking the PIN.
    for (uint32_t wait = ~ctr; wait > 0; wait--) {
        mp_hal_delay_ms(1000);
    }

    // First, we increase PIN fail counter in storage, even before checking the
    // PIN.  If the PIN is correct, we reset the counter afterwards.  If not, we
    // check if this is the last allowed attempt.
    if (!pin_fails_increase(ofs)) {
        return false;
    }
    if (!pin_check(pin, pinlen)) {
        pin_fails_check_max(ctr << 1);
        return false;
    }
    pin_fails_reset(ofs);
    return true;
}

static bool initialized = false;
static bool unlocked = false;

/// def init() -> None:
///     '''
///     Initializes the storage. Must be called before any other method is called from this module!
///     '''
STATIC mp_obj_t mod_trezorconfig_init(void) {
    bool r = norcow_init();
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not initialize config module");
    }
    initialized = true;
    unlocked = false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_init_obj, mod_trezorconfig_init);

/// def unlock(pin: str) -> None:
///     '''
///     Tries to unlock the storage with given PIN key.
///     '''
STATIC mp_obj_t mod_trezorconfig_unlock(mp_obj_t pin) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    mp_buffer_info_t pinbuf;
    mp_get_buffer_raise(pin, &pinbuf, MP_BUFFER_READ);
    bool r = pin_unlock(pinbuf.buf, pinbuf.len);
    if (!r) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorconfig_unlock_obj, mod_trezorconfig_unlock);

/// def get(app: int, key: int) -> bytes:
///     '''
///     Gets a value of given key for given app (or empty bytes if not set).
///     '''
STATIC mp_obj_t mod_trezorconfig_get(mp_obj_t app, mp_obj_t key) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    if (!unlocked) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module locked");
        // TODO: shutdown?
    }
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k, len;
    const void *val;
    bool r = norcow_get(appkey, &val, &len);
    if (!r || len == 0) {
        return mp_const_empty_bytes;
    }
    vstr_t vstr;
    vstr_init_len(&vstr, len);
    memcpy(vstr.buf, val, len);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_get_obj, mod_trezorconfig_get);

/// def set(app: int, key: int, value: bytes) -> None:
///     '''
///     Sets a value of given key for given app.
///     '''
STATIC mp_obj_t mod_trezorconfig_set(mp_obj_t app, mp_obj_t key, mp_obj_t value) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    if (!unlocked) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module locked");
        // TODO: shutdown?
    }
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k;
    mp_buffer_info_t v;
    mp_get_buffer_raise(value, &v, MP_BUFFER_READ);
    bool r = norcow_set(appkey, v.buf, v.len);
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorconfig_set_obj, mod_trezorconfig_set);

/// def wipe() -> None:
///     '''
///     Erases the whole config. Use with caution!
///     '''
STATIC mp_obj_t mod_trezorconfig_wipe(void) {
    if (!initialized) {
        mp_raise_msg(&mp_type_RuntimeError, "Config module not initialized");
    }
    bool r = norcow_wipe();
    if (!r) {
       mp_raise_msg(&mp_type_RuntimeError, "Could not wipe storage");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_wipe_obj, mod_trezorconfig_wipe);

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezorconfig_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_unlock), MP_ROM_PTR(&mod_trezorconfig_unlock_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezorconfig_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorconfig_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_wipe), MP_ROM_PTR(&mod_trezorconfig_wipe_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals, mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezorconfig_globals,
};

#endif // MICROPY_PY_TREZORCONFIG
