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
from .test_sign_sphincs_tx import VARIANT, _load_sphincs_session

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ckb,
    pytest.mark.models("t3w1"),
    pytest.mark.setup_client(uninitialized=True),
]

MESSAGE = b"Hello Nervos"
# SLH-DSA-SHA2-128s, matching VARIANT 49.
SIG_BYTES_V49 = 7856


def test_sphincs_sign_message(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        res = ckb.sign_sphincs_message(session, MESSAGE, variant=VARIANT)
    # The device must stream exactly one full SLH-DSA signature, no more.
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
    # The signature length is fully determined by the variant, so a declared
    # total that does not match it must be refused before anything is buffered.
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


# The whole public key (PUB_SEED || PK.root) for MNEMONIC_SPHINCS. Both halves are
# address-determining consensus, and they come from different places:
#
#   PUB_SEED = pk[0:n] is HKDF-SHA256(salt=zeros, ikm=<3rd sub-phrase entropy>,
#              info="ckb/quantum-purse/sphincs-plus/0"). The info string carries
#              only the account index, so every parameter set sharing an `n`
#              derives the same key material. Scoping it per variant would move
#              every address that has ever been handed out.
#   PK.root  = pk[n:2n] comes out of the vendored SPHINCS+ keygen, so bumping
#              vendor/sphincsplus to a revision that builds the hypertree
#              differently moves addresses too. spx_ref.py cannot catch that: it
#              builds from the same vendored sources the firmware uses.
#
# Pinning both makes either kind of change fail CI instead of silently moving
# every user's addresses. Regenerate only with a deliberate consensus change.
_EXPECTED_PUBLIC_KEY = {
    48: "039d22a9fd452e14a7185ba56ea7ad8c72a2de8e306fd5a5226711df86d4aa2e",
    49: "039d22a9fd452e14a7185ba56ea7ad8c158a386451dbee00384796e9288e9471",
    54: "039d22a9fd452e14a7185ba56ea7ad8cb92a44bceef6aef4182baaad528342b5",
    55: "039d22a9fd452e14a7185ba56ea7ad8c7fd52e4773577c3bfdcb9bb4fde3b80e",
}


def test_sphincs_n16_variants_share_key_material(test_ctx: TrezorTestContext):
    # A 36-word mnemonic carries 3x16 bytes, so exactly these four variants are
    # usable with it. Exercising each also runs spx_get_variant()'s cross-check
    # of the hardcoded length table against the compiled-in params, which would
    # otherwise only ever run for the default variant.

    session = _load_sphincs_session(test_ctx)
    public_keys = {}
    lock_args = {}
    for variant in (48, 49, 54, 55):
        resp = ckb.get_sphincs_address(session, network="Mainnet", variant=variant)
        assert resp.variant == variant
        assert len(resp.public_key) == 32  # 2*n for n=16
        assert len(resp.lock_args) == 32
        public_keys[variant] = bytes(resp.public_key).hex()
        lock_args[variant] = bytes(resp.lock_args)

    assert public_keys == _EXPECTED_PUBLIC_KEY

    # PUB_SEED is shared, so only PK.root distinguishes the keys; the addresses
    # differ further because lock_args also hashes the variant's script flag.
    assert len({pk[:32] for pk in public_keys.values()}) == 1
    assert len({pk[32:] for pk in public_keys.values()}) == 4
    assert len(set(lock_args.values())) == 4


def test_sphincs_verify_rejects_wrong_public_key_length(test_ctx: TrezorTestContext):
    # A wrong-length key must fail as a clean wire error, not as a ValueError
    # escaping the C binding.
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
