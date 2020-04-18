import ctypes as c
import os

EXTERNAL_SALT_LEN = 32
sectrue = -1431655766  # 0xAAAAAAAAA
fname = os.path.join(os.path.dirname(__file__), "libtrezor-storage.so")


class Storage:
    def __init__(self) -> None:
        self.lib = c.cdll.LoadLibrary(fname)
        self.flash_size = c.cast(self.lib.FLASH_SIZE, c.POINTER(c.c_uint32))[0]
        self.flash_buffer = c.create_string_buffer(self.flash_size)
        c.cast(self.lib.FLASH_BUFFER, c.POINTER(c.c_void_p))[0] = c.addressof(
            self.flash_buffer
        )

    def init(self, salt: bytes) -> None:
        self.lib.storage_init(0, salt, c.c_uint16(len(salt)))

    def wipe(self) -> None:
        self.lib.storage_wipe()

    def unlock(self, pin: int, ext_salt: bytes = None) -> bool:
        if ext_salt is not None and len(ext_salt) != EXTERNAL_SALT_LEN:
            raise ValueError
        return sectrue == self.lib.storage_unlock(c.c_uint32(pin), ext_salt)

    def lock(self) -> None:
        self.lib.storage_lock()

    def has_pin(self) -> bool:
        return sectrue == self.lib.storage_has_pin()

    def get_pin_rem(self) -> int:
        return self.lib.storage_get_pin_rem()

    def change_pin(
        self,
        oldpin: int,
        newpin: int,
        old_ext_salt: bytes = None,
        new_ext_salt: bytes = None,
    ) -> bool:
        if old_ext_salt is not None and len(old_ext_salt) != EXTERNAL_SALT_LEN:
            raise ValueError
        if new_ext_salt is not None and len(new_ext_salt) != EXTERNAL_SALT_LEN:
            raise ValueError
        return sectrue == self.lib.storage_change_pin(
            c.c_uint32(oldpin), c.c_uint32(newpin), old_ext_salt, new_ext_salt
        )

    def get(self, key: int) -> bytes:
        val_len = c.c_uint16()
        if sectrue != self.lib.storage_get(c.c_uint16(key), None, 0, c.byref(val_len)):
            raise RuntimeError("Failed to find key in storage.")
        s = c.create_string_buffer(val_len.value)
        if sectrue != self.lib.storage_get(
            c.c_uint16(key), s, val_len, c.byref(val_len)
        ):
            raise RuntimeError("Failed to get value from storage.")
        return s.raw

    def set(self, key: int, val: bytes) -> None:
        if sectrue != self.lib.storage_set(c.c_uint16(key), val, c.c_uint16(len(val))):
            raise RuntimeError("Failed to set value in storage.")

    def set_counter(self, key: int, count: int) -> bool:
        return sectrue == self.lib.storage_set_counter(
            c.c_uint16(key), c.c_uint32(count)
        )

    def next_counter(self, key: int) -> int:
        count = c.c_uint32()
        if sectrue == self.lib.storage_next_counter(c.c_uint16(key), c.byref(count)):
            return count.value
        else:
            return None

    def delete(self, key: int) -> bool:
        return sectrue == self.lib.storage_delete(c.c_uint16(key))

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
        self.flash_buffer.value = buf
