import ctypes as c
import os

sectrue = -1431655766  # 0xAAAAAAAAA
fname = os.path.join(os.path.dirname(__file__), "libtrezor-storage0.so")


class Storage:
    def __init__(self) -> None:
        self.lib = c.cdll.LoadLibrary(fname)
        self.flash_size = c.cast(self.lib.FLASH_SIZE, c.POINTER(c.c_uint32))[0]
        self.flash_buffer = c.create_string_buffer(self.flash_size)
        c.cast(self.lib.FLASH_BUFFER, c.POINTER(c.c_void_p))[0] = c.addressof(
            self.flash_buffer
        )

    def init(self) -> None:
        self.lib.storage_init(0)

    def wipe(self) -> None:
        self.lib.storage_wipe()

    def check_pin(self, pin: int) -> bool:
        return sectrue == self.lib.storage_check_pin(c.c_uint32(pin))

    def unlock(self, pin: int) -> bool:
        return sectrue == self.lib.storage_unlock(c.c_uint32(pin))

    def has_pin(self) -> bool:
        return sectrue == self.lib.storage_has_pin()

    def change_pin(self, oldpin: int, newpin: int) -> bool:
        return sectrue == self.lib.storage_change_pin(
            c.c_uint32(oldpin), c.c_uint32(newpin)
        )

    def get(self, key: int) -> bytes:
        val_ptr = c.c_void_p()
        val_len = c.c_uint16()
        if sectrue != self.lib.storage_get(
            c.c_uint16(key), c.byref(val_ptr), c.byref(val_len)
        ):
            raise RuntimeError("Failed to find key in storage.")
        return c.string_at(val_ptr, size=val_len.value)

    def set(self, key: int, val: bytes) -> None:
        if sectrue != self.lib.storage_set(c.c_uint16(key), val, c.c_uint16(len(val))):
            raise RuntimeError("Failed to set value in storage.")

    def _dump(self) -> bytes:
        # return just sectors 4 and 16 of the whole flash
        return [
            self.flash_buffer[0x010000 : 0x010000 + 0x10000],
            self.flash_buffer[0x110000 : 0x110000 + 0x10000],
        ]

    def _get_flash_buffer(self) -> bytes:
        return bytes(self.flash_buffer)

    def _set_flash_buffer(self, buf: bytes) -> None:
        if len(buf) != self.flash_size:
            raise RuntimeError("Failed to set flash buffer due to length mismatch.")
        self.flash_buffer = buf
