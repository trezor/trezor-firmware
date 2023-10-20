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
#ifndef TREZOR_EMULATOR
#include "supervise.h"
#endif

#include "image.h"
#include "version.h"

#if MICROPY_PY_TREZORUTILS

#include "embed/extmod/modtrezorutils/modtrezorutils-meminfo.h"
#include "embed/extmod/trezorobj.h"

#include <string.h>
#include "blake2s.h"
#include "common.h"
#include "flash.h"
#include "unit_variant.h"
#include "usb.h"
#include TREZOR_BOARD
#include "model.h"

#ifndef TREZOR_EMULATOR
#include "image.h"
#endif

#if USE_OPTIGA && !defined(TREZOR_EMULATOR)
#include "secret.h"
#endif

static void ui_progress(mp_obj_t ui_wait_callback, uint32_t current,
                        uint32_t total) {
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
    ensure(secfalse, msg.buf);
  } else {
    ensure(secfalse, "halt");
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
  BLAKE2S_CTX ctx;
  mp_buffer_info_t chal = {0};
  if (n_args > 0 && args[0] != mp_const_none) {
    mp_get_buffer_raise(args[0], &chal, MP_BUFFER_READ);
  }

  if (chal.len != 0) {
    if (blake2s_InitKey(&ctx, BLAKE2S_DIGEST_LENGTH, chal.buf, chal.len) != 0) {
      mp_raise_msg(&mp_type_ValueError, "Invalid challenge.");
    }
  } else {
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  }

  mp_obj_t ui_wait_callback = mp_const_none;
  if (n_args > 1 && args[1] != mp_const_none) {
    ui_wait_callback = args[1];
  }

  uint16_t firmware_sectors = flash_total_sectors(&FIRMWARE_AREA);

  ui_progress(ui_wait_callback, 0, firmware_sectors);
  for (int i = 0; i < firmware_sectors; i++) {
    uint8_t sector = flash_get_sector_num(&FIRMWARE_AREA, i);
    uint32_t size = flash_sector_size(sector);
    const void *data = flash_get_address(sector, 0, size);
    if (data == NULL) {
      mp_raise_msg(&mp_type_RuntimeError, "Failed to read firmware.");
    }
    blake2s_Update(&ctx, data, size);
    ui_progress(ui_wait_callback, i + 1, firmware_sectors);
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, BLAKE2S_DIGEST_LENGTH);
  if (blake2s_Final(&ctx, vstr.buf, vstr.len) != 0) {
    vstr_clear(&vstr);
    mp_raise_msg(&mp_type_RuntimeError, "Failed to finalize firmware hash.");
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
  vendor_header vhdr = {0};
  uint32_t size = flash_sector_size(FIRMWARE_AREA.subarea[0].first_sector);
  const void *data =
      flash_get_address(FIRMWARE_AREA.subarea[0].first_sector, 0, size);
  if (data == NULL || sectrue != read_vendor_header(data, &vhdr)) {
    mp_raise_msg(&mp_type_RuntimeError, "Failed to read vendor header.");
  }
  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)vhdr.vstr,
                             vhdr.vstr_len);
#endif
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_firmware_vendor_obj,
                                 mod_trezorutils_firmware_vendor);

/// def unit_color() -> int | None:
///     """
///     Returns the color of the unit.
///     """
STATIC mp_obj_t mod_trezorutils_unit_color(void) {
  if (!unit_variant_present()) {
    return mp_const_none;
  }
  return mp_obj_new_int(unit_variant_get_color());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_color_obj,
                                 mod_trezorutils_unit_color);

/// def unit_btconly() -> bool | None:
///     """
///     Returns True if the unit is BTConly.
///     """
STATIC mp_obj_t mod_trezorutils_unit_btconly(void) {
  if (!unit_variant_present()) {
    return mp_const_none;
  }
  return unit_variant_get_btconly() ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_btconly_obj,
                                 mod_trezorutils_unit_btconly);

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
  boot_command_t boot_command = BOOT_COMMAND_NONE;
  mp_buffer_info_t boot_args = {0};

  if (n_args > 0 && args[0] != mp_const_none) {
    mp_int_t value = mp_obj_get_int(args[0]);

    switch (value) {
      case 0:
        boot_command = BOOT_COMMAND_STOP_AND_WAIT;
        break;
      case 1:
        boot_command = BOOT_COMMAND_INSTALL_UPGRADE;
        break;
      default:
        mp_raise_ValueError("Invalid value.");
        break;
    }
  }

  if (n_args > 1 && args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &boot_args, MP_BUFFER_READ);
  }

  svc_reboot_to_bootloader(boot_command, boot_args.buf, boot_args.len);
#endif
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorutils_reboot_to_bootloader_obj, 0, 2,
    mod_trezorutils_reboot_to_bootloader);

/// def check_firmware_header(
///     header : bytes
/// ) -> dict:
///     """
///     Checks firmware image and vendor header and returns
///        { "version": (major, minor, patch),
///          "vendor": string,
///          "fingerprint": bytes,
///          "hash": bytes
///        }
///     """
STATIC mp_obj_t mod_trezorutils_check_firmware_header(mp_obj_t header) {
  mp_buffer_info_t header_buf = {0};
  mp_get_buffer_raise(header, &header_buf, MP_BUFFER_READ);

  firmware_header_info_t info;

  if (sectrue == check_firmware_header(header_buf.buf, header_buf.len, &info)) {
    mp_obj_t version[3] = {mp_obj_new_int(info.ver_major),
                           mp_obj_new_int(info.ver_minor),
                           mp_obj_new_int(info.ver_patch)};

    mp_obj_t result = mp_obj_new_dict(4);
    mp_obj_dict_store(result, MP_ROM_QSTR(MP_QSTR_version),
                      mp_obj_new_tuple(MP_ARRAY_SIZE(version), version));
    mp_obj_dict_store(
        result, MP_ROM_QSTR(MP_QSTR_vendor),
        mp_obj_new_str_copy(&mp_type_str, info.vstr, info.vstr_len));
    mp_obj_dict_store(
        result, MP_ROM_QSTR(MP_QSTR_fingerprint),
        mp_obj_new_bytes(info.fingerprint, sizeof(info.fingerprint)));
    mp_obj_dict_store(result, MP_ROM_QSTR(MP_QSTR_hash),
                      mp_obj_new_bytes(info.hash, sizeof(info.hash)));

    return result;
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

/// SCM_REVISION: bytes
/// """Git commit hash of the firmware."""
/// VERSION_MAJOR: int
/// """Major version."""
/// VERSION_MINOR: int
/// """Minor version."""
/// VERSION_PATCH: int
/// """Patch version."""
/// USE_SD_CARD: bool
/// """Whether the hardware supports SD card."""
/// USE_BACKLIGHT: bool
/// """Whether the hardware supports backlight brightness control."""
/// USE_OPTIGA: bool
/// """Whether the hardware supports Optiga secure element."""
/// MODEL: str
/// """Model name."""
/// MODEL_FULL_NAME: str
/// """Full name including Trezor prefix."""
/// INTERNAL_MODEL: str
/// """Internal model code."""
/// EMULATOR: bool
/// """Whether the firmware is running in the emulator."""
/// BITCOIN_ONLY: bool
/// """Whether the firmware is Bitcoin-only."""
/// UI_LAYOUT: str
/// """UI layout identifier ("tt" for model T, "tr" for models One and R)."""

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
    {MP_ROM_QSTR(MP_QSTR_unit_btconly),
     MP_ROM_PTR(&mod_trezorutils_unit_btconly_obj)},
    // various built-in constants
    {MP_ROM_QSTR(MP_QSTR_SCM_REVISION),
     MP_ROM_PTR(&mod_trezorutils_revision_obj)},
    {MP_ROM_QSTR(MP_QSTR_VERSION_MAJOR), MP_ROM_INT(VERSION_MAJOR)},
    {MP_ROM_QSTR(MP_QSTR_VERSION_MINOR), MP_ROM_INT(VERSION_MINOR)},
    {MP_ROM_QSTR(MP_QSTR_VERSION_PATCH), MP_ROM_INT(VERSION_PATCH)},
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
#ifdef USE_OPTIGA
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_false},
#endif
    {MP_ROM_QSTR(MP_QSTR_MODEL), MP_ROM_PTR(&mod_trezorutils_model_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_MODEL_FULL_NAME),
     MP_ROM_PTR(&mod_trezorutils_full_name_obj)},
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
#ifdef UI_LAYOUT_TT
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_TT)},
#elif UI_LAYOUT_TR
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_TR)},
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
