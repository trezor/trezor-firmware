"""Negative protocol tests: rejection must preserve the trusted head and usability.

Proof cases use debug-only root setup, then check an honest proof before and after
the attack. Attestation cases deliberately give the adversary the debug WM key:
WM signatures must not substitute for wallet authentication of a new state.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.ward_manager import DEBUG_SEED
from trezorlib import messages, ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.ward_protocol import attestation_message

from ...ward_mgr_emu import WMEmulator
from .test_ward_mpt import _tree

pytestmark = pytest.mark.models("T3T1", "T3W1")

TIMESTAMP = 1700001000
GENERATION = b"h" * 32


def _head(session: Session) -> tuple:
    reply = session.call(messages.WARDSync(), expect=messages.WARDSyncAck)
    return reply.counter, reply.root, reply.root_known, reply.ward_id


def _attestation(
    session: Session,
    *,
    counter: int = 0,
    mac: bytes | None = None,
    timestamp: int = TIMESTAMP,
    wrong_nonce: bool = False,
    wrong_wallet: bool = False,
) -> messages.WARDIngestAttestation:
    challenge = session.call(messages.WARDSync(), expect=messages.WARDSyncAck)
    assert challenge.ward_id is not None
    signature = Ed25519PrivateKey.from_private_bytes(DEBUG_SEED).sign(
        attestation_message(
            (b"w" * 32 if wrong_wallet else bytes(challenge.ward_id)).hex(),
            (b"n" * 32 if wrong_nonce else bytes(challenge.nonce)).hex(),
            counter,
            mac.hex() if mac is not None else None,
            timestamp,
            GENERATION.hex(),
        )
    )
    return messages.WARDIngestAttestation(
        counter=counter,
        mac=mac,
        timestamp=timestamp,
        head_nonce=GENERATION,
        wm_signature=signature,
    )


def _reject(session: Session, message) -> None:
    with pytest.raises(TrezorFailure) as rejected:
        session.call(message)
    assert rejected.value.code == messages.FailureType.DataError


def _genesis_still_usable(session: Session, before: tuple) -> None:
    assert _head(session) == before
    session.call(_attestation(session), expect=messages.WARDIngestAttestationAck)
    counter, root, _ = ward.reconcile(session, None)
    assert counter == 0 and root is None
    assert _head(session) == before


@pytest.mark.parametrize(
    "field",
    [
        "nonce",
        "wallet",
        "counter",
        "mac",
        "timestamp",
        "head_nonce",
        "signature",
    ],
)
def test_adversarial_attestation_field_tampering(session: Session, field: str) -> None:
    before = _head(session)
    request = _attestation(
        session, wrong_nonce=field == "nonce", wrong_wallet=field == "wallet"
    )
    if field == "counter":
        request.counter = 1
    elif field == "mac":
        request.mac = b"m" * 32
    elif field == "timestamp":
        request.timestamp += 1
    elif field == "head_nonce":
        request.head_nonce = b"x" * 32
    elif field == "signature":
        request.wm_signature = b"\x00" * 64
    _reject(session, request)
    _genesis_still_usable(session, before)


def test_adversarial_replayed_attestation(session: Session) -> None:
    before = _head(session)
    stale = _attestation(session)
    ward.sync(session)  # New device challenge invalidates the captured response.
    _reject(session, stale)
    _genesis_still_usable(session, before)


def test_adversarial_positive_empty_head_signed_by_wm(session: Session) -> None:
    before = _head(session)
    _reject(session, _attestation(session, counter=1, mac=bytes(32)))
    _genesis_still_usable(session, before)


def test_adversarial_signed_timestamp_regression(session: Session) -> None:
    session.call(_attestation(session), expect=messages.WARDIngestAttestationAck)
    ward.reconcile(session, None)
    before = _head(session)
    _reject(session, _attestation(session, timestamp=TIMESTAMP - 301))
    _genesis_still_usable(session, before)


def test_adversarial_wm_cannot_authorize_a_non_wallet_root(session: Session) -> None:
    before = _head(session)
    session.call(
        _attestation(session, counter=1, mac=b"m" * 32),
        expect=messages.WARDIngestAttestationAck,
    )
    _reject(session, messages.WARDReconcile(root=b"r" * 32))
    _genesis_still_usable(session, before)


def test_adversarial_same_counter_cannot_switch_to_another_wallet_authorized_root(
    session: Session,
) -> None:
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"original", counter=1)
    root = tree.get_root_hash()
    counter, _, _, _ = ward.debug_set_root(session, root)
    _, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    wallet = WMEmulator()
    current_mac = wallet.root_mac(bytes(wallet_id), counter, root)
    session.call(
        _attestation(session, counter=counter, mac=current_mac),
        expect=messages.WARDIngestAttestationAck,
    )
    ward.reconcile(session, root)  # Establish that the test's MAC key is correct.
    before = _head(session)

    other = _tree()
    other.insert("bitcoin", b"alice", b"alternate", counter=counter)
    other_root = other.get_root_hash()
    assert other_root != root
    alternate_mac = wallet.root_mac(bytes(wallet_id), counter, other_root)
    session.call(
        _attestation(session, counter=counter, mac=alternate_mac),
        expect=messages.WARDIngestAttestationAck,
    )
    _reject(session, messages.WARDReconcile(root=other_root))
    assert _head(session) == before
    leaf = tree.leaf_blob("bitcoin", b"alice")
    valid, member, installed = ward.lookup(session, "bitcoin", b"alice", [], leaf=leaf)
    assert valid and member and installed == counter


def test_adversarial_signed_counter_rollback_preserves_trusted_root(
    session: Session,
) -> None:
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"original", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    before = _head(session)
    _reject(session, _attestation(session, counter=0))
    assert _head(session) == before
    valid, member, counter = ward.lookup(
        session, "bitcoin", b"alice", [], leaf=tree.leaf_blob("bitcoin", b"alice")
    )
    assert valid and member and counter == before[0]


@pytest.mark.parametrize("kind", ["single", "batch", "revert"])
def test_adversarial_wm_final_signature_requires_a_device_candidate(
    session: Session, kind: str
) -> None:
    before = _head(session)
    assert before[3] is not None
    mac = b"m" * 32
    signature = Ed25519PrivateKey.from_private_bytes(DEBUG_SEED).sign(
        b"WARD FINAL v1" + bytes(before[3]) + (1).to_bytes(4, "big") + mac
    )
    request_type = {
        "single": messages.WARDConfirmedByWM,
        "batch": messages.WARDConfirmBatchByWM,
        "revert": messages.WARDConfirmRevertByWM,
    }[kind]
    _reject(session, request_type(counter=1, mac=mac, wm_signature=signature))
    _genesis_still_usable(session, before)


@pytest.mark.parametrize(
    "attack",
    [
        "omitted",
        "forged_auth",
        "wrong_predecessor",
        "reordered",
        "omitted_tail",
        "forged_tail",
        "terminal_mac",
    ],
)
def test_adversarial_chain_does_not_partially_advance(
    session: Session, attack: str
) -> None:
    before = _head(session)
    assert before[3] is not None
    wallet = WMEmulator()
    ward_id = bytes(before[3])
    valid_links = [
        messages.WARDChainLink(
            from_counter=0,
            to_counter=1,
            to_root=b"r" * 32,
            auth_commit=wallet.auth_commit(ward_id, 0, None, 1, b"r" * 32),
        ),
        messages.WARDChainLink(
            from_counter=1,
            from_root=b"r" * 32,
            to_counter=2,
            to_root=b"s" * 32,
            auth_commit=wallet.auth_commit(ward_id, 1, b"r" * 32, 2, b"s" * 32),
        ),
    ]
    session.call(
        _attestation(session, counter=2, mac=b"m" * 32),
        expect=messages.WARDIngestAttestationAck,
    )
    links = []
    if attack in ("omitted_tail", "forged_tail", "terminal_mac"):
        links = list(valid_links[:1]) if attack == "omitted_tail" else list(valid_links)
        if attack == "forged_tail":
            links[-1] = messages.WARDChainLink(
                from_counter=1,
                from_root=b"r" * 32,
                to_counter=2,
                to_root=b"s" * 32,
                auth_commit=b"x" * 32,
            )
    elif attack != "omitted":
        links = [
            messages.WARDChainLink(
                from_counter=1 if attack in ("wrong_predecessor", "reordered") else 0,
                to_counter=2 if attack in ("wrong_predecessor", "reordered") else 1,
                to_root=b"r" * 32,
                auth_commit=b"a" * 32,
            )
        ]
        if attack == "reordered":
            links.append(
                messages.WARDChainLink(
                    from_counter=0,
                    to_counter=1,
                    to_root=b"s" * 32,
                    auth_commit=b"b" * 32,
                )
            )
    _reject(session, messages.WARDVerifyChain(links=links))
    _genesis_still_usable(session, before)
    # Positive control: the same authorized prefix and complete valid suffix work.
    _, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    genuine_mac = wallet.root_mac(bytes(wallet_id), 2, b"s" * 32)
    session.call(
        _attestation(session, counter=2, mac=genuine_mac),
        expect=messages.WARDIngestAttestationAck,
    )
    accepted = session.call(
        messages.WARDVerifyChain(links=valid_links), expect=messages.WARDVerifyChainAck
    )
    assert accepted.counter == 2 and accepted.new_root == b"s" * 32


@pytest.mark.parametrize(
    "attack",
    [
        "content",
        "identity",
        "tag",
        "nonce",
        "truncated_proof",
        "split_bit",
        "namespace",
        "key_type",
        "device_id",
    ],
)
def test_adversarial_proof_tampering_preserves_head(
    session: Session, attack: str
) -> None:
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"first", counter=1)
    tree.insert("bitcoin", b"bob", b"second", counter=1)
    root = tree.get_root_hash()
    ward.debug_set_root(session, root)
    before = _head(session)
    leaf = tree.leaf_blob("bitcoin", b"alice")
    assert leaf is not None
    proof = tree.get_proof("bitcoin", b"alice")

    def honest():
        valid, member, counter = ward.lookup(
            session, "bitcoin", b"alice", proof, leaf=leaf
        )
        assert valid and member and counter == before[0]

    honest()
    forged = leaf
    bad_proof = list(proof)
    app = "bitcoin"
    key_type, device_id = "address", 0

    def flip(value):
        assert value
        return bytes([value[0] ^ 1]) + value[1:]

    if attack == "identity":
        forged = leaf._replace(
            identity=leaf.identity._replace(body=flip(leaf.identity.body))
        )
    elif attack in ("content", "tag", "nonce"):
        field = "body" if attack == "content" else attack
        part = leaf.content._replace(**{field: flip(getattr(leaf.content, field))})
        forged = leaf._replace(content=part)
    elif attack == "truncated_proof":
        assert bad_proof
        bad_proof.pop()
    elif attack == "split_bit":
        assert bad_proof
        bad_proof[0] = flip(bad_proof[0])
    elif attack == "namespace":
        app = "ethereum"
    elif attack == "key_type":
        key_type = "label"
    elif attack == "device_id":
        device_id = 1

    try:
        valid, _, _ = ward.lookup(
            session,
            app,
            b"alice",
            bad_proof,
            leaf=forged,
            key_type=key_type,
            device_id=device_id,
        )
    except TrezorFailure as rejected:
        assert rejected.code == messages.FailureType.DataError
    else:
        assert valid is False, f"accepted forged {attack} proof"
    assert _head(session) == before
    honest()


@pytest.mark.parametrize(
    "attack", ["witness_commit_only", "witness_key_only", "proof_only", "identity_only"]
)
def test_adversarial_incomplete_push_is_not_silently_replaced_by_a_pull(
    session: Session, attack: str
) -> None:
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"first", counter=1)
    tree.insert("bitcoin", b"bob", b"second", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    before = _head(session)
    leaf = tree.leaf_blob("bitcoin", b"alice")
    assert leaf is not None
    request = messages.WARDLookup(address=b"alice", app_id="bitcoin", proof=[])
    if attack == "witness_commit_only":
        request.witness_commit = b"c" * 32
    elif attack == "witness_key_only":
        request.witness_entry_key = b"k" * 32
    elif attack == "proof_only":
        request.proof = tree.get_proof("bitcoin", b"alice")
    else:
        request.identity = ward.make_leaf_identity(leaf.key_type, leaf.identity)
    previous = session.client.app.ward_proof_callback
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    try:
        _reject(session, request)
    finally:
        session.client.app.ward_proof_callback = previous
    assert _head(session) == before
    valid, member, counter = ward.lookup(
        session, "bitcoin", b"alice", tree.get_proof("bitcoin", b"alice"), leaf=leaf
    )
    assert valid and member and counter == before[0]


def test_adversarial_replayed_membership_cannot_revive_a_deleted_leaf(
    session: Session,
) -> None:
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"first", counter=1)
    tree.insert("bitcoin", b"bob", b"second", counter=1)
    entry_key = tree._ek("bitcoin", b"alice", "address", 0)
    old_leaf = tree.leaf_blob("bitcoin", b"alice")
    old_proof = tree.get_proof("bitcoin", b"alice")
    assert old_leaf is not None
    ward.debug_set_root(session, tree.get_root_hash())
    valid, member, _ = ward.lookup(
        session, "bitcoin", b"alice", old_proof, leaf=old_leaf
    )
    assert valid and member
    tree.del_leaf(entry_key)
    ward.debug_set_root(session, tree.get_root_hash())
    before = _head(session)
    valid, _, _ = ward.lookup(session, "bitcoin", b"alice", old_proof, leaf=old_leaf)
    assert valid is False
    assert _head(session) == before
    honest = ward.build_proof_ack(tree, entry_key)
    valid, member, counter = ward.lookup(
        session,
        "bitcoin",
        b"alice",
        list(honest.proof),
        witness_entry_key=honest.witness_entry_key,
        witness_commit=honest.witness_commit,
    )
    assert valid and not member and counter == before[0]


@pytest.mark.parametrize(
    "scope",
    [{"app_id": "ethereum"}, {"key_type": "label"}, {"device_id": 1}, {"device_id": 256}],
)
def test_adversarial_host_cannot_choose_the_scope(
    session: Session, scope: dict
) -> None:
    """The WARD service fills in an entry's domain, key type and device slot; the host
    may only omit them or repeat the service's values. A host naming another app's
    domain, a key type, or a device slot is refused before any screen or proof pull
    (slot 256 included: it no longer wraps to slot 0)."""
    tree = _tree()
    tree.insert("bitcoin", b"alice", b"first", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    before = _head(session)

    _reject(
        session,
        messages.WARDQueueUpdate(address=b"alice", new_value=b"evil", **scope),
    )
    _reject(session, messages.WARDLookup(address=b"alice", proof=[], **scope))
    assert _head(session) == before
    assert ward.list_pending(session)[0] == []
