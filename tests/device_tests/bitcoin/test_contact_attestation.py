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

"""Contact address attestation: GetAddress(contact_attestation) and
NostrGetPubkey(show_display).

The receiver's Trezor signs an address it derived and showed with the contact
identity key m/44'/1237'/0'/0/0, after a separate "Share address" consent."""

from collections.abc import Callable, Generator
from hashlib import sha256

import pytest
from embit import ec

from trezorlib import btc, messages, nostr
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import Cancelled
from trezorlib.tools import parse_path

from ...input_flows import InputFlowConfirmAllWarnings

# NIP-06 test mnemonic, so the identity key matches NIP-06 and the independent
# vector in core/tests/test_apps.common.contacts.py
MNEMONIC = (
    "leader monkey parrot ring guide accident before fence cannon height naive bean"
)

pytestmark = [
    pytest.mark.altcoin,  # NostrGetPubkey exists only in universal firmware
    pytest.mark.models("core"),
    pytest.mark.setup_client(mnemonic=MNEMONIC),
]

IDENTITY_PATH = parse_path("m/44h/1237h/0h/0/0")
IDENTITY_PUBKEY = bytes.fromhex(
    "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917"
)
IDENTITY_NPUB = "npub1zutzeysacnf9rru6zqwmxd54mud0k44tst6l70ja5mhv8jjumytsd2x7nu"

SHARE_BR_NAME = "contact_share_address"
_TAG = sha256(b"trezor/contact-address/v1").digest()

S = messages.InputScriptType


def _digest(slip44: int, address: str) -> bytes:
    return sha256(_TAG + _TAG + slip44.to_bytes(4, "big") + address.encode()).digest()


def _verify(pubkey: bytes, signature: bytes, slip44: int, address: str) -> bool:
    return ec.PublicKey.from_xonly(pubkey).schnorr_verify(
        ec.SchnorrSig.parse(signature), _digest(slip44, address)
    )


def _recording(
    flow: Callable[[], Generator], names: list[str]
) -> Callable[[], Generator]:
    """Wrap an input flow and record the names of the button requests."""

    def wrapper() -> Generator:
        inner = flow()
        next(inner)
        while True:
            br = yield
            names.append(br.name)
            inner.send(br)

    return wrapper


def _attest(
    session: Session,
    coin: str,
    path: str,
    script_type: messages.InputScriptType,
    show_display: bool = True,
    multisig: messages.MultisigRedeemScriptType | None = None,
) -> tuple[messages.Address, list[str]]:
    names: list[str] = []
    with session.test_ctx as client:
        client.set_input_flow(
            _recording(InputFlowConfirmAllWarnings(session).get(), names)
        )
        resp = btc.get_authenticated_address(
            session,
            coin,
            parse_path(path),
            show_display=show_display,
            script_type=script_type,
            multisig=multisig,
            contact_attestation=True,
        )
    return resp, names


VECTORS_ATTESTED = (  # coin, slip44, path, script_type
    ("Bitcoin", 0, "m/84h/0h/0h/0/0", S.SPENDWITNESS),
    ("Bitcoin", 0, "m/86h/0h/0h/0/3", S.SPENDTAPROOT),
    ("Bitcoin", 0, "m/49h/0h/1h/0/0", S.SPENDP2SHWITNESS),
    ("Bitcoin", 0, "m/44h/0h/0h/0/0", S.SPENDADDRESS),
    ("Testnet", 1, "m/84h/1h/0h/0/0", S.SPENDWITNESS),
    ("Testnet", 1, "m/84h/1h/0h/0/999", S.SPENDWITNESS),
)


@pytest.mark.parametrize("coin, slip44, path, script_type", VECTORS_ATTESTED)
def test_attestation(
    session: Session,
    coin: str,
    slip44: int,
    path: str,
    script_type: messages.InputScriptType,
):
    resp, names = _attest(session, coin, path, script_type)
    assert names == ["show_address", SHARE_BR_NAME]

    assert resp.address == btc.get_address(
        session, coin, parse_path(path), script_type=script_type
    )
    assert resp.contact_pubkey == IDENTITY_PUBKEY
    assert resp.contact_signature is not None
    assert len(resp.contact_signature) == 64
    assert _verify(resp.contact_pubkey, resp.contact_signature, slip44, resp.address)
    # bound to the coin
    assert not _verify(
        resp.contact_pubkey, resp.contact_signature, slip44 ^ 1, resp.address
    )


@pytest.mark.setup_client(mnemonic=MNEMONIC, passphrase=True)
def test_attestation_pubkey_is_nostr_pubkey(client: Client):
    """The attesting key is the session's NostrGetPubkey key, also for a
    passphrase wallet."""
    session = client.get_session(passphrase="")
    pubkey = nostr.get_pubkey(session, IDENTITY_PATH)
    assert pubkey == IDENTITY_PUBKEY
    resp, _ = _attest(session, "Testnet", "m/84h/1h/0h/0/5", S.SPENDWITNESS)
    assert resp.contact_pubkey == pubkey
    assert resp.contact_signature is not None
    assert _verify(pubkey, resp.contact_signature, 1, resp.address)

    hidden = client.get_session(passphrase="Alice")
    hidden_pubkey = nostr.get_pubkey(hidden, IDENTITY_PATH)
    assert hidden_pubkey != pubkey
    hidden_resp, _ = _attest(hidden, "Testnet", "m/84h/1h/0h/0/5", S.SPENDWITNESS)
    assert hidden_resp.address != resp.address
    assert hidden_resp.contact_pubkey == hidden_pubkey
    assert hidden_resp.contact_signature is not None
    assert _verify(hidden_pubkey, hidden_resp.contact_signature, 1, hidden_resp.address)


def test_no_attestation_without_show_display(session: Session):
    resp, names = _attest(
        session, "Bitcoin", "m/84h/0h/0h/0/0", S.SPENDWITNESS, show_display=False
    )
    assert names == []
    assert resp.contact_signature is None
    assert resp.contact_pubkey is None


@pytest.mark.parametrize(
    "path, script_type",
    (
        pytest.param("m/84h/0h/0h/1/0", S.SPENDWITNESS, id="change"),
        pytest.param("m/84h/0h/0h/0/1000", S.SPENDWITNESS, id="index_1000"),
        pytest.param("m/84h/0h/0h/0/0", S.SPENDADDRESS, id="script_type_mismatch"),
        pytest.param("m/1/0", S.SPENDADDRESS, id="greenaddress"),
        pytest.param("m/49/0/0/0/0", S.SPENDP2SHWITNESS, id="casa_unhardened"),
    ),
)
def test_no_attestation_for_path(
    session: Session, path: str, script_type: messages.InputScriptType
):
    resp, names = _attest(session, "Bitcoin", path, script_type)
    assert SHARE_BR_NAME not in names
    assert resp.contact_signature is None
    assert resp.contact_pubkey is None


@pytest.mark.multisig
def test_no_attestation_for_multisig(session: Session):
    # 1-of-1 multisig on a path that would otherwise be attested
    node = btc.get_public_node(
        session, parse_path("m/84h/0h/0h"), coin_name="Bitcoin"
    ).node
    multisig = messages.MultisigRedeemScriptType(
        nodes=[node], address_n=[0, 0], signatures=[b""], m=1
    )
    resp, names = _attest(
        session, "Bitcoin", "m/84h/0h/0h/0/0", S.SPENDWITNESS, multisig=multisig
    )
    assert "show_address" in names
    assert SHARE_BR_NAME not in names
    assert resp.contact_signature is None
    assert resp.contact_pubkey is None


def test_share_address_cancel(session: Session):
    debug = session.debug
    names: list[str] = []

    def input_flow() -> Generator:
        br = yield
        names.append(br.name)
        assert br.name == "show_address"
        debug.press_yes()

        br = yield
        names.append(br.name)
        assert br.name == SHARE_BR_NAME
        assert br.code == messages.ButtonRequestType.ProtectCall
        assert "Share address" in debug.read_layout().title()
        if session.layout_type is LayoutType.Eckhart:
            # the user picks "Cancel" in the screen's menu
            debug.click(debug.screen_buttons.menu())
            debug.synchronize_at("VerticalMenu")
            debug.button_actions.navigate_to_menu_item(0)
        else:
            session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        btc.get_authenticated_address(
            session,
            "Bitcoin",
            parse_path("m/84h/0h/0h/0/0"),
            show_display=True,
            script_type=S.SPENDWITNESS,
            contact_attestation=True,
        )
    assert names == ["show_address", SHARE_BR_NAME]


def test_nostr_get_pubkey_show_display(session: Session):
    texts: list[str] = []
    names: list[str] = []

    def on_page(layout) -> None:
        texts.append(layout.text_content())

    with session.test_ctx as client:
        client.set_input_flow(
            _recording(lambda: client.ui.default_input_flow(on_page=on_page), names)
        )
        pubkey = nostr.get_pubkey(session, IDENTITY_PATH, show_display=True)

    assert pubkey == IDENTITY_PUBKEY
    assert names == ["show_pubkey"]
    shown = "".join("".join(texts).split())
    assert IDENTITY_NPUB in shown


def test_nostr_get_pubkey_silent(session: Session):
    with session.test_ctx as client:
        names: list[str] = []
        client.set_input_flow(_recording(client.ui.default_input_flow, names))
        assert nostr.get_pubkey(session, IDENTITY_PATH) == IDENTITY_PUBKEY
    assert names == []
