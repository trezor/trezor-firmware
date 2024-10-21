/*
 * This file is part of the Trezor project, https://trezor.io/
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
#include "py/runtime.h"

#include "image.h"
#include "version.h"

#if MICROPY_PY_TREZORUTILS

#include "embed/extmod/modtrezorutils/modtrezorutils-meminfo.h"
#include "embed/extmod/trezorobj.h"

#include <string.h>
#include "blake2s.h"
#include "bootutils.h"
#include "error_handling.h"
#include "fwutils.h"
#include "unit_properties.h"
#include "usb.h"
#include TREZOR_BOARD
#include "model.h"

#if USE_OPTIGA && !defined(TREZOR_EMULATOR)
#include "secret.h"
#endif

static void ui_progress(void *context, uint32_t current, uint32_t total) {
  mp_obj_t ui_wait_callback = (mp_obj_t)context;

  if (mp_obj_is_callable(ui_wait_callback)) {
    mp_call_function_2_protected(ui_wait_callback, mp_obj_new_int(current),
                                 mp_obj_new_int(total));
  }
}

/// def consteq(sec: bytes, pub: bytes) -> bool:
///     """
///     Compares the private information in `sec` with public, user-provided
///     information in `pub`.  Runs in constant time, corresponding to a length
///     of `pub`.  Can access memory behind valid length of `sec`, caller is
///     expected to avoid any invalid memory access.
///     """
STATIC mp_obj_t mod_trezorutils_consteq(mp_obj_t sec, mp_obj_t pub) {
  mp_buffer_info_t secbuf = {0};
  mp_get_buffer_raise(sec, &secbuf, MP_BUFFER_READ);
  mp_buffer_info_t pubbuf = {0};
  mp_get_buffer_raise(pub, &pubbuf, MP_BUFFER_READ);

  size_t diff = secbuf.len - pubbuf.len;
  for (size_t i = 0; i < pubbuf.len; i++) {
    const uint8_t *s = (uint8_t *)secbuf.buf;
    const uint8_t *p = (uint8_t *)pubbuf.buf;
    diff |= s[i] - p[i];
  }

  if (diff == 0) {
    return mp_const_true;
  } else {
    return mp_const_false;
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorutils_consteq_obj,
                                 mod_trezorutils_consteq);

/// def memcpy(
///     dst: bytearray | memoryview,
///     dst_ofs: int,
///     src: bytes,
///     src_ofs: int,
///     n: int | None = None,
/// ) -> int:
///     """
///     Copies at most `n` bytes from `src` at offset `src_ofs` to
///     `dst` at offset `dst_ofs`. Returns the number of actually
///     copied bytes. If `n` is not specified, tries to copy
///     as much as possible.
///     """
STATIC mp_obj_t mod_trezorutils_memcpy(size_t n_args, const mp_obj_t *args) {
  mp_arg_check_num(n_args, 0, 4, 5, false);

  mp_buffer_info_t dst = {0};
  mp_get_buffer_raise(args[0], &dst, MP_BUFFER_WRITE);
  uint32_t dst_ofs = trezor_obj_get_uint(args[1]);

  mp_buffer_info_t src = {0};
  mp_get_buffer_raise(args[2], &src, MP_BUFFER_READ);
  uint32_t src_ofs = trezor_obj_get_uint(args[3]);

  uint32_t n = 0;
  if (n_args > 4) {
    n = trezor_obj_get_uint(args[4]);
  } else {
    n = src.len;
  }

  size_t dst_rem = (dst_ofs < dst.len) ? dst.len - dst_ofs : 0;
  size_t src_rem = (src_ofs < src.len) ? src.len - src_ofs : 0;
  size_t ncpy = MIN(n, MIN(src_rem, dst_rem));

  memmove(((char *)dst.buf) + dst_ofs, ((const char *)src.buf) + src_ofs, ncpy);

  return mp_obj_new_int(ncpy);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorutils_memcpy_obj, 4, 5,
                                           mod_trezorutils_memcpy);

/// def halt(msg: str | None = None) -> None:
///     """
///     Halts execution.
///     """
STATIC mp_obj_t mod_trezorutils_halt(size_t n_args, const mp_obj_t *args) {
  mp_buffer_info_t msg = {0};
  if (n_args > 0 && mp_get_buffer(args[0], &msg, MP_BUFFER_READ)) {
    error_shutdown(msg.buf);
  } else {
    error_shutdown("halt");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorutils_halt_obj, 0, 1,
                                           mod_trezorutils_halt);

/// def firmware_hash(
///     challenge: bytes | None = None,
///     callback: Callable[[int, int], None] | None = None,
/// ) -> bytes:
///     """
///     Computes the Blake2s hash of the firmware with an optional challenge as
///     the key.
///     """
STATIC mp_obj_t mod_trezorutils_firmware_hash(size_t n_args,
                                              const mp_obj_t *args) {
  mp_buffer_info_t chal = {0};
  if (n_args > 0 && args[0] != mp_const_none) {
    mp_get_buffer_raise(args[0], &chal, MP_BUFFER_READ);
  }

  mp_obj_t ui_wait_callback = mp_const_none;
  if (n_args > 1 && args[1] != mp_const_none) {
    ui_wait_callback = args[1];
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, BLAKE2S_DIGEST_LENGTH);

  if (sectrue != firmware_calc_hash(chal.buf, chal.len, (uint8_t *)vstr.buf,
                                    vstr.len, ui_progress, ui_wait_callback)) {
    vstr_clear(&vstr);
    mp_raise_msg(&mp_type_RuntimeError, "Failed to calculate firmware hash.");
  }

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorutils_firmware_hash_obj, 0,
                                           2, mod_trezorutils_firmware_hash);

/// def firmware_vendor() -> str:
///     """
///     Returns the firmware vendor string from the vendor header.
///     """
STATIC mp_obj_t mod_trezorutils_firmware_vendor(void) {
#ifdef TREZOR_EMULATOR
  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)"EMULATOR", 8);
#else
  char vendor[64] = {0};
  if (sectrue != firmware_get_vendor(vendor, sizeof(vendor))) {
    mp_raise_msg(&mp_type_RuntimeError, "Failed to read vendor header.");
  }
  return mp_obj_new_str_copy(&mp_type_str, (byte *)vendor, strlen(vendor));
#endif
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_firmware_vendor_obj,
                                 mod_trezorutils_firmware_vendor);

/// def unit_color() -> int | None:
///     """
///     Returns the color of the unit.
///     """
STATIC mp_obj_t mod_trezorutils_unit_color(void) {
  if (!unit_properties()->color_is_valid) {
    return mp_const_none;
  }
  return mp_obj_new_int(unit_properties()->color);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_color_obj,
                                 mod_trezorutils_unit_color);

/// def unit_btconly() -> bool | None:
///     """
///     Returns True if the unit is BTConly.
///     """
STATIC mp_obj_t mod_trezorutils_unit_btconly(void) {
  if (!unit_properties()->btconly_is_valid) {
    return mp_const_none;
  }
  return unit_properties()->btconly ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_btconly_obj,
                                 mod_trezorutils_unit_btconly);

/// def unit_packaging() -> int | None:
///     """
///     Returns the packaging version of the unit.
///     """
STATIC mp_obj_t mod_trezorutils_unit_packaging(void) {
  if (!unit_properties()->packaging_is_valid) {
    return mp_const_none;
  }
  return mp_obj_new_int(unit_properties()->packaging);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_packaging_obj,
                                 mod_trezorutils_unit_packaging);

/// def sd_hotswap_enabled() -> bool:
///     """
///     Returns True if SD card hot swapping is enabled
///     """
STATIC mp_obj_t mod_trezorutils_sd_hotswap_enabled(void) {
  return unit_properties()->sd_hotswap_enabled ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_sd_hotswap_enabled_obj,
                                 mod_trezorutils_sd_hotswap_enabled);

/// def reboot_to_bootloader(
///     boot_command : int = 0,
///     boot_args : bytes | None = None,
/// ) -> None:
///     """
///     Reboots to bootloader.
///     """
STATIC mp_obj_t mod_trezorutils_reboot_to_bootloader(size_t n_args,
                                                     const mp_obj_t *args) {
#ifndef TREZOR_EMULATOR
  if (n_args > 0 && args[0] != mp_const_none) {
    mp_int_t value = mp_obj_get_int(args[0]);

    switch (value) {
      case 0:
        // Reboot and stay in bootloader
        reboot_to_bootloader();
        break;
      case 1:
        // Reboot and continue with the firmware upgrade
        mp_buffer_info_t hash = {0};

        if (n_args > 1 && args[1] != mp_const_none) {
          mp_get_buffer_raise(args[1], &hash, MP_BUFFER_READ);
        }

        if (hash.len != 32) {
          mp_raise_ValueError("Invalid value.");
        }

        reboot_and_upgrade((uint8_t *)hash.buf);
        break;
      default:
        mp_raise_ValueError("Invalid value.");
        break;
    }
  } else {
    // Just reboot and go through the normal boot sequence
    reboot_device();
  }

#endif
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorutils_reboot_to_bootloader_obj, 0, 2,
    mod_trezorutils_reboot_to_bootloader);

/// VersionTuple = Tuple[int, int, int, int]

/// class FirmwareHeaderInfo(NamedTuple):
///     version: VersionTuple
///     vendor: str
///     fingerprint: bytes
///     hash: bytes

/// mock:global

/// def check_firmware_header(header : bytes) -> FirmwareHeaderInfo:
///     """Parses incoming firmware header and returns information about it."""
STATIC mp_obj_t mod_trezorutils_check_firmware_header(mp_obj_t header) {
  mp_buffer_info_t header_buf = {0};
  mp_get_buffer_raise(header, &header_buf, MP_BUFFER_READ);

  firmware_header_info_t info;

  if (sectrue == check_firmware_header(header_buf.buf, header_buf.len, &info)) {
    mp_obj_t version[4] = {
        mp_obj_new_int(info.ver_major), mp_obj_new_int(info.ver_minor),
        mp_obj_new_int(info.ver_patch), mp_obj_new_int(info.ver_build)};

    static const qstr fields[4] = {MP_QSTR_version, MP_QSTR_vendor,
                                   MP_QSTR_fingerprint, MP_QSTR_hash};
    const mp_obj_t values[4] = {
        mp_obj_new_tuple(MP_ARRAY_SIZE(version), version),
        mp_obj_new_str_copy(&mp_type_str, info.vstr, info.vstr_len),
        mp_obj_new_bytes(info.fingerprint, sizeof(info.fingerprint)),
        mp_obj_new_bytes(info.hash, sizeof(info.hash))};
    return mp_obj_new_attrtuple(fields, MP_ARRAY_SIZE(fields), values);
  }

  mp_raise_ValueError("Invalid value.");
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_check_firmware_header_obj,
                                 mod_trezorutils_check_firmware_header);

/// def bootloader_locked() -> bool | None:
///     """
///     Returns True/False if the the bootloader is locked/unlocked and None if
///     the feature is not supported.
///     """
STATIC mp_obj_t mod_trezorutils_bootloader_locked() {
#if USE_OPTIGA
#ifdef TREZOR_EMULATOR
  return mp_const_true;
#else
  return (secret_bootloader_locked() == sectrue) ? mp_const_true
                                                 : mp_const_false;
#endif
#else
  return mp_const_none;
#endif
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_bootloader_locked_obj,
                                 mod_trezorutils_bootloader_locked);

STATIC mp_obj_str_t mod_trezorutils_revision_obj = {
    {&mp_type_bytes}, 0, sizeof(SCM_REVISION) - 1, (const byte *)SCM_REVISION};

STATIC mp_obj_str_t mod_trezorutils_model_name_obj = {
    {&mp_type_str}, 0, sizeof(MODEL_NAME) - 1, (const byte *)MODEL_NAME};

STATIC mp_obj_str_t mod_trezorutils_full_name_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_FULL_NAME) - 1,
    (const byte *)MODEL_FULL_NAME};

STATIC mp_obj_str_t mod_trezorutils_model_usb_manufacturer_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_USB_MANUFACTURER) - 1,
    (const byte *)MODEL_USB_MANUFACTURER};

STATIC mp_obj_str_t mod_trezorutils_model_usb_product_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_USB_PRODUCT) - 1,
    (const byte *)MODEL_USB_PRODUCT};

STATIC mp_obj_tuple_t mod_trezorutils_version_obj = {
    {&mp_type_tuple},
    4,
    {MP_OBJ_NEW_SMALL_INT(VERSION_MAJOR), MP_OBJ_NEW_SMALL_INT(VERSION_MINOR),
     MP_OBJ_NEW_SMALL_INT(VERSION_PATCH), MP_OBJ_NEW_SMALL_INT(VERSION_BUILD)}};

/// SCM_REVISION: bytes
/// """Git commit hash of the firmware."""
/// VERSION: VersionTuple
/// """Firmware version as a tuple (major, minor, patch, build)."""
/// USE_SD_CARD: bool
/// """Whether the hardware supports SD card."""
/// USE_BACKLIGHT: bool
/// """Whether the hardware supports backlight brightness control."""
/// USE_HAPTIC: bool
/// """Whether the hardware supports haptic feedback."""
/// USE_OPTIGA: bool
/// """Whether the hardware supports Optiga secure element."""
/// MODEL: str
/// """Model name."""
/// MODEL_FULL_NAME: str
/// """Full name including Trezor prefix."""
/// MODEL_USB_MANUFACTURER: str
/// """USB Manufacturer name."""
/// MODEL_USB_PRODUCT: str
/// """USB Product name."""
/// INTERNAL_MODEL: str
/// """Internal model code."""
/// EMULATOR: bool
/// """Whether the firmware is running in the emulator."""
/// BITCOIN_ONLY: bool
/// """Whether the firmware is Bitcoin-only."""
/// UI_LAYOUT: str
/// """UI layout identifier ("tt" for model T, "tr" for models One and R)."""
/// USE_THP: bool
/// """Whether the firmware supports Trezor-Host Protocol (version 3)."""

STATIC const mp_rom_map_elem_t mp_module_trezorutils_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorutils)},
    {MP_ROM_QSTR(MP_QSTR_consteq), MP_ROM_PTR(&mod_trezorutils_consteq_obj)},
    {MP_ROM_QSTR(MP_QSTR_memcpy), MP_ROM_PTR(&mod_trezorutils_memcpy_obj)},
    {MP_ROM_QSTR(MP_QSTR_halt), MP_ROM_PTR(&mod_trezorutils_halt_obj)},
    {MP_ROM_QSTR(MP_QSTR_firmware_hash),
     MP_ROM_PTR(&mod_trezorutils_firmware_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_firmware_vendor),
     MP_ROM_PTR(&mod_trezorutils_firmware_vendor_obj)},
    {MP_ROM_QSTR(MP_QSTR_reboot_to_bootloader),
     MP_ROM_PTR(&mod_trezorutils_reboot_to_bootloader_obj)},
    {MP_ROM_QSTR(MP_QSTR_check_firmware_header),
     MP_ROM_PTR(&mod_trezorutils_check_firmware_header_obj)},
    {MP_ROM_QSTR(MP_QSTR_bootloader_locked),
     MP_ROM_PTR(&mod_trezorutils_bootloader_locked_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_color),
     MP_ROM_PTR(&mod_trezorutils_unit_color_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_packaging),
     MP_ROM_PTR(&mod_trezorutils_unit_packaging_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_btconly),
     MP_ROM_PTR(&mod_trezorutils_unit_btconly_obj)},
    {MP_ROM_QSTR(MP_QSTR_sd_hotswap_enabled),
     MP_ROM_PTR(&mod_trezorutils_sd_hotswap_enabled_obj)},
    // various built-in constants
    {MP_ROM_QSTR(MP_QSTR_SCM_REVISION),
     MP_ROM_PTR(&mod_trezorutils_revision_obj)},
    {MP_ROM_QSTR(MP_QSTR_VERSION), MP_ROM_PTR(&mod_trezorutils_version_obj)},
#ifdef USE_SD_CARD
    {MP_ROM_QSTR(MP_QSTR_USE_SD_CARD), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_SD_CARD), mp_const_false},
#endif
#ifdef USE_BACKLIGHT
    {MP_ROM_QSTR(MP_QSTR_USE_BACKLIGHT), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_BACKLIGHT), mp_const_false},
#endif
#ifdef USE_HAPTIC
    {MP_ROM_QSTR(MP_QSTR_USE_HAPTIC), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_HAPTIC), mp_const_false},
#endif
#ifdef USE_OPTIGA
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_false},
#endif
    {MP_ROM_QSTR(MP_QSTR_MODEL), MP_ROM_PTR(&mod_trezorutils_model_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_MODEL_FULL_NAME),
     MP_ROM_PTR(&mod_trezorutils_full_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_MODEL_USB_MANUFACTURER),
     MP_ROM_PTR(&mod_trezorutils_model_usb_manufacturer_obj)},
    {MP_ROM_QSTR(MP_QSTR_MODEL_USB_PRODUCT),
     MP_ROM_PTR(&mod_trezorutils_model_usb_product_obj)},
    {MP_ROM_QSTR(MP_QSTR_INTERNAL_MODEL),
     MP_ROM_QSTR(MODEL_INTERNAL_NAME_QSTR)},
#ifdef TREZOR_EMULATOR
    {MP_ROM_QSTR(MP_QSTR_EMULATOR), mp_const_true},
    MEMINFO_DICT_ENTRIES
#else
    {MP_ROM_QSTR(MP_QSTR_EMULATOR), mp_const_false},
#endif
#if BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_BITCOIN_ONLY), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_BITCOIN_ONLY), mp_const_false},
#endif
#ifdef USE_THP
    {MP_ROM_QSTR(MP_QSTR_USE_THP), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_THP), mp_const_false},
#endif
#ifdef UI_LAYOUT_TT
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_TT)},
#elif UI_LAYOUT_TR
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_TR)},
#elif UI_LAYOUT_MERCURY
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_MERCURY)},
#else
#error Unknown layout
#endif
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorutils_globals,
                            mp_module_trezorutils_globals_table);

const mp_obj_module_t mp_module_trezorutils = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorutils_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorutils, mp_module_trezorutils);

#endif  // MICROPY_PY_TREZORUTILS
