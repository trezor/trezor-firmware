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

#include <string.h>

#include "blake2s.h"
#include "common.h"
#include "flash_otp.h"
#include "model.h"

#include "embed/extmod/trezorobj.h"

/// package: trezorio.__init__

/// class FlashOTP:
///     """
///     """
typedef struct _mp_obj_FlashOTP_t {
  mp_obj_base_t base;
} mp_obj_FlashOTP_t;

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorio_FlashOTP_make_new(const mp_obj_type_t *type,
                                               size_t n_args, size_t n_kw,
                                               const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 0, false);
  mp_obj_FlashOTP_t *o = mp_obj_malloc(mp_obj_FlashOTP_t, type);
  return MP_OBJ_FROM_PTR(o);
}

/// def write(self, block: int, offset: int, data: bytes) -> None:
///     """
///     Writes data to OTP flash
///     """
STATIC mp_obj_t mod_trezorio_FlashOTP_write(size_t n_args,
                                            const mp_obj_t *args) {
  uint8_t block = trezor_obj_get_uint8(args[1]);
  uint8_t offset = trezor_obj_get_uint8(args[2]);
  mp_buffer_info_t data = {0};
  mp_get_buffer_raise(args[3], &data, MP_BUFFER_READ);
  if (sectrue != flash_otp_write(block, offset, data.buf, data.len)) {
    mp_raise_ValueError("write failed");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_FlashOTP_write_obj, 4,
                                           4, mod_trezorio_FlashOTP_write);

/// def read(self, block: int, offset: int, data: bytearray) -> None:
///     """
///     Reads data from OTP flash
///     """
STATIC mp_obj_t mod_trezorio_FlashOTP_read(size_t n_args,
                                           const mp_obj_t *args) {
  uint8_t block = trezor_obj_get_uint8(args[1]);
  uint8_t offset = trezor_obj_get_uint8(args[2]);
  mp_buffer_info_t data = {0};
  mp_get_buffer_raise(args[3], &data, MP_BUFFER_WRITE);
  if (sectrue != flash_otp_read(block, offset, data.buf, data.len)) {
    mp_raise_ValueError("read failed");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_FlashOTP_read_obj, 4, 4,
                                           mod_trezorio_FlashOTP_read);

/// def lock(self, block: int) -> None:
///     """
///     Lock OTP flash block
///     """
STATIC mp_obj_t mod_trezorio_FlashOTP_lock(mp_obj_t self, mp_obj_t block) {
  uint8_t b = trezor_obj_get_uint8(block);
  if (sectrue != flash_otp_lock(b)) {
    mp_raise_ValueError("lock failed");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FlashOTP_lock_obj,
                                 mod_trezorio_FlashOTP_lock);

/// def is_locked(self, block: int) -> bool:
///     """
///     Is OTP flash block locked?
///     """
STATIC mp_obj_t mod_trezorio_FlashOTP_is_locked(mp_obj_t self, mp_obj_t block) {
  uint8_t b = trezor_obj_get_uint8(block);
  return (sectrue == flash_otp_is_locked(b)) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FlashOTP_is_locked_obj,
                                 mod_trezorio_FlashOTP_is_locked);

STATIC const mp_rom_map_elem_t mod_trezorio_FlashOTP_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_trezorio_FlashOTP_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_FlashOTP_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_lock), MP_ROM_PTR(&mod_trezorio_FlashOTP_lock_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_locked),
     MP_ROM_PTR(&mod_trezorio_FlashOTP_is_locked_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_FlashOTP_locals_dict,
                            mod_trezorio_FlashOTP_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_FlashOTP_type = {
    {&mp_type_type},
    .name = MP_QSTR_FlashOTP,
    .make_new = mod_trezorio_FlashOTP_make_new,
    .locals_dict = (void *)&mod_trezorio_FlashOTP_locals_dict,
};

/// class FlashArea:
///     """
///     Area of the flash memory
///     """

typedef struct _mp_obj_FlashArea_t {
  mp_obj_base_t base;
  const flash_area_t *area;
} mp_obj_FlashArea_t;

#define FLASH_READ_CHUNK_SIZE 1024
#define CHUNKS_PER_PROGRESS_STEP ((1024 / FLASH_READ_CHUNK_SIZE) * 16)

static void ui_progress(mp_obj_t ui_wait_callback, uint32_t current) {
  if (mp_obj_is_callable(ui_wait_callback)) {
    mp_call_function_1_protected(ui_wait_callback, mp_obj_new_int(current));
  }
}

/// def size(self) -> int:
///     """
///     Returns size of the flash area
///     """
STATIC mp_obj_t mod_trezorio_FlashArea_size(mp_obj_t obj_self) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(obj_self);
  return MP_OBJ_NEW_SMALL_INT(flash_area_get_size(self->area));
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FlashArea_size_obj,
                                 mod_trezorio_FlashArea_size);

/// def hash(
///     self,
///     offset: int,
///     length: int,
///     challenge: bytes | None = None,
///     callback: Callable[[int], None] | None = None,
/// ) -> bytes:
///     """
///     Computes a Blake2s hash of a segment of the flash area.
///     Offset and length must be aligned to 1024 bytes.
///     An optional challenge can be used as the Blake2s key.
///     The progress callback will be invoked every 16 kB with the number of
///     bytes processed so far.
///     """
STATIC mp_obj_t mod_trezorio_FlashArea_hash(size_t n_args,
                                            const mp_obj_t *args) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(args[0]);
  uint32_t offset = trezor_obj_get_uint(args[1]);
  uint32_t length = trezor_obj_get_uint(args[2]);

  if (offset % FLASH_READ_CHUNK_SIZE != 0 ||
      length % FLASH_READ_CHUNK_SIZE != 0) {
    mp_raise_ValueError("Offset and length must be aligned to 1024 bytes.");
  }

  mp_buffer_info_t challenge = {0};
  if (n_args > 3 && args[3] != mp_const_none) {
    mp_get_buffer_raise(args[3], &challenge, MP_BUFFER_READ);
  }
  mp_obj_t ui_wait_callback = mp_const_none;
  if (n_args > 4) {
    ui_wait_callback = args[4];
  }

  BLAKE2S_CTX ctx;

  if (challenge.len != 0) {
    if (blake2s_InitKey(&ctx, BLAKE2S_DIGEST_LENGTH, challenge.buf,
                        challenge.len) != 0) {
      mp_raise_msg(&mp_type_ValueError, "Invalid challenge.");
    }
  } else {
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  }

  uint32_t area_size = flash_area_get_size(self->area);
  if (offset > area_size || area_size - offset < length) {
    mp_raise_ValueError("Read too long.");
  }
  const uint32_t chunks = length / FLASH_READ_CHUNK_SIZE;

  ui_progress(ui_wait_callback, 0);
  for (int i = 0; i < chunks; i++) {
    const uint32_t current_offset = offset + i * FLASH_READ_CHUNK_SIZE;
    const void *data = flash_area_get_address(self->area, current_offset,
                                              FLASH_READ_CHUNK_SIZE);
    if (data == NULL) {
      mp_raise_msg(&mp_type_RuntimeError, "Failed to read flash.");
    }
    blake2s_Update(&ctx, data, FLASH_READ_CHUNK_SIZE);
    if (i % CHUNKS_PER_PROGRESS_STEP == 0) {
      ui_progress(ui_wait_callback, i * FLASH_READ_CHUNK_SIZE);
    }
  }

  ui_progress(ui_wait_callback, length);

  vstr_t vstr = {0};
  vstr_init_len(&vstr, BLAKE2S_DIGEST_LENGTH);
  if (blake2s_Final(&ctx, vstr.buf, vstr.len) != 0) {
    vstr_clear(&vstr);
    mp_raise_msg(&mp_type_RuntimeError, "Failed to finalize hash.");
  }

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_FlashArea_hash_obj, 3,
                                           5, mod_trezorio_FlashArea_hash);

/// if __debug__:
///     def read(self, offset: int, data: bytearray) -> None:
///         """
///         Reads data from flash area. Will read exact length of data
///         bytearray. Offset and length of data must be aligned to 1024 bytes.
///         """
#if PYOPT == 0
STATIC mp_obj_t mod_trezorio_FlashArea_read(mp_obj_t obj_self,
                                            mp_obj_t obj_offset,
                                            mp_obj_t obj_data) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(obj_self);
  uint32_t offset = trezor_obj_get_uint(obj_offset);
  mp_buffer_info_t data = {0};
  mp_get_buffer_raise(obj_data, &data, MP_BUFFER_WRITE);

  if (offset % FLASH_READ_CHUNK_SIZE != 0 ||
      data.len % FLASH_READ_CHUNK_SIZE != 0) {
    mp_raise_ValueError("Offset and length must be aligned to 1024 bytes.");
  }

  uint32_t area_size = flash_area_get_size(self->area);
  if (offset > area_size || area_size - offset < data.len) {
    mp_raise_ValueError("Read too long.");
  }
  uint32_t chunks = data.len / FLASH_READ_CHUNK_SIZE;
  for (int i = 0; i < chunks; i++) {
    const uint32_t current_offset = offset + i * FLASH_READ_CHUNK_SIZE;
    const void *flash_data = flash_area_get_address(&FIRMWARE_AREA, current_offset,
                                              FLASH_READ_CHUNK_SIZE);
    if (flash_data == NULL) {
      mp_raise_msg(&mp_type_RuntimeError, "Failed to read flash.");
    }
    memcpy(data.buf + i * FLASH_READ_CHUNK_SIZE, flash_data, FLASH_READ_CHUNK_SIZE);
  }
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_FlashArea_read_obj,
                                 mod_trezorio_FlashArea_read);

/// if __debug__:
///     def write(self, offset: int, data: bytes) -> None:
///         """
///         Writes data to flash area.
///         Offset and written data size must be a multiple of FLASH_BLOCK_SIZE,
///         that is, 4 bytes on F4 or 16 bytes on U5.
///         """
STATIC mp_obj_t mod_trezorio_FlashArea_write(mp_obj_t obj_self,
                                             mp_obj_t obj_offset,
                                             mp_obj_t obj_data) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(obj_self);
  uint32_t offset = trezor_obj_get_uint(obj_offset);
  mp_buffer_info_t data = {0};
  mp_get_buffer_raise(obj_data, &data, MP_BUFFER_READ);

  if (data.len % FLASH_BLOCK_SIZE != 0) {
    mp_raise_ValueError("Write size must be a multiple of write unit.");
  }

  uint32_t area_size = flash_area_get_size(self->area);
  if (offset > area_size || area_size - offset < data.len) {
    mp_raise_ValueError("Write too long.");
  }

  uint32_t blocks = data.len / FLASH_BLOCK_SIZE;
  const flash_block_t *data_as_blocks = (const flash_block_t *)data.buf;

  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < blocks; i++) {
    if (sectrue != flash_area_write_block(self->area,
                                          offset + i * FLASH_BLOCK_SIZE,
                                          data_as_blocks[i])) {
      ensure(flash_lock_write(), NULL);
      mp_raise_ValueError("Write failed.");
    }
  }
  ensure(flash_lock_write(), NULL);
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_FlashArea_write_obj,
                                 mod_trezorio_FlashArea_write);

/// if __debug__:
///     def erase_sector(self, offset: int) -> None:
///         """
///         Erases a flash area sector starting at specified offset.
///         """
STATIC mp_obj_t mod_trezorio_FlashArea_erase_sector(mp_obj_t obj_self,
                                                    mp_obj_t obj_offset) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(obj_self);
  uint32_t offset = trezor_obj_get_uint(obj_offset);
  uint32_t bytes_erased = 0;
  if (sectrue != flash_area_erase_partial(self->area, offset, &bytes_erased)) {
    mp_raise_ValueError("Erase failed.");
  }
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FlashArea_erase_sector_obj,
                                 mod_trezorio_FlashArea_erase_sector);

/// if __debug__:
///     def erase(self) -> None:
///         """
///         Erases the whole flash area.
///         """
STATIC mp_obj_t mod_trezorio_FlashArea_erase(mp_obj_t obj_self) {
  mp_obj_FlashArea_t *self = (mp_obj_FlashArea_t *)MP_OBJ_TO_PTR(obj_self);
  if (sectrue != flash_area_erase(self->area, NULL)) {
    mp_raise_ValueError("Erase failed.");
  }
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FlashArea_erase_obj,
                                 mod_trezorio_FlashArea_erase);

#endif  // PYOPT == 0

STATIC const mp_rom_map_elem_t mod_trezorio_FlashArea_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&mod_trezorio_FlashArea_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_hash), MP_ROM_PTR(&mod_trezorio_FlashArea_hash_obj)},
#if PYOPT == 0
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_trezorio_FlashArea_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_FlashArea_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_erase_sector),
     MP_ROM_PTR(&mod_trezorio_FlashArea_erase_sector_obj)},
    {MP_ROM_QSTR(MP_QSTR_erase), MP_ROM_PTR(&mod_trezorio_FlashArea_erase_obj)},
#endif
};

STATIC MP_DEFINE_CONST_DICT(mod_trezorio_FlashArea_locals_dict,
                            mod_trezorio_FlashArea_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_FlashArea_type = {
    {&mp_type_type},
    .name = MP_QSTR_FlashArea,
    .locals_dict = (void *)&mod_trezorio_FlashArea_locals_dict,
};

#define FLASH_AREA(name, area_id)                                    \
  STATIC const mp_obj_FlashArea_t mod_trezorio_flash_area_##name = { \
      .base = {.type = MP_ROM_PTR(&mod_trezorio_FlashArea_type)},    \
      .area = &area_id,                                              \
  };

/// mock:global
/// package: trezorio.flash_area
/// from . import FlashArea
/// BOARDLOADER: FlashArea
/// BOOTLOADER: FlashArea
/// FIRMWARE: FlashArea
/// TRANSLATIONS: FlashArea
/// if __debug__:
///     STORAGE_A: FlashArea
///     STORAGE_B: FlashArea
FLASH_AREA(BOARDLOADER, BOARDLOADER_AREA)
FLASH_AREA(BOOTLOADER, BOOTLOADER_AREA)
FLASH_AREA(FIRMWARE, FIRMWARE_AREA)
FLASH_AREA(TRANSLATIONS, TRANSLATIONS_AREA)
#if PYOPT == 0
FLASH_AREA(STORAGE_A, STORAGE_AREAS[0])
FLASH_AREA(STORAGE_B, STORAGE_AREAS[1])
#endif

#define MP_ROM_FLASH_AREA(name) \
  { MP_ROM_QSTR(MP_QSTR_##name), MP_ROM_PTR(&mod_trezorio_flash_area_##name) }

STATIC const mp_rom_map_elem_t mod_trezorio_flash_area_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_flash_area)},
    MP_ROM_FLASH_AREA(BOARDLOADER),
    MP_ROM_FLASH_AREA(BOOTLOADER),
    MP_ROM_FLASH_AREA(FIRMWARE),
    MP_ROM_FLASH_AREA(TRANSLATIONS),
#if PYOPT == 0
    MP_ROM_FLASH_AREA(STORAGE_A),
    MP_ROM_FLASH_AREA(STORAGE_B),
#endif
};

STATIC MP_DEFINE_CONST_DICT(mod_trezorio_flash_area_globals,
                            mod_trezorio_flash_area_globals_table);

const mp_obj_module_t mod_trezorio_flash_area = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_flash_area_globals,
};
