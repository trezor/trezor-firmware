"""Device tests for the CKB SPHINCS+ message sign/verify flows.

The happy paths go through the trezorlib client helpers; the rejection tests
send the protobuf directly so they can put malformed values on the wire that the
client would never produce.
"""

import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import TrezorFailure

from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx, spx_ref
from .test_sign_sphincs_tx import (
    MNEMONIC_FOR_STRENGTH,
    VARIANT,
    VARIANTS_N16,
    VARIANTS_N24,
    VARIANTS_N32,
    _load_sphincs_session,
)

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ckb,
    pytest.mark.models("t3w1"),
    pytest.mark.setup_client(uninitialized=True),
]

MESSAGE = b"Hello Nervos"
SIG_BYTES_V49 = 7856

# FIPS 205 signature sizes per variant ID — an independent copy of the device's
# _VARIANT_SIG_BYTES, checked against real signatures below.
VARIANT_SIG_BYTES = {
    48: 17088,  # SHA2_128F
    49: 7856,  # SHA2_128S
    50: 35664,  # SHA2_192F
    51: 16224,  # SHA2_192S
    52: 49856,  # SHA2_256F
    53: 29792,  # SHA2_256S
    54: 17088,  # SHAKE_128F
    55: 7856,  # SHAKE_128S
    56: 35664,  # SHAKE_192F
    57: 16224,  # SHAKE_192S
    58: 49856,  # SHAKE_256F
    59: 29792,  # SHAKE_256S
}


def test_sphincs_sign_message(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        res = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)
    assert len(res.signature) == SIG_BYTES_V49
    assert res.variant == VARIANT
    assert len(res.public_key) == 32


def test_sphincs_sign_then_verify_roundtrip(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        signed = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        assert ckb.verify_sphincs_message(
            session,
            signed.address,
            signed.public_key,
            MESSAGE,
            signed.signature,
            variant=VARIANT,
        )


def test_sphincs_message_signature_covers_the_ckb_digest(test_ctx: TrezorTestContext):
    # The roundtrip cannot pin the digest construction (sign and verify share
    # _fips205_message), so the digest is recomputed and verified on the host.
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        signed = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)

    message = prevtx.fips205_pure(prevtx.message_digest(MESSAGE))
    try:
        ok = spx_ref.verify_sha2_128s(message, signed.signature, signed.public_key)
    except spx_ref.BuildUnavailable as exc:
        spx_ref.skip_or_fail(exc)

    assert ok, "device signature does not cover the CKB message digest"

    # Guard against the assertion above passing vacuously.
    tampered = bytearray(message)
    tampered[-1] ^= 0x01
    assert not spx_ref.verify_sha2_128s(
        bytes(tampered), signed.signature, signed.public_key
    )


def test_sphincs_verify_rejects_public_key_not_matching_address(
    test_ctx: TrezorTestContext,
):
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        signed = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)

    other = ckb.get_sphincs_address(session, network="Mainnet", variant=48)
    assert other.address != signed.address

    # Raw call: the client helper turns every failure into False, so a boolean
    # assert would also pass on any unrelated refusal.
    with pytest.raises(TrezorFailure, match="Public key does not match address"):
        session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address=other.address,
                public_key=signed.public_key,
                message=MESSAGE,
                variant=VARIANT,
                network="Mainnet",
                signature_total_size=len(signed.signature),
            )
        )


def test_sphincs_verify_rejects_tampered_message(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        signed = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)

    assert not ckb.verify_sphincs_message(
        session,
        signed.address,
        signed.public_key,
        MESSAGE + b"!",
        signed.signature,
        variant=VARIANT,
    )


def test_sphincs_verify_rejects_wrong_signature_size(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    addr = ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)

    with pytest.raises(TrezorFailure, match="Invalid signature size"):
        session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address=addr.address,
                public_key=addr.public_key,
                message=MESSAGE,
                variant=VARIANT,
                network="Mainnet",
                signature_total_size=SIG_BYTES_V49 + 1,
            )
        )


# Consensus goldens: PUB_SEED (pk[0:n]) pins the HKDF info strings, PK.root
# (pk[n:2n]) pins the vendored SPHINCS+ keygen — spx_ref.py cannot catch either
# moving, since it builds from the same vendored sources. Regenerate only with a
# deliberate consensus change; every user's address moves with these.
_EXPECTED_PUBLIC_KEY = {
    48: "039d22a9fd452e14a7185ba56ea7ad8c72a2de8e306fd5a5226711df86d4aa2e",
    49: "039d22a9fd452e14a7185ba56ea7ad8c158a386451dbee00384796e9288e9471",
    54: "039d22a9fd452e14a7185ba56ea7ad8cb92a44bceef6aef4182baaad528342b5",
    55: "039d22a9fd452e14a7185ba56ea7ad8c7fd52e4773577c3bfdcb9bb4fde3b80e",
}

# Derived from the keys above with an independent implementation of the lock
# script's hashing; without them the lock_args step is free to move.
_EXPECTED_LOCK_ARGS = {
    48: "0106d8a5a915fa44c84835fb78bb1431a94a91dbbbd0bcc186a75635a1bdd8df",
    49: "e6d92a948203f8b16a9326431b32ce1acd68c567462124b70f1c6d2a5b88f876",
    54: "ed0f988a75da4d750dbc2308ecd2ca89cd61ebef860de90501849151538d9851",
    55: "af6f39838c36f35a327b5c18007b206001c51864f3b02e50333cd258c21afbc5",
}

# Beyond lock_args these pin the per-network code hash and hash-type byte; the
# Testnet pair is otherwise never exercised.
_EXPECTED_ADDRESS = {
    "Mainnet": (
        "ckb1qqcz6dvc97r9a097mwdfxc8yq5cw6v4dhrsskshmhecdsvf07l8d7q0xmy4ffqsrlz"
        "ck4yexgvdn9ns6e45v2e6xyyjtwrcud549hz8cwclwtx07"
    ),
    "Testnet": (
        "ckt1qq28aja4c5f8mxpwuymz6tptksn8sq7696cqd52saz90dj42pfl27qhxmy4ffqsrlz"
        "ck4yexgvdn9ns6e45v2e6xyyjtwrcud549hz8cwc02mr5v"
    ),
}


def test_sphincs_address_matches_golden(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    for network, expected in _EXPECTED_ADDRESS.items():
        resp = ckb.get_sphincs_address(session, network=network, variant=VARIANT)
        assert resp.address == expected, f"{network} address moved"


def test_sphincs_n16_variants_share_key_material(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    public_keys = {}
    lock_args = {}
    for variant in (48, 49, 54, 55):
        resp = ckb.get_sphincs_address(session, network="Mainnet", variant=variant)
        assert resp.variant == variant
        assert len(resp.public_key) == 32  # 2*n for n=16
        assert len(resp.lock_args) == 32
        public_keys[variant] = bytes(resp.public_key).hex()
        lock_args[variant] = bytes(resp.lock_args).hex()

    # PUB_SEED is shared across parameter sets; only PK.root differs.
    assert len({pk[:32] for pk in public_keys.values()}) == 1
    assert len({pk[32:] for pk in public_keys.values()}) == len(public_keys)
    assert public_keys == _EXPECTED_PUBLIC_KEY
    assert lock_args == _EXPECTED_LOCK_ARGS


def _open_verify_stream(session, address, public_key, variant, total) -> None:
    """Send a verify request and stop at the first TXSIGCHUNK request: every
    up-front check passed, and the caller now controls the chunk stream."""
    res = session.call(
        messages.CKBSphincsPlusVerifyMessage(
            address=address,
            public_key=public_key,
            message=MESSAGE,
            variant=variant,
            network="Mainnet",
            signature_total_size=total,
        ),
        expect=messages.CKBTxRequest,
    )
    assert res.request_type == messages.CKBTxRequestType.TXSIGCHUNK


def _start_verify_stream(session) -> None:
    addr = ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)
    _open_verify_stream(session, addr.address, addr.public_key, VARIANT, SIG_BYTES_V49)


@pytest.mark.parametrize(
    "strength,variants",
    [
        pytest.param(16, VARIANTS_N16, id="n16"),
        pytest.param(24, VARIANTS_N24, id="n24"),
        pytest.param(32, VARIANTS_N32, id="n32"),
    ],
)
def test_sphincs_signature_sizes_match_the_variant_table(
    test_ctx: TrezorTestContext, strength, variants
):
    # The only check of the non-default size-table rows against real output, and
    # for n=24/32 the only signing exercise at all. The verify leg needs both
    # directions: rejecting a wrong total still passes with a wrong table entry,
    # so the true total must also be shown to reach the chunk stream.
    session = _load_sphincs_session(test_ctx, MNEMONIC_FOR_STRENGTH[strength])

    for variant in variants:
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
            signed = ckb.sign_sphincs_message(session, MESSAGE, variant=variant)

        assert len(signed.signature) == VARIANT_SIG_BYTES[variant]
        assert len(signed.public_key) == 2 * strength
        assert signed.variant == variant

        _open_verify_stream(
            session,
            signed.address,
            signed.public_key,
            variant,
            VARIANT_SIG_BYTES[variant],
        )
        with pytest.raises(TrezorFailure, match="Empty signature chunk"):
            session.call(messages.CKBTxAckSigChunk(signature=b""))

        with pytest.raises(TrezorFailure, match="Invalid signature size"):
            session.call(
                messages.CKBSphincsPlusVerifyMessage(
                    address=signed.address,
                    public_key=signed.public_key,
                    message=MESSAGE,
                    variant=variant,
                    network="Mainnet",
                    signature_total_size=VARIANT_SIG_BYTES[variant] + 1,
                )
            )


def test_sphincs_verify_rejects_invalid_variant(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. variant"):
        session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address="ckb1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
                public_key=b"\x00" * 32,
                message=MESSAGE,
                variant=47,
                network="Mainnet",
                signature_total_size=SIG_BYTES_V49,
            )
        )


def test_sphincs_verify_rejects_invalid_network(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address="ckb1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
                public_key=b"\x00" * 32,
                message=MESSAGE,
                variant=VARIANT,
                network="Devnet",
                signature_total_size=SIG_BYTES_V49,
            )
        )


def test_sphincs_verify_rejects_empty_signature_chunk(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    _start_verify_stream(session)
    with pytest.raises(TrezorFailure, match="Empty signature chunk"):
        session.call(messages.CKBTxAckSigChunk(signature=b""))


def test_sphincs_verify_rejects_oversized_signature_stream(
    test_ctx: TrezorTestContext,
):
    session = _load_sphincs_session(test_ctx)
    _start_verify_stream(session)
    session.call(
        messages.CKBTxAckSigChunk(signature=b"\x00" * 4096),
        expect=messages.CKBTxRequest,
    )
    with pytest.raises(TrezorFailure, match="Signature exceeds declared size"):
        session.call(
            messages.CKBTxAckSigChunk(signature=b"\x00" * (SIG_BYTES_V49 - 4096 + 1))
        )


def test_sphincs_verify_rejects_a_trickled_signature_stream(
    test_ctx: TrezorTestContext,
):
    # 1-byte chunks: the total is fine, the chunk count is the DoS vector.
    session = _load_sphincs_session(test_ctx)
    _start_verify_stream(session)
    with pytest.raises(TrezorFailure, match="Too many signature chunks"):
        for _ in range(ckb._MAX_SIG_CHUNKS + 1):
            session.call(
                messages.CKBTxAckSigChunk(signature=b"\x00"),
                expect=messages.CKBTxRequest,
            )


def test_sphincs_verify_rejects_wrong_public_key_length(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with pytest.raises(TrezorFailure, match="public key length"):
        session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address="ckb1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
                public_key=b"\x00" * 31,
                message=MESSAGE,
                variant=VARIANT,
                network="Mainnet",
                signature_total_size=SIG_BYTES_V49,
            )
        )
