import pytest

from ..src.norcow import NC_CLASSES
from ..src.storage import Storage


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_pin_success(nc_class):
    s = Storage(nc_class)
    hw_salt = b"\x00\x00\x00\x00\x00\x00"
    s.init(hw_salt)
    s._set_pin("")
    assert s.unlock("")

    s = Storage(nc_class)
    s.init(hw_salt)
    s._set_pin("229922")
    assert s.unlock("229922")


@pytest.mark.parametrize("nc_class", NC_CLASSES)
def test_set_pin_failure(nc_class):
    s = Storage(nc_class)
    hw_salt = b"\x00\x00\x00\x00\x00\x00"
    s.init(hw_salt)
    s._set_pin("")
    assert s.unlock("")
    assert not s.unlock("1234")

    s = Storage(nc_class)
    s.init(hw_salt)
    s._set_pin("229922")
    assert not s.unlock("1122992211")
