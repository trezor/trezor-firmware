from trezorio import FatFS, sdcard

if False:
    from typing import Any, Optional


class FilesystemWrapper:
    _INSTANCE = None  # type: Optional[FilesystemWrapper]

    def __init__(self, mounted: bool = True) -> None:
        self.fs = FatFS()
        self.mounted = mounted
        self.counter = 0

    @classmethod
    def get_instance(cls, mounted: bool = True) -> "FilesystemWrapper":
        if cls._INSTANCE is None:
            cls._INSTANCE = cls(mounted=mounted)
        if cls._INSTANCE.mounted is not mounted:
            raise RuntimeError  # cannot request mounted and non-mounted instance at the same time
        return cls._INSTANCE

    def __enter__(self) -> "FatFS":
        if self.counter <= 0:
            self.counter = 0
            sdcard.power_on()
            if self.mounted:
                self.fs.mount()
        self.counter += 1
        return self.fs

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        self.counter -= 1
        if self.counter <= 0:
            self.counter = 0
            if self.mounted:
                self.fs.unmount()
            sdcard.power_off()
            FilesystemWrapper._INSTANCE = None


def get_filesystem(mounted: bool = True) -> FilesystemWrapper:
    return FilesystemWrapper.get_instance(mounted=mounted)


is_present = sdcard.is_present
