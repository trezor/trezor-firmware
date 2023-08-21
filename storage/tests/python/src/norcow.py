import sys
from struct import pack

from . import consts


def align_int(i: int, align: int):
    return (align - i) % align


def align_data(data, align: int):
    return data + b"\x00" * align_int(len(data), align)


class Norcow:
    def __init__(self, flash_byte_access=True):
        self.sectors = None
        self.active_sector = 0
        self.flash_byte_access = flash_byte_access
        if flash_byte_access:
            self.word_size = consts.WORD_SIZE
            self.magic = consts.NORCOW_MAGIC_AND_VERSION
            self.item_prefix_len = 4
        else:
            self.word_size = 4 * consts.WORD_SIZE
            self.magic = consts.NORCOW_MAGIC_AND_VERSION + bytes([0xFF] * 8)
            self.item_prefix_len = 2 * 4 * consts.WORD_SIZE

    def init(self):
        if self.sectors:
            for sector in range(consts.NORCOW_SECTOR_COUNT):
                if self.sectors[sector][: len(self.magic)] == self.magic:
                    self.active_sector = sector
                    self.active_offset = self.find_free_offset()
                    break
        else:
            self.wipe()

    def is_byte_access(self):
        return self.flash_byte_access

    def find_free_offset(self):
        offset = len(self.magic)
        while True:
            try:
                k, v = self._read_item(offset)
            except ValueError:
                break
            offset = offset + self._norcow_item_length(v)
        return offset

    def wipe(self, sector: int = None):
        if sector is None:
            sector = self.active_sector

        self.sectors = [
            bytearray([0xFF] * consts.NORCOW_SECTOR_SIZE)
            for _ in range(consts.NORCOW_SECTOR_COUNT)
        ]
        self.sectors[sector][: len(self.magic)] = self.magic
        self.active_sector = sector
        self.active_offset = len(self.magic)

    def get(self, key: int) -> bytes:
        value, _ = self._find_item(key)
        return value

    def set(self, key: int, val: bytes):
        if key == consts.NORCOW_KEY_FREE:
            raise RuntimeError("Norcow: key 0xFFFF is not allowed")

        found_value, pos = self._find_item(key)
        if found_value is not False:
            if self._is_updatable(found_value, val):
                self._write(pos, key, val)
                return
            else:
                self._delete_old(pos, found_value)

        if (
            self.active_offset + self.item_prefix_len + len(val)
            > consts.NORCOW_SECTOR_SIZE
        ):
            self._compact()

        self._append(key, val)

    def delete(self, key: int):
        if key == consts.NORCOW_KEY_FREE:
            raise RuntimeError("Norcow: key 0xFFFF is not allowed")

        found_value, pos = self._find_item(key)
        if found_value is False:
            return False
        self._delete_old(pos, found_value)
        return True

    def replace(self, key: int, new_value: bytes) -> bool:
        old_value, offset = self._find_item(key)
        if not old_value:
            raise RuntimeError("Norcow: key not found")
        if len(old_value) != len(new_value):
            raise RuntimeError(
                "Norcow: replace works only with items of the same length"
            )
        self._write(offset, key, new_value)

    def _is_updatable(self, old: bytes, new: bytes) -> bool:
        """
        Item is updatable if the new value is the same or
        it changes 1 to 0 only (the flash memory does not
        allow to flip 0 to 1 unless you wipe it).

        For flash with no byte access, item is updatable if the new value is the same
        """
        if len(old) != len(new):
            return False
        if old == new:
            return True
        if self.flash_byte_access:
            for a, b in zip(old, new):
                if a & b != b:
                    return False
            return True
        else:
            return False

    def _delete_old(self, pos: int, value: bytes):
        wiped_data = b"\x00" * len(value)
        self._write(pos, 0x0000, wiped_data)

    def _append(self, key: int, value: bytes):
        self.active_offset += self._write(self.active_offset, key, value)

    def _write(self, pos: int, key: int, new_value: bytes) -> int:
        if self.flash_byte_access:
            data = pack("<HH", key, len(new_value)) + align_data(
                new_value, self.word_size
            )
            if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
                raise RuntimeError("Norcow: item too big")
            self.sectors[self.active_sector][pos : pos + len(data)] = data
            return len(data)
        else:
            if len(new_value) <= 12:
                if key == 0:
                    self.sectors[self.active_sector][pos : pos + self.word_size] = [
                        0
                    ] * self.word_size
                else:
                    if len(new_value) == 0:
                        data = pack("<HH", len(new_value), key) + bytes([0] * 12)
                    else:
                        data = pack("<HH", len(new_value), key) + align_data(
                            new_value, 12
                        )
                    if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
                        raise RuntimeError("Norcow: item too big")
                    self.sectors[self.active_sector][pos : pos + self.word_size] = data
                    return len(data)
            else:
                data = []
                data += pack("<L", len(new_value))
                data += bytes([0xFF] * 12)
                if key == 0:
                    data += bytes([0] * 16)
                else:
                    data += pack("<L", key)
                    data += bytes([0xFF] * 12)
                data += align_data(new_value, self.word_size)

                if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
                    raise RuntimeError("Norcow: item too big")
                self.sectors[self.active_sector][pos : pos + len(data)] = data
                return len(data)

    def _find_item(self, key: int) -> (bytes, int):
        offset = len(self.magic)
        value = False
        pos = offset
        while True:
            try:
                k, v = self._read_item(offset)
                if k == key:
                    value = v
                    pos = offset
            except ValueError:
                break
            offset = offset + self._norcow_item_length(v)
        return value, pos

    def _get_all_keys(self) -> (bytes, int):
        offset = len(self.magic)
        keys = set()
        while True:
            try:
                k, v = self._read_item(offset)
                keys.add(k)
            except ValueError:
                break
            offset = offset + self._norcow_item_length(v)
        return keys

    def _norcow_item_length(self, data: bytes) -> int:
        if len(data) <= 12 and not self.flash_byte_access:
            return self.word_size
        else:
            # APP_ID, KEY_ID, LENGTH, DATA, ALIGNMENT
            return (
                self.item_prefix_len + len(data) + align_int(len(data), self.word_size)
            )

    def _read_item(self, offset: int) -> (int, bytes):
        if offset >= consts.NORCOW_SECTOR_SIZE:
            raise ValueError("Norcow: no data on this offset")

        if self.flash_byte_access:
            key = self.sectors[self.active_sector][offset : offset + 2]
            key = int.from_bytes(key, sys.byteorder)
            if key == consts.NORCOW_KEY_FREE:
                raise ValueError("Norcow: no data on this offset")
            length = self.sectors[self.active_sector][offset + 2 : offset + 4]
            length = int.from_bytes(length, sys.byteorder)
            value = self.sectors[self.active_sector][offset + 4 : offset + 4 + length]
        else:

            length = self.sectors[self.active_sector][offset : offset + 2]
            length = int.from_bytes(length, sys.byteorder)

            if length <= 12:
                key = self.sectors[self.active_sector][offset + 2 : offset + 4]
                key = int.from_bytes(key, sys.byteorder)
                if key == consts.NORCOW_KEY_FREE:
                    raise ValueError("Norcow: no data on this offset")
                value = self.sectors[self.active_sector][
                    offset + 4 : offset + 4 + length
                ]
            else:
                key = self.sectors[self.active_sector][
                    offset + self.word_size : offset + self.word_size + 2
                ]
                key = int.from_bytes(key, sys.byteorder)
                if key == consts.NORCOW_KEY_FREE:
                    raise ValueError("Norcow: no data on this offset")
                value = self.sectors[self.active_sector][
                    offset + 2 * self.word_size : offset + 2 * self.word_size + length
                ]
        return key, value

    def _compact(self):
        offset = len(self.magic)
        data = list()
        while True:
            try:
                k, v = self._read_item(offset)
                if k != 0x00:
                    data.append((k, v))
            except ValueError:
                break
            offset = offset + self._norcow_item_length(v)
        sector = self.active_sector
        self.wipe((sector + 1) % consts.NORCOW_SECTOR_COUNT)
        for key, value in data:
            self._append(key, value)

    def _set_sectors(self, data):
        if list(map(len, data)) != [
            consts.NORCOW_SECTOR_SIZE,
            consts.NORCOW_SECTOR_SIZE,
        ]:
            raise RuntimeError("Norcow: set_sectors called with invalid data length")
        self.sectors = [bytearray(sector) for sector in data]

    def _dump(self):
        return [bytes(sector) for sector in self.sectors]
