import pytest

from python.src.norcow import NC_CLASSES

from . import common


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_change_wipe_code(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        assert s.change_pin("1234")
        assert not s.has_wipe_code()

        assert not s.change_wipe_code("1234", "1234")  # wipe code equal to PIN
        assert not s.has_wipe_code()

        assert s.change_wipe_code("1234", "5678")
        assert s.has_wipe_code()
        assert s.unlock("1234")

        assert s.change_wipe_code("1234", "")  # remove the wipe code
        assert not s.has_wipe_code()

    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_wipe_code_wipes_storage(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        assert s.change_pin("1234")
        assert s.unlock("1234")
        s.set(0x0202, b"Hello")
        assert s.change_wipe_code("1234", "5678")

        assert not s.unlock("5678")  # wipe code, wipes the storage
        assert s.unlock("")
        assert not s.has_pin()
        assert not s.has_wipe_code()
        with pytest.raises(RuntimeError):
            s.get(0x0202)

    assert common.memory_equals(sc, sp)


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_wipe_code_zero_byte(nc_class):
    sc, sp = common.init(nc_class, unlock=True)
    for s in (sc, sp):
        assert s.change_pin("1234")
        assert not s.change_wipe_code("1234", "56\x0078")  # invalid wipe code
        assert not s.has_wipe_code()

        assert s.change_wipe_code("1234", "5678")
        rem = s.get_pin_rem()
        assert not s.unlock("1234\x00")  # invalid PIN
        assert s.get_pin_rem() == rem
        assert not s.unlock("5678\x00")  # zero-byte variant of the wipe code
        assert s.get_pin_rem() == rem
        assert s.unlock("1234")
        assert s.has_wipe_code()

    assert common.memory_equals(sc, sp)
