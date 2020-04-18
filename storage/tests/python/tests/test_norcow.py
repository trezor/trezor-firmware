import pytest

from ..src import consts, norcow
from . import common


def test_norcow_set():
    n = norcow.Norcow()
    n.init()
    n.set(0x0001, b"123")
    data = n._dump()[0][:256]
    assert data[:8] == consts.NORCOW_MAGIC_AND_VERSION
    assert data[8:10] == b"\x01\x00"  # app + key
    assert data[10:12] == b"\x03\x00"  # length
    assert data[12:15] == b"123"  # data
    assert common.all_ff_bytes(data[16:])

    n.wipe()
    n.set(0x0901, b"hello")
    data = n._dump()[0][:256]
    assert data[:8] == consts.NORCOW_MAGIC_AND_VERSION
    assert data[8:10] == b"\x01\x09"  # app + key
    assert data[10:12] == b"\x05\x00"  # length
    assert data[12:17] == b"hello"  # data
    assert data[17:20] == b"\x00\x00\x00"  # alignment
    assert common.all_ff_bytes(data[20:])

    offset = 20
    n.set(0x0102, b"world!")
    data = n._dump()[0][:256]
    assert data[offset : offset + 2] == b"\x02\x01"  # app + key
    assert data[offset + 2 : offset + 4] == b"\x06\x00"  # length
    assert data[offset + 4 : offset + 10] == b"world!"  # data
    assert data[offset + 10 : offset + 12] == b"\x00\x00"  # alignment
    assert common.all_ff_bytes(data[offset + 12 :])


def test_norcow_read_item():
    n = norcow.Norcow()
    n.init()
    n.set(0x0001, b"123")
    n.set(0x0002, b"456")
    n.set(0x0101, b"789")
    key, value = n._read_item(16)
    assert key == 0x0002
    assert value == b"456"
    key, value = n._read_item(24)
    assert key == 0x0101
    assert value == b"789"

    with pytest.raises(ValueError) as e:
        key, value = n._read_item(204)
    assert "no data" in str(e.value)


def test_norcow_get_item():
    n = norcow.Norcow()
    n.init()
    n.set(0x0001, b"123")
    n.set(0x0002, b"456")
    n.set(0x0101, b"789")
    value = n.get(0x0001)
    assert value == b"123"
    assert (
        n._dump()[0][:40].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "010003003132330002000300343536000101030037383900ffffffffffffffff"
    )

    # replacing item with the same value (update)
    n.set(0x0101, b"789")
    value = n.get(0x0101)
    assert value == b"789"
    assert (
        n._dump()[0][:40].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "010003003132330002000300343536000101030037383900ffffffffffffffff"
    )

    # replacing item with value with less 1 bits than before (update)
    n.set(0x0101, b"788")
    value = n.get(0x0101)
    assert value == b"788"
    assert (
        n._dump()[0][:40].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "010003003132330002000300343536000101030037383800ffffffffffffffff"
    )

    # replacing item with value with more 1 bits than before (wipe and new entry)
    n.set(0x0101, b"787")
    value = n.get(0x0101)
    assert value == b"787"
    assert (
        n._dump()[0][:44].hex()
        == consts.NORCOW_MAGIC_AND_VERSION.hex()
        + "0100030031323300020003003435360000000300000000000101030037383700ffffffff"
    )

    n.set(0x0002, b"world")
    n.set(0x0002, b"earth")
    value = n.get(0x0002)
    assert value == b"earth"


def test_norcow_replace_item():
    n = norcow.Norcow()
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


def test_norcow_compact():
    n = norcow.Norcow()
    n.init()
    n.set(0x0101, b"ahoj")
    n.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - 100))
    n.set(0x0101, b"hello")

    n.set(0x0103, b"123456789x")
    n.set(0x0104, b"123456789x")
    n.set(0x0105, b"123456789x")
    n.set(0x0106, b"123456789x")
    mem = n._dump()
    assert mem[0][:8] == consts.NORCOW_MAGIC_AND_VERSION
    assert mem[0][200:300] == b"\x00" * 100

    # compact is triggered
    n.set(0x0107, b"123456789x")
    mem = n._dump()
    # assert the other sector is active
    assert mem[1][:8] == consts.NORCOW_MAGIC_AND_VERSION
    # assert the deleted item was not copied
    assert mem[0][200:300] == b"\xff" * 100

    n.set(0x0108, b"123456789x")
    n.set(0x0109, b"123456789x")

    assert n.get(0x0101) == b"hello"
    assert n.get(0x0103) == b"123456789x"
