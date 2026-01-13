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

#include <trezor_model.h>
#include <trezor_rtl.h>

#if MICROPY_OOM_CALLBACK
#include <py/gc.h>
#endif
#include "py/objstr.h"
#include "py/runtime.h"

#include <util/image.h>
#include "version.h"

#if MICROPY_PY_TREZORUTILS

#include "embed/upymod/modtrezorutils/modtrezorutils-meminfo.h"
#include "embed/upymod/trezorobj.h"

#include <io/usb.h>
#include <sys/logging.h>

#include <io/notify.h>
#include <sec/secret_keys.h>
#include <sec/unit_properties.h>
#include <sys/bootutils.h>
#include <util/fwutils.h>
#include <util/scm_revision.h>
#include "blake2s.h"
#include "memzero.h"

#ifdef USE_BLE
#include <io/ble.h>
#endif
#ifdef USE_NRF
#include <io/nrf.h>
#endif

#if !defined(TREZOR_EMULATOR)
#include <sec/secret.h>
#endif

#if !PYOPT && LOG_STACK_USAGE
#include <sys/stack_utils.h>
#endif

/// from trezor import utils

/// def consteq(sec: AnyBytes, pub: AnyBytes) -> bool:
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
///     dst: AnyBuffer,
///     dst_ofs: int,
///     src: AnyBytes,
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

/// def memzero(
///     dst: AnyBuffer,
/// ) -> None:
///     """
///     Zeroes all bytes at `dst`.
///     """
STATIC mp_obj_t mod_trezorutils_memzero(const mp_obj_t dst) {
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(dst, &buf, MP_BUFFER_WRITE);
  memzero(buf.buf, buf.len);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_memzero_obj,
                                 mod_trezorutils_memzero);

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
///     challenge: AnyBytes | None = None,
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

  if (firmware_hash_start(chal.buf, chal.len) < 0) {
    vstr_clear(&vstr);
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to start firmware hash."));
  }

  int progress = 0;

  while (progress < 100) {
    progress = firmware_hash_continue((uint8_t *)vstr.buf, vstr.len);

    if (progress < 0) {
      vstr_clear(&vstr);
      mp_raise_msg(&mp_type_RuntimeError,
                   MP_ERROR_TEXT("Failed to calculate firmware hash."));
      break;
    }

    if (mp_obj_is_callable(ui_wait_callback)) {
      mp_call_function_2_protected(ui_wait_callback, mp_obj_new_int(progress),
                                   mp_obj_new_int(100));
    }
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
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to read vendor header."));
  }
  return mp_obj_new_str_copy(&mp_type_str, (byte *)vendor, strlen(vendor));
#endif
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_firmware_vendor_obj,
                                 mod_trezorutils_firmware_vendor);

/// def delegated_identity() -> bytes:
///     """
///     Returns the delegated identity key used for registration and space
///     management at Evolu.
///     """
STATIC mp_obj_t mod_trezorutils_delegated_identity(void) {
  uint8_t private_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  if (secret_key_delegated_identity(private_key) != sectrue) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to read delegated identity."));
  }
  return mp_obj_new_bytes(private_key, sizeof(private_key));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_delegated_identity_obj,
                                 mod_trezorutils_delegated_identity);

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

/// def unit_production_date() -> tuple[int, int, int] | None:
///     """
///     Returns the unit production date as (year, month, day), or None if
///     unavailable.
///     """
STATIC mp_obj_t mod_trezorutils_unit_production_date(void) {
  const unit_properties_t *props = unit_properties();
  if (props == NULL) {
    return mp_const_none;
  }

  const uint16_t year = props->production_date.year;
  const uint8_t month = props->production_date.month;
  const uint8_t day = props->production_date.day;

  // If any field is zero, consider the date unavailable
  if (year == 0 || month == 0 || day == 0) {
    return mp_const_none;
  }

  mp_obj_t items[3];
  items[0] = mp_obj_new_int(year);
  items[1] = mp_obj_new_int(month);
  items[2] = mp_obj_new_int(day);
  return mp_obj_new_tuple(3, items);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_unit_production_date_obj,
                                 mod_trezorutils_unit_production_date);

#if USE_SERIAL_NUMBER

/// if utils.USE_SERIAL_NUMBER:
///     def serial_number() -> str:
///         """
///         Returns unit serial number.
///         """
STATIC mp_obj_t mod_trezorutils_serial_number(void) {
  uint8_t device_sn[MAX_DEVICE_SN_SIZE] = {0};
  size_t device_sn_size = 0;
  if (!unit_properties_get_sn(device_sn, MAX_DEVICE_SN_SIZE, &device_sn_size)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to read serial number."));
  }
  return mp_obj_new_str_copy(&mp_type_str, device_sn, device_sn_size);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_serial_number_obj,
                                 mod_trezorutils_serial_number);

#endif  // USE_SERIAL_NUMBER

/// def sd_hotswap_enabled() -> bool:
///     """
///     Returns True if SD card hot swapping is enabled
///     """
STATIC mp_obj_t mod_trezorutils_sd_hotswap_enabled(void) {
  return unit_properties()->sd_hotswap_enabled ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_sd_hotswap_enabled_obj,
                                 mod_trezorutils_sd_hotswap_enabled);

/// def presize_module(mod: module, n: int):
///     """
///     Ensure the module's dict is preallocated to an expected size.
///
///     This is used in modules like `trezor`, whose dict size depends not only
///     on the symbols defined in the file itself, but also on the number of
///     submodules that will be inserted into the module's namespace.
///     """
STATIC mp_obj_t mod_trezorutils_presize_module(mp_obj_t mod, mp_obj_t n) {
  if (!mp_obj_is_type(mod, &mp_type_module)) {
    mp_raise_TypeError(MP_ERROR_TEXT("expected module type"));
  }
  mp_uint_t size = trezor_obj_get_uint(n);
  mp_obj_dict_t *globals = mp_obj_module_get_globals(mod);
  mp_obj_dict_presize(globals, size);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorutils_presize_module_obj,
                                 mod_trezorutils_presize_module);

#if !PYOPT
#if LOG_STACK_USAGE
/// def zero_unused_stack() -> None:
///     """
///     Zero unused stack memory.
///     """
STATIC mp_obj_t mod_trezorutils_zero_unused_stack(void) {
  clear_unused_stack();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_zero_unused_stack_obj,
                                 mod_trezorutils_zero_unused_stack);

/// def estimate_unused_stack() -> int:
///     """
///     Estimate unused stack size.
///     """
STATIC mp_obj_t mod_trezorutils_estimate_unused_stack(void) {
  const uint8_t *stack_top = (const uint8_t *)MP_STATE_THREAD(stack_top);
  size_t stack_limit = MP_STATE_THREAD(stack_limit);

  const uint8_t *stack = stack_top - stack_limit;
  size_t offset = 0;
  for (; offset < stack_limit; ++offset) {
    if (stack[offset] != 0) {
      break;
    }
  }
  return mp_obj_new_int_from_uint(offset);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_estimate_unused_stack_obj,
                                 mod_trezorutils_estimate_unused_stack);

#endif  // LOG_STACK_USAGE

#if MICROPY_OOM_CALLBACK
static void gc_oom_callback(void) {
  gc_dump_info();
#if BLOCK_ON_VCP
  dump_meminfo_json(NULL);  // dump to stdout
#endif
}

/// if __debug__:
///     def enable_oom_dump() -> None:
///         """
///         Dump GC info in case of an OOM.
///         """
STATIC mp_obj_t mod_trezorutils_enable_oom_dump(void) {
  gc_set_oom_callback(gc_oom_callback);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_enable_oom_dump_obj,
                                 mod_trezorutils_enable_oom_dump);
#endif  // MICROPY_OOM_CALLBACK

static gc_info_t current_gc_info = {0};

/// if __debug__:
///     def clear_gc_info() -> None:
///         """
///         Clear GC heap stats.
///         """
STATIC mp_obj_t mod_trezorutils_clear_gc_info() {
  memzero(&current_gc_info, sizeof(current_gc_info));
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_clear_gc_info_obj,
                                 mod_trezorutils_clear_gc_info);

/// if __debug__:
///     def get_gc_info() -> dict[str, int]:
///         """
///         Get GC heap stats, updated by `update_gc_info`.
///         """
STATIC mp_obj_t mod_trezorutils_get_gc_info() {
  mp_obj_t result = mp_obj_new_dict(4);
  mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_total),
                    mp_obj_new_int_from_uint(current_gc_info.total));
  mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_used),
                    mp_obj_new_int_from_uint(current_gc_info.used));
  mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_free),
                    mp_obj_new_int_from_uint(current_gc_info.free));
  mp_obj_dict_store(result, MP_OBJ_NEW_QSTR(MP_QSTR_max_free),
                    mp_obj_new_int_from_uint(current_gc_info.max_free *
                                             MICROPY_BYTES_PER_GC_BLOCK));
  return result;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_get_gc_info_obj,
                                 mod_trezorutils_get_gc_info);

/// if __debug__:
///     def update_gc_info() -> None:
///         """
///         Update current GC heap statistics.
///         On emulator, also assert that free heap memory doesn't decrease.
///         Enabled only for frozen debug builds.
///         """
STATIC mp_obj_t mod_trezorutils_update_gc_info() {
#if MICROPY_MODULE_FROZEN_MPY
#ifdef TREZOR_EMULATOR
  size_t prev_free = current_gc_info.free;
#endif
  gc_info(&current_gc_info);
  // Currently, it may misdetect on-heap buffers' data as valid heap
  // pointers (resulting in `gc_mark_subtree` false-positives).
#ifdef TREZOR_EMULATOR
  if (prev_free > current_gc_info.free) {
    gc_dump_info();
    mp_raise_msg(&mp_type_AssertionError,
                 MP_ERROR_TEXT("Free heap size decreased"));
  }
#endif
#endif
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_update_gc_info_obj,
                                 mod_trezorutils_update_gc_info);

/// if __debug__:
///     def check_heap_fragmentation() -> None:
///         """
///         Assert known sources for heap fragmentation.
///         Enabled only for frozen debug builds.
///         """
STATIC mp_obj_t mod_trezorutils_check_heap_fragmentation(void) {
#if MICROPY_MODULE_FROZEN_MPY
  mp_obj_dict_t *modules = &MP_STATE_VM(mp_loaded_modules_dict);
  if (modules->map.alloc > MICROPY_LOADED_MODULES_DICT_SIZE) {
    mp_raise_msg(&mp_type_AssertionError,
                 MP_ERROR_TEXT("sys.modules dict is reallocated"));
  }
#ifdef TREZOR_EMULATOR
  // when profiling, __main__ module is `prof`, not `main`
  mp_obj_t main = mp_obj_dict_get(modules, MP_OBJ_NEW_QSTR(MP_QSTR_main));
  size_t main_map_alloc = mp_obj_module_get_globals(main)->map.alloc;
#else
  // `main.py` is executed (not imported), so there is no `main` module
  size_t main_map_alloc = MP_STATE_VM(dict_main).map.alloc;
#endif
  if (main_map_alloc > MICROPY_MAIN_DICT_SIZE) {
    mp_raise_msg(&mp_type_AssertionError,
                 MP_ERROR_TEXT("main globals dict is reallocated"));
  }

  size_t n_pool, n_qstr, n_str_data_bytes, n_total_bytes;
  qstr_pool_info(&n_pool, &n_qstr, &n_str_data_bytes, &n_total_bytes);
  if (n_pool) {
    qstr_dump_data();
    mp_raise_msg(&mp_type_AssertionError,
                 MP_ERROR_TEXT("Runtime QSTR allocation detected"));
  }
#endif  // MICROPY_MODULE_FROZEN_MPY
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_check_heap_fragmentation_obj,
                                 mod_trezorutils_check_heap_fragmentation);
#endif  // !PYOPT

/// def reboot_and_upgrade(
///     hash : AnyBytes,
/// ) -> None:
///     """
///     Reboots to perform upgrade to FW with specified hash.
///     """
STATIC mp_obj_t mod_trezorutils_reboot_and_upgrade(mp_obj_t hash_obj) {
  // Reboot and continue with the firmware upgrade
  mp_buffer_info_t hash = {0};

  mp_get_buffer_raise(hash_obj, &hash, MP_BUFFER_READ);

  if (hash.len != 32) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid value."));
  }

  reboot_and_upgrade((uint8_t *)hash.buf);
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_reboot_and_upgrade_obj,
                                 mod_trezorutils_reboot_and_upgrade);

/// def reboot_to_bootloader() -> None:
///     """
///     Reboots the device and stay in bootloader.
///     """
STATIC mp_obj_t mod_trezorutils_reboot_to_bootloader(void) {
  // Reboot and stay in bootloader
  reboot_to_bootloader();

  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_reboot_to_bootloader_obj,
                                 mod_trezorutils_reboot_to_bootloader);

/// def reboot() -> None:
///     """
///     Reboots the device.
///     """
STATIC mp_obj_t mod_trezorutils_reboot(void) {
#ifdef USE_BLE
  ble_switch_off();
#endif
#ifdef USE_NRF
  nrf_reboot();
#endif

  // Just reboot and go through the normal boot sequence
  reboot_device();

  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_reboot_obj,
                                 mod_trezorutils_reboot);

/// VersionTuple = Tuple[int, int, int, int]

/// class FirmwareHeaderInfo(NamedTuple):
///     version: VersionTuple
///     vendor: str
///     fingerprint: AnyBytes
///     hash: AnyBytes

/// mock:global

/// def check_firmware_header(header : AnyBytes) -> FirmwareHeaderInfo:
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

  mp_raise_ValueError(MP_ERROR_TEXT("Invalid value."));
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_check_firmware_header_obj,
                                 mod_trezorutils_check_firmware_header);

/// def bootloader_locked() -> bool | None:
///     """
///     Returns True/False if the bootloader is locked/unlocked and None if
///     the feature is not supported.
///     """
STATIC mp_obj_t mod_trezorutils_bootloader_locked() {
#if LOCKABLE_BOOTLOADER
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

/// def notify_send(event: int) -> None:
///     """
///     Sends a notification to host
///     """
STATIC mp_obj_t mod_trezorutils_notify_send(const mp_obj_t event) {
  mp_int_t value = mp_obj_get_int(event);
  if (value < 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid event."));
  }
  notify_send((notification_event_t)value);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_notify_send_obj,
                                 mod_trezorutils_notify_send);

#ifdef USE_NRF
/// def nrf_get_version() -> VersionTuple:
///     """
///     Reads version of nRF firmware
///     """
STATIC mp_obj_t mod_trezorutils_nrf_get_version(void) {
  uint32_t version = nrf_get_version();

  mp_obj_t nrf_version[4] = {mp_obj_new_int((version >> 24) & 0xff),
                             mp_obj_new_int((version >> 16) & 0xff),
                             mp_obj_new_int((version >> 8) & 0xff),
                             mp_obj_new_int((version >> 0) & 0xff)};

  mp_obj_t version_tuple =
      mp_obj_new_tuple(MP_ARRAY_SIZE(nrf_version), nrf_version);

  return version_tuple;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_nrf_get_version_obj,
                                 mod_trezorutils_nrf_get_version);
#endif

#ifdef USE_DBG_CONSOLE
/// def set_log_filter(filter: str) -> None:
///     """
///     Sets filter string for syslog
///     """
STATIC mp_obj_t mod_trezorutils_set_log_filter(mp_obj_t filter) {
  mp_buffer_info_t filter_buf = {0};
  mp_get_buffer_raise(filter, &filter_buf, MP_BUFFER_READ);
  syslog_set_filter(filter_buf.buf, filter_buf.len);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_set_log_filter_obj,
                                 mod_trezorutils_set_log_filter);
#endif

STATIC const mp_obj_str_t mod_trezorutils_revision_obj = {
    {&mp_type_bytes}, 0, sizeof(SCM_REVISION), (const byte *)SCM_REVISION};

STATIC const mp_obj_str_t mod_trezorutils_model_name_obj = {
    {&mp_type_str}, 0, sizeof(MODEL_NAME) - 1, (const byte *)MODEL_NAME};

STATIC const mp_obj_str_t mod_trezorutils_full_name_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_FULL_NAME) - 1,
    (const byte *)MODEL_FULL_NAME};

STATIC const mp_obj_str_t mod_trezorutils_model_usb_manufacturer_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_USB_MANUFACTURER) - 1,
    (const byte *)MODEL_USB_MANUFACTURER};

STATIC const mp_obj_str_t mod_trezorutils_model_usb_product_obj = {
    {&mp_type_str},
    0,
    sizeof(MODEL_USB_PRODUCT) - 1,
    (const byte *)MODEL_USB_PRODUCT};

STATIC const mp_obj_tuple_t mod_trezorutils_version_obj = {
    {&mp_type_tuple},
    4,
    {MP_OBJ_NEW_SMALL_INT(VERSION_MAJOR), MP_OBJ_NEW_SMALL_INT(VERSION_MINOR),
     MP_OBJ_NEW_SMALL_INT(VERSION_PATCH), MP_OBJ_NEW_SMALL_INT(VERSION_BUILD)}};

/// SCM_REVISION: bytes
/// """Git commit hash of the firmware."""
/// VERSION: VersionTuple
/// """Firmware version as a tuple (major, minor, patch, build)."""
/// USE_BLE: bool
/// """Whether the hardware supports BLE."""
/// USE_SD_CARD: bool
/// """Whether the hardware supports SD card."""
/// USE_SERIAL_NUMBER: bool
/// """Whether the hardware support exporting its serial number."""
/// USE_BACKLIGHT: bool
/// """Whether the hardware supports backlight brightness control."""
/// USE_HAPTIC: bool
/// """Whether the hardware supports haptic feedback."""
/// USE_RGB_LED: bool
/// """Whether the hardware supports RGB LED."""
/// USE_OPTIGA: bool
/// """Whether the hardware supports Optiga secure element."""
/// USE_TROPIC: bool
/// """Whether the hardware supports Tropic Square secure element."""
/// USE_TOUCH: bool
/// """Whether the hardware supports touch screen."""
/// USE_BUTTON: bool
/// """Whether the hardware supports two-button input."""
/// USE_POWER_MANAGER: bool
/// """Whether the hardware has a battery."""
/// USE_NRF: bool
/// """Whether the hardware has a nRF chip."""
/// USE_DBG_CONSOLE: bool
/// """Whether a debug console is enabled."""
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
/// HOMESCREEN_MAXSIZE: int
/// """Maximum size of user-uploaded homescreen in bytes."""
/// EMULATOR: bool
/// """Whether the firmware is running in the emulator."""
/// BITCOIN_ONLY: bool
/// """Whether the firmware is Bitcoin-only."""
/// UI_LAYOUT: str
/// """UI layout identifier ("BOLT"-T, "CAESAR"-TS3, "DELIZIA"-TS5)."""
/// USE_THP: bool
/// """Whether the firmware supports Trezor-Host Protocol (version 2)."""
/// NOTIFY_BOOT: int
/// """Notification event: boot completed."""
/// NOTIFY_UNLOCK: int
/// """Notification event: device unlocked from hardlock"""
/// NOTIFY_LOCK: int
/// """Notification event: device locked to hardlock"""
/// NOTIFY_DISCONNECT: int
/// """Notification event: user-initiated disconnect from host"""
/// NOTIFY_SETTING_CHANGE: int
/// """Notification event: change of settings"""
/// NOTIFY_SOFTLOCK: int
/// """Notification event: device soft-locked"""
/// NOTIFY_SOFTUNLOCK: int
/// """Notification event: device soft-unlocked"""
/// NOTIFY_PIN_CHANGE: int
/// """Notification event: PIN changed on the device"""
/// NOTIFY_WIPE: int
/// """Notification event: factory reset (wipe) invoked"""
/// NOTIFY_UNPAIR: int
/// """Notification event: BLE bonding for current connection deleted"""
///
/// if __debug__:
///     DISABLE_ANIMATION: bool
///     """Whether the firmware should disable animations."""
///     LOG_STACK_USAGE: bool
///     """Whether the firmware should log estimated stack usage."""

STATIC const mp_rom_map_elem_t mp_module_trezorutils_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorutils)},
    {MP_ROM_QSTR(MP_QSTR_consteq), MP_ROM_PTR(&mod_trezorutils_consteq_obj)},
    {MP_ROM_QSTR(MP_QSTR_memcpy), MP_ROM_PTR(&mod_trezorutils_memcpy_obj)},
    {MP_ROM_QSTR(MP_QSTR_memzero), MP_ROM_PTR(&mod_trezorutils_memzero_obj)},
    {MP_ROM_QSTR(MP_QSTR_halt), MP_ROM_PTR(&mod_trezorutils_halt_obj)},
    {MP_ROM_QSTR(MP_QSTR_firmware_hash),
     MP_ROM_PTR(&mod_trezorutils_firmware_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_firmware_vendor),
     MP_ROM_PTR(&mod_trezorutils_firmware_vendor_obj)},
    {MP_ROM_QSTR(MP_QSTR_reboot_and_upgrade),
     MP_ROM_PTR(&mod_trezorutils_reboot_and_upgrade_obj)},
    {MP_ROM_QSTR(MP_QSTR_reboot_to_bootloader),
     MP_ROM_PTR(&mod_trezorutils_reboot_to_bootloader_obj)},
    {MP_ROM_QSTR(MP_QSTR_reboot), MP_ROM_PTR(&mod_trezorutils_reboot_obj)},
    {MP_ROM_QSTR(MP_QSTR_check_firmware_header),
     MP_ROM_PTR(&mod_trezorutils_check_firmware_header_obj)},
    {MP_ROM_QSTR(MP_QSTR_bootloader_locked),
     MP_ROM_PTR(&mod_trezorutils_bootloader_locked_obj)},
    {MP_ROM_QSTR(MP_QSTR_notify_send),
     MP_ROM_PTR(&mod_trezorutils_notify_send_obj)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_BOOT), MP_ROM_INT(NOTIFY_BOOT)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_UNLOCK), MP_ROM_INT(NOTIFY_UNLOCK)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_LOCK), MP_ROM_INT(NOTIFY_LOCK)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_DISCONNECT), MP_ROM_INT(NOTIFY_DISCONNECT)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_SETTING_CHANGE),
     MP_ROM_INT(NOTIFY_SETTING_CHANGE)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_SOFTLOCK), MP_ROM_INT(NOTIFY_SOFTLOCK)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_SOFTUNLOCK), MP_ROM_INT(NOTIFY_SOFTUNLOCK)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_PIN_CHANGE), MP_ROM_INT(NOTIFY_PIN_CHANGE)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_WIPE), MP_ROM_INT(NOTIFY_WIPE)},
    {MP_ROM_QSTR(MP_QSTR_NOTIFY_UNPAIR), MP_ROM_INT(NOTIFY_UNPAIR)},
#ifdef USE_NRF
    {MP_ROM_QSTR(MP_QSTR_nrf_get_version),
     MP_ROM_PTR(&mod_trezorutils_nrf_get_version_obj)},
#endif
#ifdef USE_DBG_CONSOLE
    {MP_ROM_QSTR(MP_QSTR_set_log_filter),
     MP_ROM_PTR(&mod_trezorutils_set_log_filter_obj)},
#endif
    {MP_ROM_QSTR(MP_QSTR_delegated_identity),
     MP_ROM_PTR(&mod_trezorutils_delegated_identity_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_color),
     MP_ROM_PTR(&mod_trezorutils_unit_color_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_packaging),
     MP_ROM_PTR(&mod_trezorutils_unit_packaging_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_btconly),
     MP_ROM_PTR(&mod_trezorutils_unit_btconly_obj)},
    {MP_ROM_QSTR(MP_QSTR_unit_production_date),
     MP_ROM_PTR(&mod_trezorutils_unit_production_date_obj)},
#if USE_SERIAL_NUMBER
    {MP_ROM_QSTR(MP_QSTR_serial_number),
     MP_ROM_PTR(&mod_trezorutils_serial_number_obj)},
    {MP_ROM_QSTR(MP_QSTR_USE_SERIAL_NUMBER), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_SERIAL_NUMBER), mp_const_false},
#endif
#if !PYOPT
#if LOG_STACK_USAGE
    {MP_ROM_QSTR(MP_QSTR_zero_unused_stack),
     MP_ROM_PTR(&mod_trezorutils_zero_unused_stack_obj)},
    {MP_ROM_QSTR(MP_QSTR_estimate_unused_stack),
     MP_ROM_PTR(&mod_trezorutils_estimate_unused_stack_obj)},
#endif
#if MICROPY_OOM_CALLBACK
    {MP_ROM_QSTR(MP_QSTR_enable_oom_dump),
     MP_ROM_PTR(&mod_trezorutils_enable_oom_dump_obj)},
#endif
    {MP_ROM_QSTR(MP_QSTR_clear_gc_info),
     MP_ROM_PTR(&mod_trezorutils_clear_gc_info_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_gc_info),
     MP_ROM_PTR(&mod_trezorutils_get_gc_info_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_gc_info),
     MP_ROM_PTR(&mod_trezorutils_update_gc_info_obj)},
    {MP_ROM_QSTR(MP_QSTR_check_heap_fragmentation),
     MP_ROM_PTR(&mod_trezorutils_check_heap_fragmentation_obj)},
#endif
    {MP_ROM_QSTR(MP_QSTR_sd_hotswap_enabled),
     MP_ROM_PTR(&mod_trezorutils_sd_hotswap_enabled_obj)},
    {MP_ROM_QSTR(MP_QSTR_presize_module),
     MP_ROM_PTR(&mod_trezorutils_presize_module_obj)},
    // various built-in constants
    {MP_ROM_QSTR(MP_QSTR_SCM_REVISION),
     MP_ROM_PTR(&mod_trezorutils_revision_obj)},
    {MP_ROM_QSTR(MP_QSTR_VERSION), MP_ROM_PTR(&mod_trezorutils_version_obj)},
#ifdef USE_SD_CARD
    {MP_ROM_QSTR(MP_QSTR_USE_SD_CARD), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_SD_CARD), mp_const_false},
#endif
#ifdef USE_BLE
    {MP_ROM_QSTR(MP_QSTR_USE_BLE), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_BLE), mp_const_false},
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
#ifdef USE_RGB_LED
    {MP_ROM_QSTR(MP_QSTR_USE_RGB_LED), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_RGB_LED), mp_const_false},
#endif
#ifdef USE_OPTIGA
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_OPTIGA), mp_const_false},
#endif
#ifdef USE_TROPIC
    {MP_ROM_QSTR(MP_QSTR_USE_TROPIC), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_TROPIC), mp_const_false},
#endif
#ifdef USE_TOUCH
    {MP_ROM_QSTR(MP_QSTR_USE_TOUCH), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_TOUCH), mp_const_false},
#endif
#ifdef USE_BUTTON
    {MP_ROM_QSTR(MP_QSTR_USE_BUTTON), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_BUTTON), mp_const_false},
#endif
#ifdef USE_POWER_MANAGER
    {MP_ROM_QSTR(MP_QSTR_USE_POWER_MANAGER), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_POWER_MANAGER), mp_const_false},
#endif
#ifdef USE_NRF
    {MP_ROM_QSTR(MP_QSTR_USE_NRF), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_NRF), mp_const_false},
#endif
#ifdef USE_DBG_CONSOLE
    {MP_ROM_QSTR(MP_QSTR_USE_DBG_CONSOLE), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_USE_DBG_CONSOLE), mp_const_false},
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
    {MP_ROM_QSTR(MP_QSTR_HOMESCREEN_MAXSIZE),
     MP_ROM_INT(MODEL_HOMESCREEN_MAXSIZE)},
#ifdef TREZOR_EMULATOR
    {MP_ROM_QSTR(MP_QSTR_EMULATOR), mp_const_true},
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
#ifdef UI_LAYOUT_BOLT
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_BOLT)},
#elif UI_LAYOUT_CAESAR
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_CAESAR)},
#elif UI_LAYOUT_DELIZIA
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_DELIZIA)},
#elif UI_LAYOUT_ECKHART
    {MP_ROM_QSTR(MP_QSTR_UI_LAYOUT), MP_ROM_QSTR(MP_QSTR_ECKHART)},
#else
#error Unknown layout
#endif
#if !PYOPT
    MEMINFO_DICT_ENTRIES
#if DISABLE_ANIMATION
    {MP_ROM_QSTR(MP_QSTR_DISABLE_ANIMATION), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_DISABLE_ANIMATION), mp_const_false},
#endif  // TREZOR_DISABLE_ANIMATION
#if LOG_STACK_USAGE
    {MP_ROM_QSTR(MP_QSTR_LOG_STACK_USAGE), mp_const_true},
#else
    {MP_ROM_QSTR(MP_QSTR_LOG_STACK_USAGE), mp_const_false},
#endif  // LOG_STACK_USAGE
#endif  // PYOPT
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorutils_globals,
                            mp_module_trezorutils_globals_table);

const mp_obj_module_t mp_module_trezorutils = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorutils_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorutils, mp_module_trezorutils);

#endif  // MICROPY_PY_TREZORUTILS
