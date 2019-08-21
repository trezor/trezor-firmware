import pytest

from python.src import consts

from . import common


def test_compact():
    sc, sp = common.init(unlock=True)
    for s in (sc, sp):
        s.set(0xBEEF, b"hello")
        s.set(0xBEEF, b"asdasdasdasd")
        s.set(0xBEEF, b"fsdasdasdasdasdsadasdsadasdasd")
        s.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - 600))
        s.set(0x03FE, b"world!")
        s.set(0x04FE, b"world!xfffffffffffffffffffffffffffff")
        s.set(0x05FE, b"world!affffffffffffffffffffffffffffff")
        s.set(0x0101, b"s")
        s.set(0x06FE, b"world!aaaaaaaaaaaaaaaaaaaaaaaaab")
        s.set(0x07FE, b"worxxxxxxxxxxxxxxxxxx")
        s.set(0x09EE, b"worxxxxxxxxxxxxxxxxxx")
    assert common.memory_equals(sc, sp)

    sc, sp = common.init(unlock=True)
    for s in (sc, sp):
        s.set(0xBEEF, b"asdasdasdasd")
        s.set(0xBEEF, b"fsdasdasdasdasdsadasdsadasdasd")
        s.set(0x8101, b"a" * (consts.NORCOW_SECTOR_SIZE - 1000))
        with pytest.raises(RuntimeError):
            s.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - 100))
        s.set(0x0101, b"hello")
    assert common.memory_equals(sc, sp)
