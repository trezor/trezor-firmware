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

/// package: trezorio.fatfs

// clang-format off
/// FR_OK: int                   # (0) Succeeded
/// FR_DISK_ERR: int             # (1) A hard error occurred in the low level disk I/O layer
/// FR_INT_ERR: int              # (2) Assertion failed
/// FR_NOT_READY: int            # (3) The physical drive cannot work
/// FR_NO_FILE: int              # (4) Could not find the file
/// FR_NO_PATH: int              # (5) Could not find the path
/// FR_INVALID_NAME: int         # (6) The path name format is invalid
/// FR_DENIED: int               # (7) Access denied due to prohibited access or directory full
/// FR_EXIST: int                # (8) Access denied due to prohibited access
/// FR_INVALID_OBJECT: int       # (9) The file/directory object is invalid
/// FR_WRITE_PROTECTED: int      # (10) The physical drive is write protected
/// FR_INVALID_DRIVE: int        # (11) The logical drive number is invalid
/// FR_NOT_ENABLED: int          # (12) The volume has no work area
/// FR_NO_FILESYSTEM: int        # (13) There is no valid FAT volume
/// FR_MKFS_ABORTED: int         # (14) The f_mkfs() aborted due to any problem
/// FR_TIMEOUT: int              # (15) Could not get a grant to access the volume within defined period
/// FR_LOCKED: int               # (16) The operation is rejected according to the file sharing policy
/// FR_NOT_ENOUGH_CORE: int      # (17) LFN working buffer could not be allocated
/// FR_TOO_MANY_OPEN_FILES: int  # (18) Number of open files > FF_FS_LOCK
/// FR_INVALID_PARAMETER: int    # (19) Given parameter is invalid
#define FR_NO_SPACE 64
/// # nonstandard value:
/// FR_NO_SPACE: int             # (64) No space left on device
// clang-format on

static FATFS fs_instance;

bool _fatfs_instance_is_mounted() { return fs_instance.fs_type != 0; }
void _fatfs_unmount_instance() { fs_instance.fs_type = 0; }

/// class FatFSError(OSError):
///     pass
MP_DEFINE_EXCEPTION(FatFSError, OSError)
/// class NotMounted(FatFSError):
///     pass
MP_DEFINE_EXCEPTION(NotMounted, FatFSError)
/// class NoFilesystem(FatFSError):
///     pass
MP_DEFINE_EXCEPTION(NoFilesystem, FatFSError)

// to avoid collisions with POSIX errno values, we add 0xFF to FR_* error codes
#define FATFS_ERROR_CODE(n) (n + 0xFF)
#define FATFS_ROM_INT(n) MP_ROM_INT(FATFS_ERROR_CODE(n))

#define FATFS_RAISE(exc_type, num)                                          \
  {                                                                         \
    nlr_raise(mp_obj_new_exception_arg1(                                    \
        &mp_type_##exc_type, MP_OBJ_NEW_SMALL_INT(FATFS_ERROR_CODE(num)))); \
  }

#define FATFS_ONLY_MOUNTED                   \
  {                                          \
    if (!_fatfs_instance_is_mounted()) {     \
      FATFS_RAISE(NotMounted, FR_NOT_READY); \
    }                                        \
  }

DSTATUS disk_initialize(BYTE pdrv) { return disk_status(pdrv); }

DSTATUS disk_status(BYTE pdrv) {
  return (sectrue == sdcard_is_present()) ? 0 : (STA_NOINIT | STA_NODISK);
}

DRESULT disk_read(BYTE pdrv, BYTE *buff, LBA_t sector, UINT count) {
  (void)pdrv;
  if (sectrue == sdcard_read_blocks((uint32_t *)buff, sector, count)) {
    return RES_OK;
  } else {
    return RES_ERROR;
  }
}

DRESULT disk_write(BYTE pdrv, const BYTE *buff, LBA_t sector, UINT count) {
  (void)pdrv;
  if (sectrue == sdcard_write_blocks((const uint32_t *)buff, sector, count)) {
    return RES_OK;
  } else {
    return RES_ERROR;
  }
}

DRESULT disk_ioctl(BYTE pdrv, BYTE cmd, void *buff) {
  (void)pdrv;
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
    default:
      return RES_PARERR;
  }
}

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

/// def __enter__(self) -> FatFSFile:
///     """
///     Return an open file object
///     """

/// from types import TracebackType
/// def __exit__(
///     self, type: Optional[Type[BaseException]],
///     value: Optional[BaseException],
///     traceback: Optional[TracebackType],
/// ) -> None:
///     """
///     Close an open file object
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile___exit__(size_t n_args,
                                                const mp_obj_t *args) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(args[0]);
  FRESULT res = f_close(&(o->fp));
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
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
    FATFS_RAISE(FatFSError, res);
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
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(data, &buf, MP_BUFFER_WRITE);
  UINT read = 0;
  FRESULT res = f_read(&(o->fp), buf.buf, buf.len, &read);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_obj_new_int_from_uint(read);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_FatFSFile_read_obj,
                                 mod_trezorio_FatFSFile_read);

/// def write(self, data: Union[bytes, bytearray]) -> int:
///     """
///     Write data to the file
///     """
STATIC mp_obj_t mod_trezorio_FatFSFile_write(mp_obj_t self, mp_obj_t data) {
  mp_obj_FatFSFile_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
  UINT written = 0;
  FRESULT res = f_write(&(o->fp), buf.buf, buf.len, &written);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  if (written != buf.len) {
    /* no space left on device or free clusters recorded in FSInfo fell to 0 */
    FATFS_RAISE(FatFSError, FR_NO_SPACE);
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
    FATFS_RAISE(FatFSError, res);
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
    FATFS_RAISE(FatFSError, res);
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
    FATFS_RAISE(FatFSError, res);
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

/// class FatFSDir(Iterator[Tuple[int, str, str]]):
///     """
///     Class encapsulating directory
///     """
typedef struct _mp_obj_FatFSDir_t {
  mp_obj_base_t base;
  DIR dp;
} mp_obj_FatFSDir_t;

/// def __next__(self) -> Tuple[int, str, str]:
///     """
///     Read an entry in the directory
///     """
STATIC mp_obj_t mod_trezorio_FatFSDir_iternext(mp_obj_t self) {
  mp_obj_FatFSDir_t *o = MP_OBJ_TO_PTR(self);
  FILINFO info = {0};
  FRESULT res = f_readdir(&(o->dp), &info);
  if (res != FR_OK) {
    f_closedir(&(o->dp));
    FATFS_RAISE(FatFSError, res);
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

/// mock:global

/// def open(path: str, flags: str) -> FatFSFile:
///     """
///     Open or create a file
///     """
STATIC mp_obj_t mod_trezorio_fatfs_open(mp_obj_t path, mp_obj_t flags) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _path = {0}, _flags = {0};
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
  FIL fp = {0};
  FRESULT res = f_open(&fp, _path.buf, mode);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  mp_obj_FatFSFile_t *f = m_new_obj(mp_obj_FatFSFile_t);
  f->base.type = &mod_trezorio_FatFSFile_type;
  f->fp = fp;
  return f;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_fatfs_open_obj,
                                 mod_trezorio_fatfs_open);

/// def listdir(path: str) -> FatFSDir:
///     """
///     List a directory (return generator)
///     """
STATIC mp_obj_t mod_trezorio_fatfs_listdir(mp_obj_t path) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _path = {0};
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  DIR dp = {0};
  FRESULT res = f_opendir(&dp, _path.buf);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  mp_obj_FatFSDir_t *d = m_new_obj(mp_obj_FatFSDir_t);
  d->base.type = &mod_trezorio_FatFSDir_type;
  d->dp = dp;
  return d;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_fatfs_listdir_obj,
                                 mod_trezorio_fatfs_listdir);

/// def mkdir(path: str, exist_ok: bool=False) -> None:
///     """
///     Create a sub directory
///     """
STATIC mp_obj_t mod_trezorio_fatfs_mkdir(size_t n_args, const mp_obj_t *args) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t path = {0};
  mp_get_buffer_raise(args[0], &path, MP_BUFFER_READ);
  FRESULT res = f_mkdir(path.buf);
  // directory exists and exist_ok is True, return without failure
  if (res == FR_EXIST && n_args > 1 && args[1] == mp_const_true) {
    return mp_const_none;
  }
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorio_fatfs_mkdir_obj, 1, 2,
                                           mod_trezorio_fatfs_mkdir);

/// def unlink(path: str) -> None:
///     """
///     Delete an existing file or directory
///     """
STATIC mp_obj_t mod_trezorio_fatfs_unlink(mp_obj_t path) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _path = {0};
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  FRESULT res = f_unlink(_path.buf);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_fatfs_unlink_obj,
                                 mod_trezorio_fatfs_unlink);

/// def stat(path: str) -> Tuple[int, str, str]:
///     """
///     Get file status
///     """
STATIC mp_obj_t mod_trezorio_fatfs_stat(mp_obj_t path) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _path = {0};
  mp_get_buffer_raise(path, &_path, MP_BUFFER_READ);
  FILINFO info = {0};
  FRESULT res = f_stat(_path.buf, &info);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return filinfo_to_tuple(&info);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_fatfs_stat_obj,
                                 mod_trezorio_fatfs_stat);

/// def rename(oldpath: str, newpath: str) -> None:
///     """
///     Rename/Move a file or directory
///     """
STATIC mp_obj_t mod_trezorio_fatfs_rename(mp_obj_t oldpath, mp_obj_t newpath) {
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _oldpath = {0}, _newpath = {0};
  mp_get_buffer_raise(oldpath, &_oldpath, MP_BUFFER_READ);
  mp_get_buffer_raise(newpath, &_newpath, MP_BUFFER_READ);
  FRESULT res = f_rename(_oldpath.buf, _newpath.buf);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_fatfs_rename_obj,
                                 mod_trezorio_fatfs_rename);

/// def mount() -> None:
///     """
///     Mount the SD card filesystem.
///     """
STATIC mp_obj_t mod_trezorio_fatfs_mount() {
  FRESULT res = f_mount(&fs_instance, "", 1);
  if (res != FR_OK) {
    if (res == FR_NO_FILESYSTEM) {
      FATFS_RAISE(NoFilesystem, FR_NO_FILESYSTEM);
    } else {
      FATFS_RAISE(FatFSError, res);
    }
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_fatfs_mount_obj,
                                 mod_trezorio_fatfs_mount);

/// def unmount() -> None:
///     """
///     Unmount the SD card filesystem.
///     """
STATIC mp_obj_t mod_trezorio_fatfs_unmount() {
  _fatfs_unmount_instance();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_fatfs_unmount_obj,
                                 mod_trezorio_fatfs_unmount);

/// def is_mounted() -> bool:
///    """
///    Check if the filesystem is mounted.
///    """
STATIC mp_obj_t mod_trezorio_fatfs_is_mounted() {
  return mp_obj_new_bool(_fatfs_instance_is_mounted());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_fatfs_is_mounted_obj,
                                 mod_trezorio_fatfs_is_mounted);

/// def mkfs() -> None:
///     """
///     Create a FAT volume on the SD card,
///     """
STATIC mp_obj_t mod_trezorio_fatfs_mkfs() {
  if (_fatfs_instance_is_mounted()) {
    FATFS_RAISE(FatFSError, FR_LOCKED);
  }
  MKFS_PARM params = {FM_FAT32, 0, 0, 0, 0};
  uint8_t working_buf[FF_MAX_SS] = {0};
  FRESULT res = f_mkfs("", &params, working_buf, sizeof(working_buf));
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_fatfs_mkfs_obj,
                                 mod_trezorio_fatfs_mkfs);

/// def setlabel(label: str) -> None:
///     """
///     Set volume label
///     """
STATIC mp_obj_t mod_trezorio_fatfs_setlabel(mp_obj_t label) {
  /* setlabel is marked as only-mounted, because "mounting" in ff.c terms means
  having parsed the FAT table, which is of course a prerequisite for setting
  label. */
  FATFS_ONLY_MOUNTED;
  mp_buffer_info_t _label = {0};
  mp_get_buffer_raise(label, &_label, MP_BUFFER_READ);
  FRESULT res = f_setlabel(_label.buf);
  if (res != FR_OK) {
    FATFS_RAISE(FatFSError, res);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_fatfs_setlabel_obj,
                                 mod_trezorio_fatfs_setlabel);

STATIC const mp_rom_map_elem_t mod_trezorio_fatfs_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_fatfs)},
    {MP_ROM_QSTR(MP_QSTR_FatFSFile), MP_ROM_PTR(&mod_trezorio_FatFSFile_type)},
    {MP_ROM_QSTR(MP_QSTR_FatFSDir), MP_ROM_PTR(&mod_trezorio_FatFSDir_type)},
    {MP_ROM_QSTR(MP_QSTR_FatFSError), MP_ROM_PTR(&mp_type_FatFSError)},
    {MP_ROM_QSTR(MP_QSTR_NotMounted), MP_ROM_PTR(&mp_type_NotMounted)},
    {MP_ROM_QSTR(MP_QSTR_NoFilesystem), MP_ROM_PTR(&mp_type_NoFilesystem)},

    {MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&mod_trezorio_fatfs_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_listdir), MP_ROM_PTR(&mod_trezorio_fatfs_listdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_mkdir), MP_ROM_PTR(&mod_trezorio_fatfs_mkdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_unlink), MP_ROM_PTR(&mod_trezorio_fatfs_unlink_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&mod_trezorio_fatfs_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_stat), MP_ROM_PTR(&mod_trezorio_fatfs_stat_obj)},
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&mod_trezorio_fatfs_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_unmount), MP_ROM_PTR(&mod_trezorio_fatfs_unmount_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_mounted),
     MP_ROM_PTR(&mod_trezorio_fatfs_is_mounted_obj)},
    {MP_ROM_QSTR(MP_QSTR_mkfs), MP_ROM_PTR(&mod_trezorio_fatfs_mkfs_obj)},
    {MP_ROM_QSTR(MP_QSTR_setlabel),
     MP_ROM_PTR(&mod_trezorio_fatfs_setlabel_obj)},

    {MP_ROM_QSTR(MP_QSTR_FR_OK), FATFS_ROM_INT(FR_OK)},
    {MP_ROM_QSTR(MP_QSTR_FR_DISK_ERR), FATFS_ROM_INT(FR_DISK_ERR)},
    {MP_ROM_QSTR(MP_QSTR_FR_INT_ERR), FATFS_ROM_INT(FR_INT_ERR)},
    {MP_ROM_QSTR(MP_QSTR_FR_NOT_READY), FATFS_ROM_INT(FR_NOT_READY)},
    {MP_ROM_QSTR(MP_QSTR_FR_NO_FILE), FATFS_ROM_INT(FR_NO_FILE)},
    {MP_ROM_QSTR(MP_QSTR_FR_NO_PATH), FATFS_ROM_INT(FR_NO_PATH)},
    {MP_ROM_QSTR(MP_QSTR_FR_INVALID_NAME), FATFS_ROM_INT(FR_INVALID_NAME)},
    {MP_ROM_QSTR(MP_QSTR_FR_DENIED), FATFS_ROM_INT(FR_DENIED)},
    {MP_ROM_QSTR(MP_QSTR_FR_EXIST), FATFS_ROM_INT(FR_EXIST)},
    {MP_ROM_QSTR(MP_QSTR_FR_INVALID_OBJECT), FATFS_ROM_INT(FR_INVALID_OBJECT)},
    {MP_ROM_QSTR(MP_QSTR_FR_WRITE_PROTECTED),
     FATFS_ROM_INT(FR_WRITE_PROTECTED)},
    {MP_ROM_QSTR(MP_QSTR_FR_INVALID_DRIVE), FATFS_ROM_INT(FR_INVALID_DRIVE)},
    {MP_ROM_QSTR(MP_QSTR_FR_NOT_ENABLED), FATFS_ROM_INT(FR_NOT_ENABLED)},
    {MP_ROM_QSTR(MP_QSTR_FR_NO_FILESYSTEM), FATFS_ROM_INT(FR_NO_FILESYSTEM)},
    {MP_ROM_QSTR(MP_QSTR_FR_MKFS_ABORTED), FATFS_ROM_INT(FR_MKFS_ABORTED)},
    {MP_ROM_QSTR(MP_QSTR_FR_TIMEOUT), FATFS_ROM_INT(FR_TIMEOUT)},
    {MP_ROM_QSTR(MP_QSTR_FR_LOCKED), FATFS_ROM_INT(FR_LOCKED)},
    {MP_ROM_QSTR(MP_QSTR_FR_NOT_ENOUGH_CORE),
     FATFS_ROM_INT(FR_NOT_ENOUGH_CORE)},
    {MP_ROM_QSTR(MP_QSTR_FR_TOO_MANY_OPEN_FILES),
     FATFS_ROM_INT(FR_TOO_MANY_OPEN_FILES)},
    {MP_ROM_QSTR(MP_QSTR_FR_INVALID_PARAMETER),
     FATFS_ROM_INT(FR_INVALID_PARAMETER)},
    {MP_ROM_QSTR(MP_QSTR_FR_NO_SPACE), FATFS_ROM_INT(FR_NO_SPACE)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_fatfs_globals,
                            mod_trezorio_fatfs_globals_table);

STATIC const mp_obj_module_t mod_trezorio_fatfs_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_fatfs_globals,
};
