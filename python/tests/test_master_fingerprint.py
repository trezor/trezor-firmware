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

import io

import pytest

from trezorlib._internal.master_fingerprint import (
    master_fingerprint,
    parse_fingerprints_file,
)
from trezorlib._internal.slip26 import Purpose

T3T1 = int.from_bytes(b"T3T1", "little")
FP1 = "11" * 32
FP2 = "22" * 32
FP3 = "33" * 32

TRIPLES = {
    (T3T1, Purpose.FIRMWARE, bytes.fromhex(FP1)),
    (T3T1, Purpose.SECURE_MONITOR, bytes.fromhex(FP2)),
    (0, Purpose.DEFINITIONS, bytes.fromhex(FP3)),
}

# sha256 of the triples above, sorted, each hashed as model (4B LE), purpose
# (1B), fingerprint (32B); computed independently of the implementation
MASTER = bytes.fromhex(
    "f83c2542aa3edecfbed2246c39db58f8fd459f0059300402c2fd70f20d063723"
)


def _fingerprints_file(text: str, name: str = "fps.txt") -> io.StringIO:
    f = io.StringIO(text)
    f.name = name
    return f


def test_parse_fingerprints_file():
    """Comments, blank lines, chunked hex and duplicates are handled"""
    chunked = " ".join(FP2[i : i + 4] for i in range(0, len(FP2), 4))
    text = (
        "# core-T3T1/firmware/firmware-T3T1-2.12.2-987f81b8.bin\n"
        f"t3t1_universal: {FP1}\n"
        "\n"
        f"t3t1_secmon: {chunked}\n"
        f"definitions: {FP3}  # trailing comment\n"
        f"t3t1_universal: {FP1}\n"
    )
    assert parse_fingerprints_file(_fingerprints_file(text)) == TRIPLES


@pytest.mark.parametrize(
    "line,error",
    [
        (f"t3t1_universal {FP1}", "expected 'label: HEX'"),
        (f"t3t1_unknown: {FP1}", "unknown label"),
        ("t3t1_universal: xyz", "invalid hex"),
        ("t3t1_universal: aabb", "must be 32 bytes"),
    ],
)
def test_parse_fingerprints_file_errors(line, error):
    """Malformed lines are rejected with the file name and line number"""
    text = f"t3t1_universal: {FP1}\n{line}\n"
    with pytest.raises(ValueError) as e:
        parse_fingerprints_file(_fingerprints_file(text))
    assert str(e.value).startswith("fps.txt:2: ")
    assert error in str(e.value)


def test_master_fingerprint():
    assert master_fingerprint(TRIPLES) == MASTER


def test_master_fingerprint_order_independent():
    """The result must not depend on the order the fingerprints were listed in"""
    text_a = f"t3t1_universal: {FP1}\nt3t1_secmon: {FP2}\ndefinitions: {FP3}\n"
    text_b = f"definitions: {FP3}\nt3t1_universal: {FP1}\nt3t1_secmon: {FP2}\n"
    master_a = master_fingerprint(parse_fingerprints_file(_fingerprints_file(text_a)))
    master_b = master_fingerprint(parse_fingerprints_file(_fingerprints_file(text_b)))
    assert master_a == master_b == MASTER


def test_master_fingerprint_empty():
    with pytest.raises(ValueError, match="no fingerprints found"):
        master_fingerprint(set())
