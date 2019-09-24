/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "embed/extmod/trezorobj.h"
#include "py/mperrno.h"
#include "py/objstr.h"

// clang-format off
#include "ff.h"
#include "diskio.h"
#include "sdcard.h"
// clang-format on

DRESULT disk_read(void *drv, BYTE *buff, DWORD sector, UINT count) {
  if (sectrue == sdcard_read_blocks((uint32_t *)buff, sector, count)) {
    return RES_OK;
  } else {
    return RES_ERROR;
  }
}

DRESULT disk_write(void *drv, const BYTE *buff, DWORD sector, UINT count) {
  if (sectrue == sdcard_write_blocks((const uint32_t *)buff, sector, count)) {
    return RES_OK;
  } else {
    return RES_ERROR;
  }
}

DRESULT disk_ioctl(void *drv, BYTE cmd, void *buff) {
  (void)drv;
  switch (cmd) {
    case CTRL_SYNC:
      return RES_OK;
    case GET_SECTOR_COUNT:
      *((DWORD *)buff) = sdcard_get_capacity_in_bytes() / SDCARD_BLOCK_SIZE;
      return RES_OK;
    case GET_SECTOR_SIZE:
      *((WORD *)buff) = SDCARD_BLOCK_SIZE;
      return RES_OK;
    case GET_BLOCK_SIZE:
      *((DWORD *)buff) = 1;
      return RES_OK;
    case IOCTL_INIT:
      *((DSTATUS *)buff) = (sectrue == sdcard_is_present()) ? 0 : STA_NODISK;
      return RES_OK;
    case IOCTL_STATUS:
      *((DSTATUS *)buff) = (sectrue == sdcard_is_present()) ? 0 : STA_NODISK;
      return RES_OK;
    default:
      return RES_PARERR;
  }
}

// this table converts from FRESULT to POSIX errno
const uint8_t fresult_to_errno_table[20] = {
    [FR_OK] = 0,
    [FR_DISK_ERR] = MP_EIO,
    [FR_INT_ERR] = MP_EIO,
    [FR_NOT_READY] = MP_EBUSY,
    [FR_NO_FILE] = MP_ENOENT,
    [FR_NO_PATH] = MP_ENOENT,
    [FR_INVALID_NAME] = MP_EINVAL,
    [FR_DENIED] = MP_EACCES,
    [FR_EXIST] = MP_EEXIST,
    [FR_INVALID_OBJECT] = MP_EINVAL,
    [FR_WRITE_PROTECTED] = MP_EROFS,
    [FR_INVALID_DRIVE] = MP_ENODEV,
    [FR_NOT_ENABLED] = MP_ENODEV,
    [FR_NO_FILESYSTEM] = MP_ENODEV,
    [FR_MKFS_ABORTED] = MP_EIO,
    [FR_TIMEOUT] = MP_EIO,
    [FR_LOCKED] = MP_EIO,
    [FR_NOT_ENOUGH_CORE] = MP_ENOMEM,
    [FR_TOO_MANY_OPEN_FILES] = MP_EMFILE,
    [FR_INVALID_PARAMETER] = MP_EINVAL,
};

STATIC mp_obj_t filinfo_to_tuple(const FILINFO *info) {
  mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(3, NULL));
  tuple->items[0] = mp_obj_new_int_from_uint(info->fsize);
  char attrs[] = "-----";
  if (info->fattrib & AM_RDO) {
    attrs[0] = 'r';
  }
  if (info->fattrib & AM_HID) {
    attrs[1] = 'h';
  }
  if (info->fattrib & AM_SYS) {
    attrs[2] = 's';
  }
  if (info->fattrib & AM_DIR) {
    attrs[3] = 'd';
  }
  if (info->fattrib & AM_ARC) {
    attrs[4] = 'a';
  }
  tuple->items[1] = mp_obj_new_str(attrs, 5);
  tuple->items[2] = mp_obj_new_str(info->fname, strlen(info->fname));
  return MP_OBJ_FROM_PTR(tuple);
}

/// class FatFSFile:
///     """
///     Class encapsulating file
///     """
typedef struct _mp_obj_FatFSFile_t {
  mp_obj_base_t base;
  FIL fp;
} mp_obj_FatFSFile_t;

/// def __exit__(self) -> None:
///     """
///     Close an open file object
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile___exit__(size_t n_args,
                                                const mp_obj_t *args) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(args[0]);
  FRESULT res = f_close(&(o->fp));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_FatFSFile___exit___obj,
                                           4, 4,
                                           mod_trezorio_FatFSFile___exit__);

/// def close(self) -> None:
///     """
///     Close an open file object
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_close(mp_obj_t self) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  FRESULT res = f_close(&(o->fp));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFSFile_close_obj,
                                 mod_trezorio_FatFSFile_close);

/// def read(self, data: bytearray) -> int:
///     """
///     Read data from the file
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_read(mp_obj_t self, mp_obj_t data) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t buf;
  mp_get_buffer_raise(data, &buf, MP_BUFFER_WRITE);
  UINT read;
  FRESULT res = f_read(&(o->fp), buf.buf, buf.len, &read);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_obj_new_int_from_uint(read);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFSFile_read_obj,
                                 mod_trezorio_FatFSFile_read);

/// def write(self, data: bytearray) -> int:
///     """
///     Write data to the file
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_write(mp_obj_t self, mp_obj_t data) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t buf;
  mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
  UINT written;
  FRESULT res = f_write(&(o->fp), buf.buf, buf.len, &written);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  if (written != buf.len) {
    /* no space left on device or free clusters recorded in FSInfo fell to 0 */
    mp_raise_OSError(MP_ENOSPC);
  }
  return mp_obj_new_int_from_uint(written);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFSFile_write_obj,
                                 mod_trezorio_FatFSFile_write);

/// def seek(self, offset: int) -> None:
///     """
///     Move file pointer of the file object
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_seek(mp_obj_t self, mp_obj_t offset) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  FSIZE_t ofs = trezor_obj_get_uint(offset);
  FRESULT res = f_lseek(&(o->fp), ofs);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFSFile_seek_obj,
                                 mod_trezorio_FatFSFile_seek);

/// def truncate(self) -> None:
///     """
///     Truncate the file
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_truncate(mp_obj_t self) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  FRESULT res = f_truncate(&(o->fp));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFSFile_truncate_obj,
                                 mod_trezorio_FatFSFile_truncate);

/// def sync(self) -> None:
///     """
///     Flush cached data of the writing file
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_sync(mp_obj_t self) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  FRESULT res = f_sync(&(o->fp));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFSFile_sync_obj,
                                 mod_trezorio_FatFSFile_sync);

STATIC const mp_rom_map_elem_t mod_trezorio_FatFSFile_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___enter__), MP_ROM_PTR(&mp_identity_obj)},
    {MP_ROM_QSTR(MP_QSTR___exit__),
     MP_ROM_PTR(&mod_trezorio_FatFSFile___exit___obj)},
    {MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mod_trezorio_FatFSFile_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_trezorio_FatFSFile_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_FatFSFile_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_seek), MP_ROM_PTR(&mod_trezorio_FatFSFile_seek_obj)},
    {MP_ROM_QSTR(MP_QSTR_truncate),
     MP_ROM_PTR(&mod_trezorio_FatFSFile_truncate_obj)},
    {MP_ROM_QSTR(MP_QSTR_sync), MP_ROM_PTR(&mod_trezorio_FatFSFile_sync_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_FatFSFile_locals_dict,
                            mod_trezorio_FatFSFile_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_FatFSFile_type = {
    {&mp_type_type},
    .name = MP_QSTR_FatFSFile,
    .locals_dict = (void *)&mod_trezorio_FatFSFile_locals_dict,
};

/// class FatFSDir(Iterable[Tuple[int, str, str]]):
///     """
///     Class encapsulating directory
///     """
typedef struct _mp_obj_FatFSDir_t {
  mp_obj_base_t base;
  FF_DIR dp;
} mp_obj_FatFSDir_t;

/// def __next__(self) -> Tuple[int, str, str]:
///     """
///     Read an entry in the directory
///     """
STATIC mp_obj_t mod_trezorio_FatFSDir_iternext(mp_obj_t self) {
  mp_obj_FatFSDir_t *o = MP_OBJ_TO_PTR(self);
  FILINFO info;
  FRESULT res = f_readdir(&(o->dp), &info);
  if (res != FR_OK) {
    f_closedir(&(o->dp));
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  if (info.fname[0] == 0) {  // stop on end of dir
    f_closedir(&(o->dp));
    return MP_OBJ_STOP_ITERATION;
  }
  return filinfo_to_tuple(&info);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFSDir_iternext_obj,
                                 mod_trezorio_FatFSDir_iternext);

STATIC const mp_obj_type_t mod_trezorio_FatFSDir_type = {
    {&mp_type_type},
    .name = MP_QSTR_FatFSDir,
    .getiter = mp_identity_getiter,
    .iternext = mod_trezorio_FatFSDir_iternext,
};

/// class FatFS:
///     """
///     Class encapsulating FAT filesystem
///     """
typedef struct _mp_obj_FatFS_t {
  mp_obj_base_t base;
  FATFS fs;
} mp_obj_FatFS_t;

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorio_FatFS_make_new(const mp_obj_type_t *type,
                                            size_t n_args, size_t n_kw,
                                            const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 0, false);
  mp_obj_FatFS_t *o = m_new_obj(mp_obj_FatFS_t);
  o->base.type = type;
  return MP_OBJ_FROM_PTR(o);
}

/// def open(self, path: str, flags: str) -> FatFSFile:
///     """
///     Open or create a file
///     """
STATIC mp_obj_t mod_trezorio_FatFS_open(mp_obj_t self, mp_obj_t path,
                                        mp_obj_t flags) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t _path, _flags;
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  mp_get_buffer_raise(flags, &_flags, MP_BUFFER_READ);
  const char *mode_s = _flags.buf;
  uint8_t mode = 0;
  while (*mode_s) {
    switch (*mode_s++) {
      case 'r':
        mode |= FA_READ;
        break;
      case 'w':
        mode |= FA_WRITE | FA_CREATE_ALWAYS;
        break;
      case 'x':
        mode |= FA_WRITE | FA_CREATE_NEW;
        break;
      case 'a':
        mode |= FA_WRITE | FA_OPEN_ALWAYS;
        break;
      case '+':
        mode |= FA_READ | FA_WRITE;
        break;
    }
  }
  FIL fp;
  FRESULT res = f_open(&(o->fs), &fp, _path.buf, mode);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  mp_obj_FatFSFile_t *f = m_new_obj(mp_obj_FatFSFile_t);
  f->base.type = &mod_trezorio_FatFSFile_type;
  f->fp = fp;
  return f;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_FatFS_open_obj,
                                 mod_trezorio_FatFS_open);

/// def listdir(self, path: str) -> FatFSDir:
///     """
///     List a directory (return generator)
///     """
STATIC mp_obj_t mod_trezorio_FatFS_listdir(mp_obj_t self, mp_obj_t path) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t _path;
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  FF_DIR dp;
  FRESULT res = f_opendir(&(o->fs), &dp, _path.buf);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  mp_obj_FatFSDir_t *d = m_new_obj(mp_obj_FatFSDir_t);
  d->base.type = &mod_trezorio_FatFSDir_type;
  d->dp = dp;
  return d;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFS_listdir_obj,
                                 mod_trezorio_FatFS_listdir);

/// def mkdir(self, path: str, exist_ok: bool=False) -> None:
///     """
///     Create a sub directory
///     """
STATIC mp_obj_t mod_trezorio_FatFS_mkdir(size_t n_args, const mp_obj_t *args) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(args[0]);
  mp_buffer_info_t path;
  mp_get_buffer_raise(args[1], &path, MP_BUFFER_READ);
  FRESULT res = f_mkdir(&(o->fs), path.buf);
  // directory exists and exist_ok is True, return without failure
  if (res == FR_EXIST && n_args > 2 && args[2] == mp_const_true) {
    return mp_const_none;
  }
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_FatFS_mkdir_obj, 2, 3,
                                           mod_trezorio_FatFS_mkdir);

/// def unlink(self, path: str) -> None:
///     """
///     Delete an existing file or directory
///     """
STATIC mp_obj_t mod_trezorio_FatFS_unlink(mp_obj_t self, mp_obj_t path) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t _path;
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  FRESULT res = f_unlink(&(o->fs), _path.buf);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFS_unlink_obj,
                                 mod_trezorio_FatFS_unlink);

/// def stat(self, path: str) -> Tuple[int, str, str]:
///     """
///     Get file status
///     """
STATIC mp_obj_t mod_trezorio_FatFS_stat(mp_obj_t self, mp_obj_t path) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t _path;
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  FILINFO info;
  FRESULT res = f_stat(&(o->fs), _path.buf, &info);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return filinfo_to_tuple(&info);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFS_stat_obj,
                                 mod_trezorio_FatFS_stat);

/// def rename(self, oldpath: str, newpath: str) -> None:
///     """
///     Rename/Move a file or directory
///     """
STATIC mp_obj_t mod_trezorio_FatFS_rename(mp_obj_t self, mp_obj_t oldpath,
                                          mp_obj_t newpath) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t _oldpath, _newpath;
  mp_get_buffer_raise(oldpath, &_oldpath, MP_BUFFER_READ);
  mp_get_buffer_raise(newpath, &_newpath, MP_BUFFER_READ);
  FRESULT res = f_rename(&(o->fs), _oldpath.buf, _newpath.buf);
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_FatFS_rename_obj,
                                 mod_trezorio_FatFS_rename);

/// def mount(self) -> None:
///     """
///     Mount/Unmount a logical drive
///     """
STATIC mp_obj_t mod_trezorio_FatFS_mount(mp_obj_t self) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  FRESULT res = f_mount(&(o->fs));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFS_mount_obj,
                                 mod_trezorio_FatFS_mount);

/// def unmount(self) -> None:
///     """
///     Unmount a logical drive
///     """
STATIC mp_obj_t mod_trezorio_FatFS_unmount(mp_obj_t self) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  FRESULT res = f_umount(&(o->fs));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFS_unmount_obj,
                                 mod_trezorio_FatFS_unmount);

#ifdef TREZOR_EMULATOR

/// def mkfs(self) -> None:
///     """
///     Create a FAT volume
///     """
STATIC mp_obj_t mod_trezorio_FatFS_mkfs(mp_obj_t self) {
  mp_obj_FatFS_t *o = MP_OBJ_TO_PTR(self);
  uint8_t working_buf[FF_MAX_SS];
  FRESULT res = f_mkfs(&(o->fs), FM_FAT32, 0, working_buf, sizeof(working_buf));
  if (res != FR_OK) {
    mp_raise_OSError(fresult_to_errno_table[res]);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_FatFS_mkfs_obj,
                                 mod_trezorio_FatFS_mkfs);

#endif

STATIC const mp_rom_map_elem_t mod_trezorio_FatFS_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&mod_trezorio_FatFS_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_listdir), MP_ROM_PTR(&mod_trezorio_FatFS_listdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_mkdir), MP_ROM_PTR(&mod_trezorio_FatFS_mkdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_unlink), MP_ROM_PTR(&mod_trezorio_FatFS_unlink_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&mod_trezorio_FatFS_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_stat), MP_ROM_PTR(&mod_trezorio_FatFS_stat_obj)},
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&mod_trezorio_FatFS_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_unmount), MP_ROM_PTR(&mod_trezorio_FatFS_unmount_obj)},
#ifdef TREZOR_EMULATOR
    {MP_ROM_QSTR(MP_QSTR_mkfs), MP_ROM_PTR(&mod_trezorio_FatFS_mkfs_obj)},
#endif
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_FatFS_locals_dict,
                            mod_trezorio_FatFS_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_FatFS_type = {
    {&mp_type_type},
    .name = MP_QSTR_FatFS,
    .make_new = mod_trezorio_FatFS_make_new,
    .locals_dict = (void *)&mod_trezorio_FatFS_locals_dict,
};
