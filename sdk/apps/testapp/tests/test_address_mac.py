# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import btc
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from . import testapp_ext
from .testapp_ext import DEFAULT_BIP32_PATH, SdkError, raises

ADDRESS_N = parse_path(DEFAULT_BIP32_PATH)
ADDRESS = "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
SLIP44 = 1


def get_mac(session: Session, instance_id: int, **kw) -> bytes:
    args = {"address_n": ADDRESS_N, "address": ADDRESS, "slip44": SLIP44, **kw}
    return testapp_ext.get_address_mac(
        session, instance_id, args["address_n"], args["address"], args["slip44"]
    )


def check_mac(session: Session, instance_id: int, mac: bytes, **kw) -> None:
    args = {"address_n": ADDRESS_N, "address": ADDRESS, "slip44": SLIP44, **kw}
    testapp_ext.check_address_mac(
        session, instance_id, args["address_n"], mac, args["address"], args["slip44"]
    )


def test_address_mac_roundtrip(session: Session, instance_id: int):
    mac = get_mac(session, instance_id)
    assert len(mac) == 32
    check_mac(session, instance_id, mac)


def test_address_mac_deterministic(session: Session, instance_id: int):
    assert get_mac(session, instance_id) == get_mac(session, instance_id)


@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"address": ADDRESS + "x"}, id="address"),
        pytest.param({"address": ""}, id="empty_address"),
        pytest.param({"slip44": 0}, id="slip44"),
        pytest.param({"slip44": 0xFFFFFFFF}, id="slip44_max"),
        pytest.param({"address_n": parse_path("m/44h/1h/0h/0/1")}, id="path"),
    ],
)
def test_address_mac_binds_inputs(session: Session, instance_id: int, change: dict):
    """The MAC covers the address, the coin type and the path: changing any of
    them gives a different MAC, under which the original doesn't check."""
    mac = get_mac(session, instance_id)
    other = get_mac(session, instance_id, **change)
    assert other != mac
    check_mac(session, instance_id, other, **change)
    with raises(SdkError.ServiceError):
        check_mac(session, instance_id, mac, **change)


def test_check_address_mac_wrong_mac(session: Session, instance_id: int):
    mac = bytearray(get_mac(session, instance_id))
    for i in (0, 31):
        corrupted = bytearray(mac)
        corrupted[i] ^= 0x01
        with raises(SdkError.ServiceError):
            check_mac(session, instance_id, bytes(corrupted))
    with raises(SdkError.ServiceError):
        check_mac(session, instance_id, b"\x00" * 32)


@pytest.mark.parametrize("length", [0, 31, 33])
def test_check_address_mac_wrong_length(
    session: Session, instance_id: int, length: int
):
    with raises(SdkError.InvalidArgument):
        check_mac(session, instance_id, b"\x01" * length)


def test_address_mac_long_address(session: Session, instance_id: int):
    address = "a" * 1000
    mac = get_mac(session, instance_id, address=address)
    check_mac(session, instance_id, mac, address=address)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("m/44h/0h/0h/0/0", id="other_coin"),
        pytest.param("m/44h", id="purpose"),
    ],
)
def test_get_address_mac_forbidden_path(session: Session, instance_id: int, path: str):
    with raises(SdkError.ServiceError):
        get_mac(session, instance_id, address_n=parse_path(path))


def test_check_address_mac_other_app_path(session: Session, instance_id: int):
    """A MAC from another app checks, as in a coin purchase memo, while a wrong
    one on the same path still fails."""
    address_n = parse_path("m/44h/0h/0h/0/0")
    resp = btc.get_authenticated_address(session, "Bitcoin", address_n)
    assert resp.mac is not None
    kw = {"address_n": address_n, "address": resp.address, "slip44": 0}
    check_mac(session, instance_id, resp.mac, **kw)
    with raises(SdkError.ServiceError):
        check_mac(session, instance_id, b"\x00" * 32, **kw)
