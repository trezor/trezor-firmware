# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from ecdsa import SECP256k1, VerifyingKey
from hashlib import sha256
import json
import pytest
from six import b
import time

from trezorlib import nostr
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

# test data from NIP-06: https://github.com/nostr-protocol/nips/blob/master/06.md

LEAD_MONKEY_MNEMONIC = "leader monkey parrot ring guide accident before fence cannon height naive bean"
LEAD_MONKEY_SK = "7f7ff03d123792d6ac594bfa67bf6d0c0ab55b6b1fdb6249303fe861f1ccba9a"
LEAD_MONKEY_PK = "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917"

WHAT_BLEAK_MNEMONIC = "what bleak badge arrange retreat wolf trade produce cricket blur garlic valid proud rude strong choose busy staff weather area salt hollow arm fade"
WHAT_BLEAK_SK = "c15d739894c81a2fcfd3a2df85a0d2c0dbc47a280d092799f144d73d7ae78add"
WHAT_BLEAK_PK = "d41b22899549e1f3d335a31002cfd382174006e166d3e658e3a5eecdb6463573"

@pytest.mark.setup_client(mnemonic=LEAD_MONKEY_MNEMONIC)
def test_signevent_lead_monkey(client: Client):
    _test_sign_event(client, LEAD_MONKEY_SK, LEAD_MONKEY_PK)

#@pytest.mark.setup_client(mnemonic=WHAT_BLEAK_MNEMONIC)
#def test_signevent_what_bleak(client: Client):
#    _test_sign_event(client, WHAT_BLEAK_SK, WHAT_BLEAK_PK)

def _test_sign_event(client, expected_sk, expected_pk):
    created_at = int(time.time())
    kind = 1
    tags = []
    content = "Hello, world!"

    sig = nostr.sign_event(
        client,
        event=json.dumps({'created_at': created_at, 'kind': kind, 'tags': tags, 'content': content}),
        n=parse_path("m/44'/1237'/0'/0/0"),
    )

    assert sig.pubkey == bytes.fromhex(expected_pk)

    expected_id = sha256(json.dumps([0, expected_pk, created_at, kind, tags, content], separators=(',', ':')).encode('utf-8')).digest()

    assert sig.id == expected_id

    key_verifier = VerifyingKey.from_string(b("\x02") + bytes.fromhex(expected_pk), curve=SECP256k1)

    assert key_verifier.verify(sig.signature[-64:], sig.id)
