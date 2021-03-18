from typing import *
FR_OK: int                   # (0) Succeeded
FR_DISK_ERR: int             # (1) A hard error occurred in the low level disk I/O layer
FR_INT_ERR: int              # (2) Assertion failed
FR_NOT_READY: int            # (3) The physical drive cannot work
FR_NO_FILE: int              # (4) Could not find the file
FR_NO_PATH: int              # (5) Could not find the path
FR_INVALID_NAME: int         # (6) The path name format is invalid
FR_DENIED: int               # (7) Access denied due to prohibited access or directory full
FR_EXIST: int                # (8) Access denied due to prohibited access
FR_INVALID_OBJECT: int       # (9) The file/directory object is invalid
FR_WRITE_PROTECTED: int      # (10) The physical drive is write protected
FR_INVALID_DRIVE: int        # (11) The logical drive number is invalid
FR_NOT_ENABLED: int          # (12) The volume has no work area
FR_NO_FILESYSTEM: int        # (13) There is no valid FAT volume
FR_MKFS_ABORTED: int         # (14) The f_mkfs() aborted due to any problem
FR_TIMEOUT: int              # (15) Could not get a grant to access the volume within defined period
FR_LOCKED: int               # (16) The operation is rejected according to the file sharing policy
FR_NOT_ENOUGH_CORE: int      # (17) LFN working buffer could not be allocated
FR_TOO_MANY_OPEN_FILES: int  # (18) Number of open files > FF_FS_LOCK
FR_INVALID_PARAMETER: int    # (19) Given parameter is invalid
# nonstandard value:
FR_NO_SPACE: int             # (64) No space left on device


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFSError(OSError):
    pass


# extmod/modtrezorio/modtrezorio-fatfs.h
class NotMounted(FatFSError):
    pass


# extmod/modtrezorio/modtrezorio-fatfs.h
class NoFilesystem(FatFSError):
    pass


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFSFile:
    """
    Class encapsulating file
    """

    def __enter__(self) -> FatFSFile:
        """
        Return an open file object
        """
    from types import TracebackType

    def __exit__(
        self, type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Close an open file object
        """

    def close(self) -> None:
        """
        Close an open file object
        """

    def read(self, data: bytearray) -> int:
        """
        Read data from the file
        """

    def write(self, data: bytes | bytearray) -> int:
        """
        Write data to the file
        """

    def seek(self, offset: int) -> None:
        """
        Move file pointer of the file object
        """

    def truncate(self) -> None:
        """
        Truncate the file
        """

    def sync(self) -> None:
        """
        Flush cached data of the writing file
        """


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFSDir(Iterator[tuple[int, str, str]]):
    """
    Class encapsulating directory
    """

    def __next__(self) -> tuple[int, str, str]:
        """
        Read an entry in the directory
        """


# extmod/modtrezorio/modtrezorio-fatfs.h
def open(path: str, flags: str) -> FatFSFile:
    """
    Open or create a file
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def listdir(path: str) -> FatFSDir:
    """
    List a directory (return generator)
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def mkdir(path: str, exist_ok: bool=False) -> None:
    """
    Create a sub directory
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def unlink(path: str) -> None:
    """
    Delete an existing file or directory
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def stat(path: str) -> tuple[int, str, str]:
    """
    Get file status
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def rename(oldpath: str, newpath: str) -> None:
    """
    Rename/Move a file or directory
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def mount() -> None:
    """
    Mount the SD card filesystem.
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def unmount() -> None:
    """
    Unmount the SD card filesystem.
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def is_mounted() -> bool:
   """
   Check if the filesystem is mounted.
   """


# extmod/modtrezorio/modtrezorio-fatfs.h
def mkfs() -> None:
    """
    Create a FAT volume on the SD card,
    """


# extmod/modtrezorio/modtrezorio-fatfs.h
def setlabel(label: str) -> None:
    """
    Set volume label
    """
