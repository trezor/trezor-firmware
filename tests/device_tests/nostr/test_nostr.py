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
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

pytestmark = [pytest.mark.altcoin, pytest.mark.models("core")]

# test data from NIP-06: https://github.com/nostr-protocol/nips/blob/master/06.md

LEAD_MONKEY_MNEMONIC = (
    "leader monkey parrot ring guide accident before fence cannon height naive bean"
)
LEAD_MONKEY_PUBKEY_HEX = (
    "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917"
)

WHAT_BLEAK_MNEMONIC = "what bleak badge arrange retreat wolf trade produce cricket blur garlic valid proud rude strong choose busy staff weather area salt hollow arm fade"
WHAT_BLEAK_PUBKEY_HEX = (
    "d41b22899549e1f3d335a31002cfd382174006e166d3e658e3a5eecdb6463573"
)

VECTORS = [
    pytest.param(
        LEAD_MONKEY_PUBKEY_HEX,
        marks=pytest.mark.setup_client(mnemonic=LEAD_MONKEY_MNEMONIC),
    ),
    pytest.param(
        WHAT_BLEAK_PUBKEY_HEX,
        marks=pytest.mark.setup_client(mnemonic=WHAT_BLEAK_MNEMONIC),
    ),
]

TEST_EVENTS = [
    {
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
    },
    {
        "created_at": 1737396951,
        "kind": 1,
        "tags": [
            [
                "e",
                "5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36",
                "wss://nostr.example.com",
            ],
            ["p", "f7234bd4c1394dda46d09f35bd384dd30cc552ad5541990f98844fb06676e9ca"],
            ["alt", "reply"],
            ["x-win-dir", "C:\\Program Files"],
        ],
        "content": '\tHellö, "world"',
    },
]

EXPECTED_SIGNATURES = {
    LEAD_MONKEY_PUBKEY_HEX: {
        1737396950: "a2981b2f9858184226a0c63ec000102bedfc35afcb2e7cb4a91bdd3a95d4faeeb6afb523ebae1f3a2889ed93be6b8f3d86e0ab1e9dd0fe4ebc7bf75ba9a4dc78",
        1737396951: "0ecd0e600af0d8bd651729436220eec873c67f89319a979e83ea47013a3dd36ae4708124a76ccdeccea56bf92d86df610f834de6a44d1691d986ade1516a1d3e",
    },
    WHAT_BLEAK_PUBKEY_HEX: {
        1737396950: "dbfc47f0174ef263e471d07b5df99a6a9eb88b881250a207f67bff344c3503b8544cd25a4f4d183773ed11edfe3d3741925cb2fa9def09dcac3bab7d11d835ac",
        1737396951: "4d8cda744fb19b25d8863cecf5e73caefe309f5483e182521854d2c82f0b4956bf7d0c672ee346625d37e8696bc71ad898664fb88cfd6bf5aed9972b2e8f13b0",
    },
}


def event_to_pb(event: dict) -> messages.NostrSignEvent:
    return messages.NostrSignEvent(
        address_n=parse_path("m/44h/1237h/0h/0/0"),
        created_at=event["created_at"],
        kind=event["kind"],
        content=event["content"],
        tags=[
            messages.NostrTag(key=t[0], value=t[1] if len(t) > 1 else None, extra=t[2:])
            for t in event["tags"]
        ],
    )


@pytest.mark.parametrize("pubkey_hex", VECTORS)
def test_get_pubkey(session: Session, pubkey_hex: str):
    response = nostr.get_pubkey(
        session,
        n=parse_path("m/44h/1237h/0h/0/0"),
    )

    assert response == bytes.fromhex(pubkey_hex)


@pytest.mark.parametrize("pubkey_hex", VECTORS)
@pytest.mark.parametrize("event", TEST_EVENTS)
def test_sign_event(session: Session, pubkey_hex: str, event: dict):
    response = nostr.sign_event(session, event_to_pb(event))

    assert response.pubkey == bytes.fromhex(pubkey_hex)

    expected_id = sha256(
        json.dumps(
            [
                0,
                pubkey_hex,
                event["created_at"],
                event["kind"],
                event["tags"],
                event["content"],
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).digest()

    assert response.id == expected_id
    assert (
        response.signature.hex() == EXPECTED_SIGNATURES[pubkey_hex][event["created_at"]]
    )
