from typing import *


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
        self, type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
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

    def write(self, data: Union[bytes, bytearray]) -> int:
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
class FatFSDir(Iterator[Tuple[int, str, str]]):
    """
    Class encapsulating directory
    """

    def __next__(self) -> Tuple[int, str, str]:
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
def stat(path: str) -> Tuple[int, str, str]:
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
