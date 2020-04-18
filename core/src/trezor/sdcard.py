from trezorio import fatfs, sdcard

if False:
    from typing import Any, Callable, Optional, TypeVar

    T = TypeVar("T", bound=Callable)


class FilesystemWrapper:
    _INSTANCE = None  # type: Optional[FilesystemWrapper]

    def __init__(self, mounted: bool) -> None:
        self.mounted = mounted
        self.counter = 0

    @classmethod
    def get_instance(cls, mounted: bool = True) -> "FilesystemWrapper":
        if cls._INSTANCE is None:
            cls._INSTANCE = cls(mounted=mounted)
        if cls._INSTANCE.mounted is not mounted:
            raise RuntimeError  # cannot request mounted and non-mounted instance at the same time
        return cls._INSTANCE

    def _deinit_instance(self) -> None:
        fatfs.unmount()
        sdcard.power_off()
        FilesystemWrapper._INSTANCE = None

    def __enter__(self) -> None:
        try:
            if self.counter <= 0:
                self.counter = 0
                sdcard.power_on()
                if self.mounted:
                    fatfs.mount()
            self.counter += 1
        except Exception:
            self._deinit_instance()
            raise

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        self.counter -= 1
        if self.counter <= 0:
            self.counter = 0
            self._deinit_instance()


def filesystem(mounted: bool = True) -> FilesystemWrapper:
    return FilesystemWrapper.get_instance(mounted=mounted)


def with_filesystem(func: T) -> T:
    def wrapped_func(*args, **kwargs) -> Any:  # type: ignore
        with filesystem():
            return func(*args, **kwargs)

    return wrapped_func  # type: ignore


is_present = sdcard.is_present
capacity = sdcard.capacity
