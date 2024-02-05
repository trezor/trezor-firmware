import pytest

from python.src import consts
from python.src.norcow import NorcowBitwise, NorcowBlockwise

from . import common


@pytest.mark.parametrize(
    "nc_class,reserve", [(NorcowBlockwise, 800), (NorcowBitwise, 600)]
)
def test_compact(nc_class, reserve):
    sc, sp = common.init(nc_class, unlock=True)

    assert sp._get_active_sector() == 0
    assert sc._get_active_sector() == 0

    for s in (sc, sp):
        s.set(0xBEEF, b"hello")
        s.set(0xBEEF, b"asdasdasdasd")
        s.set(0xBEEF, b"fsdasdasdasdasdsadasdsadasdasd")
        s.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - reserve))
        s.set(0x03FE, b"world!")
        s.set(0x04FE, b"world!xfffffffffffffffffffffffffffff")
        s.set(0x05FE, b"world!affffffffffffffffffffffffffffff")
        assert s._get_active_sector() == 1
        s.set(0x0101, b"s")
        s.set(0x06FE, b"world!aaaaaaaaaaaaaaaaaaaaaaaaab")
        s.set(0x07FE, b"worxxxxxxxxxxxxxxxxxx")
        s.set(0x09EE, b"worxxxxxxxxxxxxxxxxxx")
    assert common.memory_equals(sc, sp)

    assert sp._get_active_sector() == 0
    assert sc._get_active_sector() == 0

    sc, sp = common.init(nc_class, unlock=True)
    assert sp._get_active_sector() == 0
    assert sc._get_active_sector() == 0
    for s in (sc, sp):
        s.set(0xBEEF, b"asdasdasdasd")
        s.set(0xBEEF, b"fsdasdasdasdasdsadasdsadasdasd")
        s.set(0x8101, b"a" * (consts.NORCOW_SECTOR_SIZE - 1000))
        with pytest.raises(RuntimeError):
            s.set(0x0101, b"a" * (consts.NORCOW_SECTOR_SIZE - 100))
        s.set(0x0101, b"hello")

    assert sp._get_active_sector() == 1
    assert sc._get_active_sector() == 1
    assert common.memory_equals(sc, sp)
