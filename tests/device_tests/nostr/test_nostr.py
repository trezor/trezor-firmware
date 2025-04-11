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

import json
from hashlib import sha256

import pytest

from trezorlib import messages, nostr
from trezorlib.tools import parse_path

pytestmark = [pytest.mark.altcoin, pytest.mark.models("core")]

# test data from NIP-06: https://github.com/nostr-protocol/nips/blob/master/06.md

LEAD_MONKEY_MNEMONIC = (
    "leader monkey parrot ring guide accident before fence cannon height naive bean"
)
LEAD_MONKEY_PUBKEY_HEX = (
    "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917"
)

LEAD_MONKEY_EXPECTED_SIG = "a2981b2f9858184226a0c63ec000102bedfc35afcb2e7cb4a91bdd3a95d4faeeb6afb523ebae1f3a2889ed93be6b8f3d86e0ab1e9dd0fe4ebc7bf75ba9a4dc78"

WHAT_BLEAK_MNEMONIC = "what bleak badge arrange retreat wolf trade produce cricket blur garlic valid proud rude strong choose busy staff weather area salt hollow arm fade"
WHAT_BLEAK_PUBKEY_HEX = (
    "d41b22899549e1f3d335a31002cfd382174006e166d3e658e3a5eecdb6463573"
)

WHAT_BLEAK_EXPECTED_SIG = "dbfc47f0174ef263e471d07b5df99a6a9eb88b881250a207f67bff344c3503b8544cd25a4f4d183773ed11edfe3d3741925cb2fa9def09dcac3bab7d11d835ac"

pytestmark_lead_monkey = pytest.mark.setup_client(mnemonic=LEAD_MONKEY_MNEMONIC)
pytestmark_what_bleak = pytest.mark.setup_client(mnemonic=WHAT_BLEAK_MNEMONIC)

VECTORS = [
    pytest.param(
        LEAD_MONKEY_PUBKEY_HEX, LEAD_MONKEY_EXPECTED_SIG, marks=pytestmark_lead_monkey
    ),
    pytest.param(
        WHAT_BLEAK_PUBKEY_HEX, WHAT_BLEAK_EXPECTED_SIG, marks=pytestmark_what_bleak
    ),
]

TEST_EVENT = {
    "created_at": 1737396950,
    "kind": 1,
    "tags": [
        [
            "e",
            "5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36",
            "wss://nostr.example.com",
        ],
        ["p", "f7234bd4c1394dda46d09f35bd384dd30cc552ad5541990f98844fb06676e9ca"],
        [
            "a",
            "30023:f7234bd4c1394dda46d09f35bd384dd30cc552ad5541990f98844fb06676e9ca:abcd",
            "wss://nostr.example.com",
        ],
        ["alt", "reply"],
    ],
    "content": "Hello, world",
}

SIGN_TEST_EVENT = messages.NostrSignEvent(
    address_n=parse_path("m/44h/1237h/0h/0/0"),
    created_at=TEST_EVENT["created_at"],
    kind=TEST_EVENT["kind"],
    content=TEST_EVENT["content"],
    tags=[
        messages.NostrTag(key=t[0], value=t[1] if len(t) > 1 else None, extra=t[2:])
        for t in TEST_EVENT["tags"]
    ],
)


@pytest.mark.parametrize("pubkey_hex,_", VECTORS)
def test_get_pubkey(client, pubkey_hex, _):
    response = nostr.get_pubkey(
        client,
        n=parse_path("m/44h/1237h/0h/0/0"),
    )

    assert response == bytes.fromhex(pubkey_hex)


@pytest.mark.parametrize("pubkey_hex,expected_sig", VECTORS)
def test_sign_event(client, pubkey_hex, expected_sig):
    response = nostr.sign_event(client, SIGN_TEST_EVENT)

    assert response.pubkey == bytes.fromhex(pubkey_hex)

    expected_id = sha256(
        json.dumps(
            [
                0,
                pubkey_hex,
                TEST_EVENT["created_at"],
                TEST_EVENT["kind"],
                TEST_EVENT["tags"],
                TEST_EVENT["content"],
            ],
            separators=(",", ":"),
        ).encode()
    ).digest()

    assert response.id == expected_id
    assert response.signature == bytes.fromhex(expected_sig)
