import pytest

from ..src import consts, norcow
from . import common


def test_norcow_set_qw():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"123")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:18] == b"\x01\x00"  # app + key
    assert data[18:20] == b"\x03\x00"  # length
    assert data[20:23] == b"123"  # data
    assert data[23:32] == bytes([0] * 9)  # alignment
    assert common.all_ff_bytes(data[32:])

    n.wipe()
    n.set(0x0901, b"hello")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:18] == b"\x01\x09"  # app + key
    assert data[18:20] == b"\x05\x00"  # length
    assert data[20:25] == b"hello"  # data
    assert data[25:32] == bytes([0] * 7)  # alignment
    assert common.all_ff_bytes(data[32:])

    offset = 32
    n.set(0x0102, b"world!")
    data = n._dump()[0][:256]
    assert data[offset : offset + 2] == b"\x02\x01"  # app + key
    assert data[offset + 2 : offset + 4] == b"\x06\x00"  # length
    assert data[offset + 4 : offset + 4 + 6] == b"world!"  # data
    assert data[offset + 4 + 6 : offset + 16] == bytes([0] * 6)  # alignment
    assert common.all_ff_bytes(data[offset + 16 :])


def test_norcow_update():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"1234567890A")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:18] == b"\x01\x00"  # app + key
    assert data[18:20] == b"\x0B\x00"  # length
    assert data[20:31] == b"1234567890A"  # data
    assert data[31:32] == bytes([0] * 1)  # alignment
    assert common.all_ff_bytes(data[32:])

    n.set(0x0001, b"A0987654321")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:32] == bytes([0] * 16)  # empty data

    assert data[32:34] == b"\x01\x00"  # app + key
    assert data[34:36] == b"\x0B\x00"  # length
    assert data[36:47] == b"A0987654321"  # data
    assert data[47:48] == bytes([0] * 1)  # alignment
    assert common.all_ff_bytes(data[48:])

    n.wipe()
    n.set(0x0001, b"1234567890AB")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:18] == b"\x01\x00"  # app + key
    assert data[18:20] == b"\x0C\x00"  # length
    assert data[20:32] == b"1234567890AB"  # data
    assert common.all_ff_bytes(data[32:])

    n.set(0x0001, b"BA0987654321")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:32] == bytes([0] * 16)  # empty data

    assert data[32:34] == b"\x01\x00"  # app + key
    assert data[34:36] == b"\x0C\x00"  # length
    assert data[36:48] == b"BA0987654321"  # data
    assert common.all_ff_bytes(data[48:])

    n.wipe()

    offset = 16
    n.set(0x0102, b"world!_world!")
    data = n._dump()[0][:256]
    assert data[offset : offset + 2] == b"\x02\x01"  # app + key
    assert data[offset + 2 : offset + 4] == b"\x0D\x00"  # length
    assert data[offset + 16 : offset + 16 + 13] == b"world!_world!"  # data
    assert data[offset + 16 + 13 : offset + 32] == b"\xff\xff\xff"  # alignment
    assert common.all_ff_bytes(data[offset + 32 :])

    n.set(0x0102, b"hello!_hello!")
    data = n._dump()[0][:256]
    assert data[offset : offset + 4] == b"\x02\x01\x0D\x00"  # app + key + length
    assert data[offset + 4 : offset + 32] == bytes([0] * 28)

    offset += 32

    assert data[offset + 0 : offset + 4] == b"\x02\x01\x0D\x00"  # app + key + length
    assert data[offset + 4 : offset + 16] == b"\x00" * 12  # alignment
    assert data[offset + 16 : offset + 16 + 13] == b"hello!_hello!"  # data
    assert data[offset + 16 + 13 : offset + 32] == b"\xff\xff\xff"  # alignment

    assert common.all_ff_bytes(data[offset + 32 :])


def test_norcow_set_qw_long():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"1234567890abc")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:20] == b"\x01\x00\x0D\x00"  # app + key + length
    assert data[32:45] == b"1234567890abc"  # data
    assert common.all_ff_bytes(data[45:])

    n.wipe()
    n.set(0x0901, b"hello_hello__")
    data = n._dump()[0][:256]
    assert data[:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert data[16:20] == b"\x01\x09\x0D\x00"  # app + key + length
    assert data[32:45] == b"hello_hello__"  # data
    assert common.all_ff_bytes(data[45:])

    offset = 48
    n.set(0x0102, b"world!_world!")
    data = n._dump()[0][:256]
    assert data[offset : offset + 4] == b"\x02\x01\x0D\x00"  # app + key + length
    assert data[offset + 16 : offset + 16 + 13] == b"world!_world!"  # data
    assert data[offset + 16 + 13 : offset + 32] == b"\xff\xff\xff"  # alignment
    assert common.all_ff_bytes(data[offset + 32 :])


def test_norcow_read_item_qw():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"123")
    n.set(0x0002, b"456")
    n.set(0x0101, b"789")
    key, value = n._read_item(32)
    assert key == 0x0002
    assert value == b"456"
    key, value = n._read_item(48)
    assert key == 0x0101
    assert value == b"789"

    with pytest.raises(ValueError) as e:
        key, value = n._read_item(204)
    assert "no data" in str(e.value)


def test_norcow_get_item_qw():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"123")
    n.set(0x0002, b"456")
    n.set(0x0101, b"789")
    value = n.get(0x0001)
    assert value == b"123"
    assert (
        n._dump()[0][:80].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "0000000000000000"
        + "01000300313233000000000000000000"
        + "02000300343536000000000000000000"
        + "01010300373839000000000000000000"
        + "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with the same value (update)
    n.set(0x0101, b"789")
    value = n.get(0x0101)
    assert value == b"789"
    assert (
        n._dump()[0][:80].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "0000000000000000"
        + "01000300313233000000000000000000"
        + "02000300343536000000000000000000"
        + "01010300373839000000000000000000"
        + "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with value with less 1 bits than before (wipe and new entry)
    n.set(0x0101, b"788")
    value = n.get(0x0101)
    assert value == b"788"
    assert (
        n._dump()[0][:96].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "0000000000000000"
        + "01000300313233000000000000000000"
        + "02000300343536000000000000000000"
        + "00000000000000000000000000000000"
        + "01010300373838000000000000000000"
        + "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with value with more 1 bits than before (wipe and new entry)
    n.set(0x0101, b"787")
    value = n.get(0x0101)
    assert value == b"787"
    assert (
        n._dump()[0][:112].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "0000000000000000"
        + "01000300313233000000000000000000"
        + "02000300343536000000000000000000"
        + "00000000000000000000000000000000"
        + "00000000000000000000000000000000"
        + "01010300373837000000000000000000"
        + "ffffffffffffffffffffffffffffffff"
    )

    n.set(0x0002, b"world")
    n.set(0x0002, b"earth")
    value = n.get(0x0002)
    assert value == b"earth"


def test_norcow_get_item_qw_long():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"1231231231231")
    n.set(0x0002, b"4564564564564")
    n.set(0x0101, b"7897897897897")
    value = n.get(0x0001)
    assert value == b"1231231231231"
    assert (
        n._dump()[0][:128].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex() + "0000000000000000"
        "01000d00000000000000000000000000"
        "31323331323331323331323331ffffff"
        "02000d00000000000000000000000000"
        "34353634353634353634353634ffffff"
        "01010d00000000000000000000000000"
        "37383937383937383937383937ffffff"
        "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with the same value (update)
    n.set(0x0101, b"7897897897897")
    value = n.get(0x0101)
    assert value == b"7897897897897"
    assert (
        n._dump()[0][:128].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex() + "0000000000000000"
        "01000d00000000000000000000000000"
        "31323331323331323331323331ffffff"
        "02000d00000000000000000000000000"
        "34353634353634353634353634ffffff"
        "01010d00000000000000000000000000"
        "37383937383937383937383937ffffff"
        "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with value with less 1 bits than before (update)
    n.set(0x0101, b"7887887887887")
    value = n.get(0x0101)
    assert value == b"7887887887887"
    assert (
        n._dump()[0][:160].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex() + "0000000000000000"
        "01000d00000000000000000000000000"
        "31323331323331323331323331ffffff"
        "02000d00000000000000000000000000"
        "34353634353634353634353634ffffff"
        "01010d00000000000000000000000000"
        "00000000000000000000000000000000"
        "01010d00000000000000000000000000"
        "37383837383837383837383837ffffff"
        "ffffffffffffffffffffffffffffffff"
    )

    # replacing item with value with more 1 bits than before (wipe and new entry)
    n.set(0x0101, b"7877877877877")
    value = n.get(0x0101)
    assert value == b"7877877877877"
    assert (
        n._dump()[0][:192].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex() + "0000000000000000"
        "01000d00000000000000000000000000"
        "31323331323331323331323331ffffff"
        "02000d00000000000000000000000000"
        "34353634353634353634353634ffffff"
        "01010d00000000000000000000000000"
        "00000000000000000000000000000000"
        "01010d00000000000000000000000000"
        "00000000000000000000000000000000"
        "01010d00000000000000000000000000"
        "37383737383737383737383737ffffff"
        "ffffffffffffffffffffffffffffffff"
    )

    n.set(0x0002, b"world")
    n.set(0x0002, b"earth")
    value = n.get(0x0002)
    assert value == b"earth"


def test_norcow_replace_item_qw():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0001, b"123")
    n.set(0x0002, b"456")
    n.set(0x0101, b"789")
    value = n.get(0x0002)
    assert value == b"456"

    n.replace(0x0001, b"000")
    value = n.get(0x0001)
    assert value == b"000"

    n.replace(0x0002, b"111")
    value = n.get(0x0002)
    assert value == b"111"
    value = n.get(0x0001)
    assert value == b"000"
    value = n.get(0x0101)
    assert value == b"789"

    with pytest.raises(RuntimeError) as e:
        n.replace(0x0001, b"00000")
    assert "same length" in str(e.value)


def test_norcow_compact_qw():
    n = norcow.NorcowBlockwise()
    n.init()
    n.set(0x0101, b"ahoj_ahoj_ahoj")
    n.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - 240))
    n.set(0x0101, b"hello_hello__")

    n.set(0x0103, b"123456789xxxx")
    n.set(0x0104, b"123456789xxxx")
    n.set(0x0105, b"123456789xxxx")
    n.set(0x0106, b"123456789xxxx")
    mem = n._dump()
    assert mem[0][:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    assert mem[0][200:300] == b"\x00" * 100

    # compact is triggered
    n.set(0x0107, b"123456789xxxx")
    mem = n._dump()
    # assert the other sector is active
    assert mem[1][:16] == consts.NORCOW_MAGIC_AND_VERSION + b"\x00" * 8
    # assert the deleted item was not copied
    assert mem[0][200:300] == b"\xff" * 100

    n.set(0x0108, b"123456789x")
    n.set(0x0109, b"123456789x")

    assert n.get(0x0101) == b"hello_hello__"
    assert n.get(0x0103) == b"123456789xxxx"
