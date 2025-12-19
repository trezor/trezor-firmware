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
from __future__ import annotations

import secrets

from trezorlib.thp import cpace, curve25519

PRS = b"Password"
CI = b"oc\x0bB_responder\x0bA_initiator"
SID = bytes.fromhex("7e4b4791d6a8ef019b936c79fb7f2c57")

GENERATOR_STRING = bytes.fromhex(
    "0843506163653235350850617373776f72646d000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000001a6f630b425f726573706f6e"
    "6465720b415f696e69746961746f72107e4b4791d6a8ef019b936c79"
    "fb7f2c57"
)

GENERATOR = bytes.fromhex(
    "64e8099e3ea682cfdc5cb665c057ebb514d06bf23ebc9f743b51b82242327074"
)


def test_generator():
    assert cpace._generator_string(prs=PRS, ci=CI, sid=SID) == GENERATOR_STRING
    assert cpace._generator(prs=PRS, ci=CI, sid=SID) == GENERATOR


def test_exchange():
    a_privkey = secrets.token_bytes(32)
    a_pubkey = curve25519.multiply(a_privkey, GENERATOR)
    b_privkey = secrets.token_bytes(32)
    b_pubkey = curve25519.multiply(b_privkey, GENERATOR)

    result_a = cpace.cpace(
        prs=PRS, ci=CI, sid=SID, b_pubkey=b_pubkey, _a_privkey=a_privkey
    )
    result_b = cpace.cpace(
        prs=PRS, ci=CI, sid=SID, b_pubkey=a_pubkey, _a_privkey=b_privkey
    )

    assert result_b.a_pubkey == b_pubkey
    assert result_a.a_pubkey == a_pubkey
    assert result_b.shared_secret == result_a.shared_secret
