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

import hashlib
import hmac

import pytest

from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext
from .common import parametrize_using_common_fixtures
from .generated import messages as m

HASHES = {
    m.HmacAlgorithm.HmacSha256: hashlib.sha256,
    m.HmacAlgorithm.HmacSha512: hashlib.sha512,
}


@parametrize_using_common_fixtures("hmac.json")
def test_hmac(session: Session, instance_id: int, parameters, result):
    """RFC 4231 test cases, and keys shorter than, equal to and longer than
    the hash's block size."""
    digest = testapp_ext.hmac(
        session,
        instance_id,
        m.HmacAlgorithm[parameters["algorithm"]],
        bytes.fromhex(parameters["key"]),
        [bytes.fromhex(parameters["data"])],
    )
    assert digest.hex() == result["digest"]


@pytest.mark.parametrize("algorithm", list(m.HmacAlgorithm), ids=lambda a: a.name)
def test_hmac_chunked(session: Session, instance_id: int, algorithm: m.HmacAlgorithm):
    """Any split of the data into updates gives the HMAC of the whole."""
    key = b"chunked key"
    data = bytes(range(256)) * 4
    for chunks in (
        [],
        [b"", data, b""],
        [data[i : i + 1] for i in range(100)] + [data[100:]],
        [data[i : i + 7] for i in range(0, len(data), 7)],
    ):
        expected = hmac.new(key, b"".join(chunks), HASHES[algorithm]).digest()
        assert (
            testapp_ext.hmac(session, instance_id, algorithm, key, chunks) == expected
        )


@pytest.mark.parametrize("algorithm", list(m.HmacAlgorithm), ids=lambda a: a.name)
def test_hmac_key_matters(
    session: Session, instance_id: int, algorithm: m.HmacAlgorithm
):
    """A different key, or the key zero-padded to the block size, changes the MAC
    only where the HMAC definition says so."""
    block = HASHES[algorithm]().block_size
    data = b"message"
    a = testapp_ext.hmac(session, instance_id, algorithm, b"key", [data])
    b = testapp_ext.hmac(session, instance_id, algorithm, b"kez", [data])
    assert a != b
    # HMAC pads a short key with zeros, so these two keys are the same key.
    padded = testapp_ext.hmac(
        session, instance_id, algorithm, b"key" + b"\x00" * (block - 3), [data]
    )
    assert padded == a
