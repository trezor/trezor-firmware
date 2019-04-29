from ..src.storage import Storage


def test_set_pin_success():
    s = Storage()
    hw_salt = b"\x00\x00\x00\x00\x00\x00"
    s.init(hw_salt)
    s._set_pin(1)
    assert s.unlock(1)

    s = Storage()
    s.init(hw_salt)
    s._set_pin(229922)
    assert s.unlock(229922)


def test_set_pin_failure():
    s = Storage()
    hw_salt = b"\x00\x00\x00\x00\x00\x00"
    s.init(hw_salt)
    s._set_pin(1)
    assert s.unlock(1)
    assert not s.unlock(1234)

    s = Storage()
    s.init(hw_salt)
    s._set_pin(229922)
    assert not s.unlock(1122992211)
