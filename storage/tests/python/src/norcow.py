from struct import pack, unpack

from . import consts
from .pin_log_bitwise import PinLogBitwise
from .pin_log_blockwise import PinLogBlockwise


def align_int(i: int, align: int):
    return (-i) % align


def align_int_add(i: int, align: int):
    return i + align_int(i, align)


def align_data(data, align: int, padding: bytes = b"\x00"):
    return data + padding * align_int(len(data), align)


class Norcow:
    def __init__(self):
        self.sectors = None
        self.active_sector = 0

    def init(self):
        if self.sectors:
            for sector in range(consts.NORCOW_SECTOR_COUNT):
                if self.sectors[sector][: len(self.magic)] == self.magic:
                    self.active_sector = sector
                    self.active_offset = self.find_free_offset()
                    break
        else:
            self.wipe()

    def find_free_offset(self):
        offset = len(self.magic)
        while True:
            try:
                k, v = self._read_item(offset)
            except ValueError:
                break
            offset = offset + self._norcow_item_length(len(v))
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
        if found_value is not None:
            if self._is_updatable(key, val):
                self._write(pos, key, val)
                return
            else:
                self._delete_old(pos, found_value)

        if (
            self.active_offset
            + align_int_add(self.item_prefix_len + len(val), self.block_size)
            > consts.NORCOW_SECTOR_SIZE
        ):
            self._compact()

        if (
            self.active_offset
            + align_int_add(self.item_prefix_len + len(val), self.block_size)
            > consts.NORCOW_SECTOR_SIZE
        ):
            raise RuntimeError("Norcow: no space left")

        self._append(key, val)

    def delete(self, key: int):
        if key == consts.NORCOW_KEY_FREE:
            raise RuntimeError("Norcow: key 0xFFFF is not allowed")

        found_value, pos = self._find_item(key)
        if found_value is None:
            return False
        self._delete_old(pos, found_value)
        return True

    def replace(self, key: int, new_value: bytes) -> bool:
        old_value, offset = self._find_item(key)
        if old_value is None:
            raise RuntimeError("Norcow: key not found")
        if len(old_value) != len(new_value):
            raise RuntimeError(
                "Norcow: replace works only with items of the same length"
            )
        self._write(offset, key, new_value)

    def _delete_old(self, pos: int, value: bytes):
        wiped_data = b"\x00" * len(value)
        self._write(pos, 0x0000, wiped_data)

    def _append(self, key: int, value: bytes):
        self.active_offset += self._write(self.active_offset, key, value)

    def _find_item(self, key: int) -> (bytes, int):
        offset = len(self.magic)
        value = None
        pos = offset
        while True:
            try:
                k, v = self._read_item(offset)
                if k == key:
                    value = v
                    pos = offset
            except ValueError:
                break
            offset = offset + self._norcow_item_length(len(v))
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
            offset = offset + self._norcow_item_length(len(v))
        return keys

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
            offset = offset + self._norcow_item_length(len(v))
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


class NorcowBitwise(Norcow):
    def __init__(self):
        super().__init__()
        self.block_size = consts.WORD_SIZE
        self.magic = consts.NORCOW_MAGIC_AND_VERSION
        self.item_prefix_len = 4
        self.lib_name = "libtrezor-storage.so"

    def get_pin_log(self):
        return PinLogBitwise(self)

    def get_lib_name(self):
        return self.lib_name

    def is_byte_access(self):
        return True

    def _is_updatable(self, key: int, new: bytes) -> bool:
        """
        Item is updatable if the new value is the same or
        it changes 1 to 0 only (the flash memory does not
        allow to flip 0 to 1 unless you wipe it).
        """

        old, _ = self._find_item(key)
        if old is None:
            return False
        if len(old) != len(new):
            return False
        for a, b in zip(old, new):
            if a & b != b:
                return False
        return True

    def _write(self, pos: int, key: int, new_value: bytes) -> int:
        data = pack("<HH", key, len(new_value)) + align_data(new_value, self.block_size)
        if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
            raise RuntimeError("Norcow: item too big")
        self.sectors[self.active_sector][pos : pos + len(data)] = data
        return len(data)

    def _norcow_item_length(self, data_len: int) -> int:
        # APP_ID, KEY_ID, LENGTH, DATA, ALIGNMENT
        return self.item_prefix_len + data_len + align_int(data_len, self.block_size)

    def _read_item(self, offset: int) -> (int, bytes):
        if offset >= consts.NORCOW_SECTOR_SIZE:
            raise ValueError("Norcow: no data on this offset")

        key, length = unpack(
            "<HH", self.sectors[self.active_sector][offset : offset + 4]
        )
        if key == consts.NORCOW_KEY_FREE:
            raise ValueError("Norcow: no data on this offset")
        value = self.sectors[self.active_sector][offset + 4 : offset + 4 + length]

        return key, value


class NorcowBlockwise(Norcow):
    def __init__(self):
        super().__init__()
        self.block_size = 4 * consts.WORD_SIZE
        self.small_item_size = 12
        self.magic = consts.NORCOW_MAGIC_AND_VERSION + bytes([0x00] * 8)
        self.item_prefix_len = 4 * consts.WORD_SIZE + 1
        self.lib_name = "libtrezor-storage-qw.so"

    def get_pin_log(self):
        return PinLogBlockwise(self)

    def get_lib_name(self):
        return self.lib_name

    def is_byte_access(self):
        return False

    def _is_updatable(self, key: int, new: bytes) -> bool:
        """
        The item is only deemed updatable if the new value is the same as the old one.
        """
        old, _ = self._find_item(key)
        if old is None:
            return False
        if len(old) != len(new):
            return False
        for a, b in zip(old, new):
            if a != b:
                return False
        return True

    def _write(self, pos: int, key: int, new_value: bytes) -> int:

        if len(new_value) <= self.small_item_size:
            if key == 0:
                self.sectors[self.active_sector][pos : pos + self.block_size] = [
                    0
                ] * self.block_size
            else:
                if len(new_value) == 0:
                    data = pack("<HH", key, len(new_value)) + bytes(
                        [0] * self.small_item_size
                    )
                else:
                    data = pack("<HH", key, len(new_value)) + align_data(
                        new_value, self.small_item_size
                    )
                if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
                    raise RuntimeError("Norcow: item too big")
                self.sectors[self.active_sector][pos : pos + self.block_size] = data
                return len(data)
        else:
            if key == 0:
                old_key, _ = unpack(
                    "<HH", self.sectors[self.active_sector][pos : pos + 4]
                )
                data = align_data(
                    pack("<HH", old_key, len(new_value)), self.block_size, b"\x00"
                )
                data += align_data(new_value + bytes([0]), self.block_size, b"\x00")
            else:
                data = align_data(
                    pack("<HH", key, len(new_value)), self.block_size, b"\x00"
                )
                data += align_data(new_value + bytes([0xFF]), self.block_size, b"\xFF")

            if pos + len(data) > consts.NORCOW_SECTOR_SIZE:
                raise RuntimeError("Norcow: item too big")
            self.sectors[self.active_sector][pos : pos + len(data)] = data
            return len(data)

    def _norcow_item_length(self, data_len: int) -> int:
        if data_len <= 12:
            return self.block_size
        else:
            # APP_ID, KEY_ID, LENGTH, DATA, ALIGNMENT
            return (
                self.block_size
                + 1
                + data_len
                + align_int(1 + data_len, self.block_size)
            )

    def _read_item(self, offset: int) -> (int, bytes):
        if offset >= consts.NORCOW_SECTOR_SIZE:
            raise ValueError("Norcow: no data on this offset")

        key, length = unpack(
            "<HH", self.sectors[self.active_sector][offset : offset + 4]
        )

        if length <= self.small_item_size:
            if key == consts.NORCOW_KEY_FREE:
                raise ValueError("Norcow: no data on this offset")
            value = self.sectors[self.active_sector][offset + 4 : offset + 4 + length]
        else:
            if key == consts.NORCOW_KEY_FREE:
                raise ValueError("Norcow: no data on this offset")
            deleted = self.sectors[self.active_sector][
                offset + self.block_size + length
            ]
            value = self.sectors[self.active_sector][
                offset + self.block_size : offset + self.block_size + length
            ]
            if deleted == 0:
                key = 0
            else:
                if key == consts.NORCOW_KEY_FREE:
                    raise ValueError("Norcow: no data on this offset")

        return key, value


NC_CLASSES = [NorcowBitwise, NorcowBlockwise]
