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

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext


def get_nonce(session: Session) -> bytes:
    """Has Core cache a fresh nonce for this session, as `GetNonce` does."""
    return session.call(messages.GetNonce(), expect=messages.Nonce).nonce


def test_verify_nonce_cache(session: Session, instance_id: int):
    nonce = get_nonce(session)
    assert testapp_ext.verify_nonce_cache(session, instance_id, nonce) is True


def test_verify_nonce_cache_single_use(session: Session, instance_id: int):
    """A verified nonce is removed from the cache."""
    nonce = get_nonce(session)
    assert testapp_ext.verify_nonce_cache(session, instance_id, nonce) is True
    assert testapp_ext.verify_nonce_cache(session, instance_id, nonce) is False


def test_verify_nonce_cache_nothing_cached(session: Session, instance_id: int):
    assert testapp_ext.verify_nonce_cache(session, instance_id, b"\x00" * 32) is False
    assert testapp_ext.verify_nonce_cache(session, instance_id, b"") is False


def test_verify_nonce_cache_wrong_nonce(session: Session, instance_id: int):
    nonce = get_nonce(session)
    for wrong in (
        bytes([nonce[0] ^ 1]) + nonce[1:],
        nonce[:-1],
        nonce + b"\x00",
        b"",
    ):
        assert testapp_ext.verify_nonce_cache(session, instance_id, wrong) is False
    # A wrong guess leaves the cached nonce in place.
    assert testapp_ext.verify_nonce_cache(session, instance_id, nonce) is True


def test_verify_nonce_cache_latest_only(session: Session, instance_id: int):
    """A new GetNonce replaces the previously cached nonce."""
    old = get_nonce(session)
    new = get_nonce(session)
    assert old != new
    assert testapp_ext.verify_nonce_cache(session, instance_id, old) is False
    assert testapp_ext.verify_nonce_cache(session, instance_id, new) is True
