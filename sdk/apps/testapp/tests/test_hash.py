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

import json

import pytest

from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext
from .common import COMMON_FIXTURES_DIR
from .generated import messages as m

# Every vector, by algorithm: data lengths around each algorithm's block
# boundary, up to 4000 bytes, plus "abc".
VECTORS: dict[str, list[tuple[bytes, bytes]]] = {}
for test in json.loads((COMMON_FIXTURES_DIR / "hash.json").read_text())["tests"]:
    VECTORS.setdefault(test["parameters"]["algorithm"], []).append(
        (
            bytes.fromhex(test["parameters"]["data"]),
            bytes.fromhex(test["result"]["digest"]),
        )
    )

ALGORITHMS = list(m.HashAlgorithm)


def expected(algorithm: m.HashAlgorithm, data: bytes) -> bytes:
    return next(d for v, d in VECTORS[algorithm.name] if v == data)


@pytest.mark.parametrize("algorithm", ALGORITHMS, ids=lambda a: a.name)
def test_hash(session: Session, instance_id: int, algorithm: m.HashAlgorithm):
    for data, digest in VECTORS[algorithm.name]:
        result = testapp_ext.hash(session, instance_id, algorithm, [data])
        assert result == digest, f"{len(data)} bytes"


@pytest.mark.parametrize("algorithm", ALGORITHMS, ids=lambda a: a.name)
def test_hash_no_update(session: Session, instance_id: int, algorithm: m.HashAlgorithm):
    """Finalizing without a single update is the digest of no data."""
    result = testapp_ext.hash(session, instance_id, algorithm, [])
    assert result == expected(algorithm, b"")


@pytest.mark.parametrize("algorithm", ALGORITHMS, ids=lambda a: a.name)
def test_hash_chunked(session: Session, instance_id: int, algorithm: m.HashAlgorithm):
    """Any split of the data into updates gives the digest of the whole."""
    data = next(v for v, _ in VECTORS[algorithm.name] if len(v) == 1000)
    digest = expected(algorithm, data)
    splits = {
        "empty_chunks": [b"", data[:500], b"", data[500:], b""],
        "byte_by_byte": [data[i : i + 1] for i in range(200)] + [data[200:]],
        "uneven": [data[:1], data[1:64], data[64:137], data[137:999], data[999:]],
        "block_sized": [data[i : i + 64] for i in range(0, len(data), 64)],
    }
    for name, chunks in splits.items():
        assert b"".join(chunks) == data
        result = testapp_ext.hash(session, instance_id, algorithm, chunks)
        assert result == digest, name


def test_hash_algorithms_differ(session: Session, instance_id: int):
    """Each algorithm is its own function, not an alias of another."""
    digests = {testapp_ext.hash(session, instance_id, a, [b"abc"]) for a in ALGORITHMS}
    assert len(digests) == len(ALGORITHMS)
