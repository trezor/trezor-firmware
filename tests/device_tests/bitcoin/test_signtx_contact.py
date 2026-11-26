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

"""Pay-to-contact at SignTx: the payer's Trezor names an external output.

Alice's Trezor attests her receive address (GetAddress with
contact_attestation, here in a passphrase wallet of the same device). Bob's
standard wallet holds `npub(Alice) -> "Alice"` in WARD. When Bob signs a
transaction whose output carries Alice's attestation, his Trezor verifies the
attestation, pulls the WARD proof for her npub and shows "Alice" instead of
"Recipient #1". Every failure shows the bare address; only malformed contact
fields abort signing."""

from collections.abc import Callable
from hashlib import sha256
from typing import TypeVar

import pytest
from embit import bech32, ec

from trezorlib import btc, messages, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.testing.device_handler import BackgroundDeviceHandler
from trezorlib.tools import parse_path

from ...input_flows import InputFlowConfirmAllWarnings
from ...tx_cache import TxCache
from ...ward_mgr_emu import (
    WMEmulator,
    device_ward_keys,
    sign_ward_update,
    wm_attestation,
)

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.setup_client(passphrase=True),
]

T = TypeVar("T")

TX_API_TESTNET = TxCache("Testnet")
TXHASH_b36780 = bytes.fromhex(
    "b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e"
)

_APP = "bitcoin"  # the host label domain SignTx is granted
NAME = "Alice"
ALICE_PASSPHRASE = "p2c-recipient"
ALICE_PATH = parse_path("m/84h/1h/0h/0/0")

_TAG = sha256(b"trezor/contact-address/v1").digest()

# Bob is the standard wallet of the default test seed; the host tree uses his
# device's WARD keys so that its proofs verify on the device.
_K_PATH, _K_DATA, _K_IDENT = device_ward_keys()


def _tree() -> WARDTree:
    return WARDTree(_K_PATH, _K_DATA, _K_IDENT)


def _npub(pubkey: bytes) -> bytes:
    """NIP-19 npub of a 32-byte x-only key, as the roster identifier (UTF-8)."""
    data = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode(bech32.Encoding.BECH32, "npub", data).encode()


def _digest(slip44: int, address: str) -> bytes:
    return sha256(_TAG + _TAG + slip44.to_bytes(4, "big") + address.encode()).digest()


def _alice_attests(client: Client) -> tuple[str, bytes, bytes]:
    """Alice's Trezor attests her receive address. Returns (address, pubkey,
    signature)."""
    alice = client.get_session(passphrase=ALICE_PASSPHRASE)
    with alice.test_ctx as test_client:
        test_client.set_input_flow(InputFlowConfirmAllWarnings(alice).get())
        resp = btc.get_authenticated_address(
            alice,
            "Testnet",
            ALICE_PATH,
            show_display=True,
            script_type=messages.InputScriptType.SPENDWITNESS,
            contact_attestation=True,
        )
    assert resp.contact_pubkey is not None and resp.contact_signature is not None
    return resp.address, resp.contact_pubkey, resp.contact_signature


def _bob(client: Client) -> Session:
    return client.get_session(passphrase="")


def _roster(session: Session, entries: dict[bytes, bytes]) -> WARDTree:
    """Install a WARD tree with `entries` (npub -> name) as Bob's trusted root."""
    tree = _tree()
    for npub, name in entries.items():
        tree.insert(_APP, npub, name, counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    return tree


def _contact_output(
    address: str, pubkey: bytes | None, signature: bytes | None
) -> messages.TxOutputType:
    return messages.TxOutputType(
        address=address,
        amount=40_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        contact_pubkey=pubkey,
        contact_signature=signature,
    )


def _change_output() -> messages.TxOutputType:
    return messages.TxOutputType(
        address_n=parse_path("m/84h/1h/0h/1/87"),
        amount=100_000 - 40_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )


def _sign(
    session: Session,
    outputs: list[messages.TxOutputType],
    proof_callback: (
        Callable[[messages.WARDProofRequest], messages.WARDProofAck] | None
    ),
) -> list[str]:
    """Sign a Testnet transaction from Bob's standard wallet, confirming every
    screen. Returns the text of each page, whitespace folded."""
    inp = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_b36780,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    pages: list[str] = []

    def on_page(layout: LayoutContent) -> None:
        text = f"{layout.title()} {layout.subtitle()} {layout.screen_content()}"
        pages.append(" ".join(text.split()))

    with session.test_ctx as client:
        client.app.ward_proof_callback = proof_callback
        client.set_input_flow(lambda: client.ui.default_input_flow(on_page=on_page))
        btc.sign_tx(session, "Testnet", [inp], outputs, prev_txes=TX_API_TESTNET)
    return pages


def _shown(pages: list[str], address: str) -> bool:
    return any(address in "".join(page.split()) for page in pages)


def _assert_named(pages: list[str], address: str) -> None:
    assert _shown(pages, address)
    assert any(NAME in page for page in pages)


def _assert_bare(pages: list[str], address: str) -> None:
    assert _shown(pages, address)
    assert not any(NAME in page for page in pages)


def test_contact_name_shown(client: Client):
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    tree = _roster(bob, {_npub(pubkey): NAME.encode()})

    pulled: list[bytes] = []
    serve = ward.tree_proof_callback(tree)

    def proofs(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        pulled.append(msg.entry_key)
        return serve(msg)

    pages = _sign(
        bob, [_contact_output(address, pubkey, signature), _change_output()], proofs
    )
    _assert_named(pages, address)
    # one pull, for the attested identity only
    assert pulled == [tree._ek(_APP, _npub(pubkey), "address", 0)]


def test_without_contact_fields_no_pull(client: Client):
    address, pubkey, _signature = _alice_attests(client)
    bob = _bob(client)
    _roster(bob, {_npub(pubkey): NAME.encode()})

    def never(_msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        raise AssertionError("no WARD proof may be pulled without contact fields")

    pages = _sign(bob, [_contact_output(address, None, None), _change_output()], never)
    _assert_bare(pages, address)


def test_bad_signature(client: Client):
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    tree = _roster(bob, {_npub(pubkey): NAME.encode()})
    forged = bytes([signature[0] ^ 1]) + signature[1:]

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, forged), _change_output()],
        ward.tree_proof_callback(tree),
    )
    _assert_bare(pages, address)


@pytest.mark.parametrize("slip44, named", ((1, True), (0, False)))
def test_attestation_is_bound_to_the_coin(client: Client, slip44: int, named: bool):
    """An attestation made for another coin (slip44 0) of the same address string
    does not name a Testnet output; the same key signing for slip44 1 does."""
    address, _pubkey, _signature = _alice_attests(client)
    key = ec.PrivateKey(sha256(b"contact identity").digest())
    pubkey = key.xonly()
    signature = key.schnorr_sign(_digest(slip44, address)).serialize()
    bob = _bob(client)
    tree = _roster(bob, {_npub(pubkey): NAME.encode()})

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, signature), _change_output()],
        ward.tree_proof_callback(tree),
    )
    if named:
        _assert_named(pages, address)
    else:
        _assert_bare(pages, address)


def test_npub_not_in_roster(client: Client):
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    other = ec.PrivateKey(sha256(b"someone else").digest()).xonly()
    tree = _roster(bob, {_npub(other): NAME.encode()})

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, signature), _change_output()],
        ward.tree_proof_callback(tree),
    )
    _assert_bare(pages, address)


@pytest.mark.parametrize(
    "value",
    (
        pytest.param("Alice Müller".encode(), id="non_ascii"),
        pytest.param("‮Alice".encode(), id="bidi_override"),
        pytest.param(b" Alice", id="leading_space"),
    ),
)
def test_name_not_plain_text(client: Client, value: bytes):
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    tree = _roster(bob, {_npub(pubkey): value})

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, signature), _change_output()],
        ward.tree_proof_callback(tree),
    )
    _assert_bare(pages, address)


def test_no_proof_callback(client: Client):
    """No WARD host (trezorlib answers WARDProofAck(unavailable)): bare address."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    _roster(bob, {_npub(pubkey): NAME.encode()})

    pages = _sign(
        bob, [_contact_output(address, pubkey, signature), _change_output()], None
    )
    _assert_bare(pages, address)


def test_no_trusted_root(client: Client):
    """The device never synced WARD: the proof cannot be checked, bare address."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    tree = _tree()
    tree.insert(_APP, _npub(pubkey), NAME.encode(), counter=1)

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, signature), _change_output()],
        ward.tree_proof_callback(tree),
    )
    _assert_bare(pages, address)


def _confirmed(session: Session, fn: Callable[[Session], T]) -> T:
    """Run `fn` and approve its one confirmation screen."""
    with session.test_ctx as client:
        # the handler replaces the UI and does not put it back
        ui, button_callback = client.ui, client.app.button_callback
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(session, fn)
            dev.debuglink().press_yes()
            result = dev.result()
        client.ui, client.app.button_callback = ui, button_callback
    return result


def _queue_delete(session: Session, identifier: bytes) -> int:
    pending_id = _confirmed(
        session,
        lambda s: ward.queue_update(
            s, _APP, identifier, NAME.encode(), b"", delete=True
        ),
    )
    assert pending_id is not None
    return pending_id


def test_sticky_cached_name_needs_a_proof(client: Client):
    """An offline copy of the contact the user chose to keep (sticky) is shown by
    DisplayAddress as "cached" when there is no WARD host. It is not a proof, so
    SignTx does not name the output with it."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    npub = _npub(pubkey)
    tree = _roster(bob, {npub: NAME.encode()})
    bob.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    try:
        _confirmed(
            bob,
            lambda s: ward.cache_entry(s, tree._ek(_APP, npub, "address", 0), True),
        )
    except TrezorFailure as e:
        if "this firmware has no offline store" in str(e):
            pytest.skip("firmware built without the WARD offline store")
        raise
    outputs = [_contact_output(address, pubkey, signature), _change_output()]

    _assert_bare(_sign(bob, outputs, None), address)
    _assert_named(_sign(bob, outputs, ward.tree_proof_callback(tree)), address)


def test_deleted_entry(client: Client):
    """The contact was deleted from WARD; the old attestation no longer names the
    output."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    npub = _npub(pubkey)
    tree = _roster(bob, {npub: NAME.encode()})
    outputs = [_contact_output(address, pubkey, signature), _change_output()]
    _assert_named(_sign(bob, outputs, ward.tree_proof_callback(tree)), address)

    # delete through the device: queue -> perform (pulls the proof) -> WM confirms
    pending_id = _queue_delete(bob, npub)
    bob.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    res = ward.perform_update(bob, pending_id)
    counter, _root, mac, ward_id, entry_key, leaf = res
    assert ward_id is not None and leaf.is_delete()
    sig = sign_ward_update(counter, mac if mac is not None else ward.ZERO_MAC, ward_id)
    ward.confirmed_by_wm(bob, counter, mac, sig, pending_id)
    tree.del_leaf(entry_key)

    _assert_bare(_sign(bob, outputs, ward.tree_proof_callback(tree)), address)


def test_queued_delete(client: Client):
    """A delete waiting for the WARD Manager hides the name without asking the
    host for a proof; once it is discarded the name is back."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    npub = _npub(pubkey)
    tree = _roster(bob, {npub: NAME.encode()})
    outputs = [_contact_output(address, pubkey, signature), _change_output()]

    pending_id = _queue_delete(bob, npub)

    def never(_msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        raise AssertionError(
            "no proof may be pulled for a contact with a queued change"
        )

    _assert_bare(_sign(bob, outputs, never), address)

    ward.discard_pending(bob, pending_id)
    _assert_named(_sign(bob, outputs, ward.tree_proof_callback(tree)), address)


@pytest.mark.parametrize(
    "freshness, named",
    (("current", True), ("behind", False), ("forged", False)),
)
def test_freshness(client: Client, freshness: str, named: bool):
    """A host that attaches the WM's head attestation: the name is shown only if
    the head is this device's own; a newer head (the roster changed elsewhere) or
    an attestation that does not verify shows the bare address."""
    address, pubkey, signature = _alice_attests(client)
    bob = _bob(client)
    tree = _tree()
    tree.insert(_APP, _npub(pubkey), NAME.encode(), counter=1)
    counter, _root, wallet_id, mac = ward.debug_set_root(bob, tree.get_root_hash())
    _nonce, ward_id = ward.sync(bob)
    assert wallet_id is not None and mac is not None and ward_id is not None

    def attest(nonce: bytes) -> messages.WARDAttestation:
        if freshness == "behind":
            newer_mac = WMEmulator().root_mac(wallet_id, counter + 1, b"n" * 32)
            return wm_attestation(nonce, counter + 1, newer_mac, ward_id)
        att = wm_attestation(nonce, counter, mac, ward_id)
        if freshness == "forged":
            att.wm_signature = bytes([att.wm_signature[0] ^ 1]) + att.wm_signature[1:]
        return att

    pages = _sign(
        bob,
        [_contact_output(address, pubkey, signature), _change_output()],
        ward.tree_proof_callback(tree, attest),
    )
    if named:
        _assert_named(pages, address)
    else:
        _assert_bare(pages, address)


_PUBKEY = bytes(range(32))
_SIGNATURE = bytes(range(64))
_ADDRESS = "tb1qe48wz5ysk9mlzhkswcxct9tdjw6ejr2l9e6j8q"


@pytest.mark.parametrize(
    "output",
    (
        pytest.param(_contact_output(_ADDRESS, _PUBKEY, None), id="pubkey_only"),
        pytest.param(_contact_output(_ADDRESS, None, _SIGNATURE), id="signature_only"),
        pytest.param(
            _contact_output(_ADDRESS, _PUBKEY + b"\x00", _SIGNATURE), id="pubkey_33"
        ),
        pytest.param(
            _contact_output(_ADDRESS, _PUBKEY, _SIGNATURE[:63]), id="signature_63"
        ),
        pytest.param(
            messages.TxOutputType(
                amount=0,
                op_return_data=b"test",
                script_type=messages.OutputScriptType.PAYTOOPRETURN,
                contact_pubkey=_PUBKEY,
                contact_signature=_SIGNATURE,
            ),
            id="op_return",
        ),
        pytest.param(
            messages.TxOutputType(
                address_n=parse_path("m/84h/1h/0h/0/1"),
                amount=40_000,
                script_type=messages.OutputScriptType.PAYTOWITNESS,
                contact_pubkey=_PUBKEY,
                contact_signature=_SIGNATURE,
            ),
            id="own_address",
        ),
    ),
)
def test_malformed_contact_fields(client: Client, output: messages.TxOutputType):
    with pytest.raises(TrezorFailure, match="Invalid contact attestation"):
        _sign(_bob(client), [output, _change_output()], None)
