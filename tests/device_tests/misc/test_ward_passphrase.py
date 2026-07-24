"""WARD behaviour across passphrase (hidden) wallets.

A passphrase changes the seed, hence the wallet_id (RIPEMD160(SHA256(master
pubkey))) AND the MAC key (SLIP-21 from the passphrase seed, bound to wallet_id).
So each hidden wallet is a fully independent WARD tree, and neither a WM
attestation nor a root_mac minted for one wallet may be accepted by another.

The WMEmulator reproduces each hidden wallet's secrets from the known mnemonic +
that wallet's passphrase, so it can attest each wallet correctly and forge the
cross-wallet attempts the negative tests need."""

import pytest

from trezorlib import ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure

from ...ward_mgr_emu import WMEmulator, sign_wm_attestation, wm_initial_sync

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.setup_client(passphrase=True),
]

_PP_A = "passphrase-A"
_PP_B = "passphrase-B"
_ADDR_A = "bc1qwalletaentry0000000000000000000000000000"
_ADDR_B = "bc1qwalletbentry0000000000000000000000000000"
_VAL_A = b'TEST:1:{"label":"A"}'
_VAL_B = b'TEST:1:{"label":"B"}'


def _single_leaf_tree(address: str, value: bytes) -> WARDTree:
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    return tree


def test_ward_passphrase_wallets_are_isolated(client: Client) -> None:
    """Two passphrases => two wallet_ids => two independent WARD trees. Each
    wallet adopts its own tree and authenticates only its own entry."""
    session_a = client.get_session(passphrase=_PP_A)
    session_b = client.get_session(passphrase=_PP_B)
    wm_a = WMEmulator(passphrase=_PP_A)
    wm_b = WMEmulator(passphrase=_PP_B)

    _pending, wallet_id_a = ward.list_pending(session_a)
    _pending, wallet_id_b = ward.list_pending(session_b)
    assert wallet_id_a is not None and wallet_id_b is not None
    assert wallet_id_a != wallet_id_b

    tree_a = _single_leaf_tree(_ADDR_A, _VAL_A)
    tree_b = _single_leaf_tree(_ADDR_B, _VAL_B)
    wm_initial_sync(session_a, wm_a, tree_a, counter=1, wallet_id=wallet_id_a)
    wm_initial_sync(session_b, wm_b, tree_b, counter=1, wallet_id=wallet_id_b)

    # Each wallet authenticates its own entry ...
    valid_a, membership_a, _c, _w = ward.lookup(
        session_a, _ADDR_A.encode(), _VAL_A, tree_a.get_proof(_ADDR_A.encode()), counter=1
    )
    assert valid_a and membership_a
    valid_b, membership_b, _c, _w = ward.lookup(
        session_b, _ADDR_B.encode(), _VAL_B, tree_b.get_proof(_ADDR_B.encode()), counter=1
    )
    assert valid_b and membership_b

    # ... and does NOT recognize the other wallet's entry (different root).
    other_valid, _m, _c, _w = ward.lookup(
        session_a, _ADDR_B.encode(), _VAL_B, tree_b.get_proof(_ADDR_B.encode()), counter=1
    )
    assert not other_valid


def test_ward_passphrase_mac_is_wallet_scoped(client: Client) -> None:
    """A root_mac minted for wallet A must not bind the same root on wallet B:
    the MAC key is derived from the (passphrase-dependent) seed + wallet_id, so
    reconcile on B recomputes a different MAC and rejects."""
    session_a = client.get_session(passphrase=_PP_A)
    session_b = client.get_session(passphrase=_PP_B)
    wm_a = WMEmulator(passphrase=_PP_A)

    _pending, wallet_id_a = ward.list_pending(session_a)
    _pending, wallet_id_b = ward.list_pending(session_b)
    assert wallet_id_a is not None and wallet_id_b is not None

    tree = _single_leaf_tree(_ADDR_A, _VAL_A)
    root = tree.get_root_hash()
    mac_a = wm_a.root_mac(wallet_id_a, 1, root)  # MAC that only wallet A can reproduce

    # Give B a FRESHLY-signed, otherwise-valid attestation carrying A's MAC, so it
    # clears B's signature + counter checks and fails only at the MAC binding.
    nonce_b = ward.sync(session_b)
    sig = sign_wm_attestation(nonce_b, 1, mac_a, wallet_id_b)
    ward.ingest_attestation(session_b, 1, mac_a, sig)

    with pytest.raises(TrezorFailure, match="root does not match the attested mac"):
        ward.reconcile(session_b, root)


def test_ward_passphrase_attestation_is_wallet_bound(client: Client) -> None:
    """A whole WM attestation minted for wallet A cannot be replayed to wallet B:
    the signature covers wallet_id, so B's verification (with its own wallet_id)
    fails."""
    session_a = client.get_session(passphrase=_PP_A)
    session_b = client.get_session(passphrase=_PP_B)
    wm_a = WMEmulator(passphrase=_PP_A)

    _pending, wallet_id_a = ward.list_pending(session_a)
    assert wallet_id_a is not None

    tree = _single_leaf_tree(_ADDR_A, _VAL_A)
    root = tree.get_root_hash()
    mac_a = wm_a.root_mac(wallet_id_a, 1, root)

    # Attestation valid for wallet A (signed over nonce_a, wallet_id_a).
    nonce_a = ward.sync(session_a)
    sig_a = wm_a.sign_attestation(wallet_id_a, nonce_a, 1, mac_a)

    # Replay it into a sync round on wallet B.
    ward.sync(session_b)
    with pytest.raises(TrezorFailure, match="attestation verification failed"):
        ward.ingest_attestation(session_b, 1, mac_a, sig_a)
