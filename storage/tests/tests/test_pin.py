import pytest

from python.src import consts

from . import common


def test_init_pin():
    sc, sp = common.init(uid=b"\x00\x00\x00\x00\x00\x00")
    assert common.memory_equals(sc, sp)

    sc, sp = common.init(uid=b"\x22\x00\xDD\x00\x00\xBE")
    assert common.memory_equals(sc, sp)


def test_change_pin():
    sc, sp = common.init(unlock=True)
    for s in (sc, sp):
        assert s.change_pin("", "222")
        assert not s.change_pin("9999", "")  # invalid PIN
        assert s.unlock("222")
        assert s.change_pin("222", "99999")
        assert s.change_pin("99999", "Trezor")
        assert s.unlock("Trezor")
        assert not s.unlock("9999")  # invalid PIN
        assert not s.unlock("99999")  # invalid old PIN

    assert common.memory_equals(sc, sp)


def test_has_pin():
    sc, sp = common.init()
    for s in (sc, sp):
        assert not s.has_pin()
        assert s.unlock("")
        assert not s.has_pin()
        assert s.change_pin("", "22")
        assert s.has_pin()
        assert s.change_pin("22", "")
        assert not s.has_pin()


def test_wipe_after_max_pin():
    sc, sp = common.init(unlock=True)
    for s in (sc, sp):
        assert s.change_pin("", "222")
        assert s.unlock("222")
        s.set(0x0202, b"Hello")

        # try an invalid PIN MAX - 1 times
        for i in range(consts.PIN_MAX_TRIES - 1):
            assert not s.unlock("9999")
        # this should pass
        assert s.unlock("222")
        assert s.get(0x0202) == b"Hello"

        # try an invalid PIN MAX times, the storage should get wiped
        for i in range(consts.PIN_MAX_TRIES):
            assert not s.unlock("9999")
        assert i == consts.PIN_MAX_TRIES - 1
        # this should return False and raise an exception, the storage is wiped
        assert not s.unlock("222")
        with pytest.raises(RuntimeError):
            assert s.get(0x0202) == b"Hello"

    assert common.memory_equals(sc, sp)
