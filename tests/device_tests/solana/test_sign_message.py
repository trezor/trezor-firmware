from random import Random

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from trezorlib import exceptions, solana
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

pytestmark = [pytest.mark.altcoin, pytest.mark.solana, pytest.mark.models("core")]

ADDRESS_N = parse_path("m/44h/501h/0h/0h")
ED25519_PRIV_SIZE = 32


@pytest.mark.parametrize(
    ["n_cosigners", "message"],
    [
        pytest.param(0, "Hello, world!", id="ascii"),
        pytest.param(0, "Hello, 🌍! Spëcial châräctérs.", id="utf-8"),
        pytest.param(0, "Much " + "much " * 42 + "longer message.", id="long"),
        pytest.param(2, "Multi-party agreement.", id="multi"),
    ],
)
def test_sign_verify(session: Session, n_cosigners: int, message: str) -> None:
    signer_pub = Ed25519PublicKey.from_public_bytes(
        solana.get_public_key(session, ADDRESS_N, show_display=True)
    )

    rng = Random(0)
    cosigner_privs = [
        Ed25519PrivateKey.from_private_bytes(rng.randbytes(ED25519_PRIV_SIZE))
        for _ in range(n_cosigners)
    ]
    cosigner_pubs = [priv.public_key() for priv in cosigner_privs]

    pubs = cosigner_pubs + [signer_pub]

    offchain_message = solana.OffchainMessageV0(
        app=b"\x00" * solana.OffchainMessageV0.APP_LEN,
        signers=[pub.public_bytes_raw() for pub in pubs],
        message=message,
    ).to_bytes()

    signatures = [priv.sign(offchain_message) for priv in cosigner_privs]
    signatures.append(solana.sign_message(session, ADDRESS_N, offchain_message))

    for pub, sig in zip(pubs, signatures):
        pub.verify(sig, offchain_message)

    envelope = solana.Envelope(signatures, offchain_message).to_bytes()

    assert solana.verify_message(session, envelope)


def test_missing_signer(session: Session) -> None:
    offchain_message = solana.OffchainMessageV0(
        app=b"\x00" * solana.OffchainMessageV0.APP_LEN,
        signers=[b"\x00" * solana.OffchainMessageV0.PUB_KEY_LEN],
        message="Missing signer!",
    ).to_bytes()

    with pytest.raises(
        exceptions.TrezorFailure, match="Requested key not among signers"
    ):
        solana.sign_message(session, ADDRESS_N, offchain_message)


@pytest.mark.parametrize(
    "signatures",
    [
        pytest.param([], id="missing"),
        pytest.param([b"\x00" * (solana.Envelope.SIG_LEN - 1)], id="malformed"),
        pytest.param([b"\x00" * solana.Envelope.SIG_LEN], id="invalid"),
        pytest.param([b"\x00" * solana.Envelope.SIG_LEN] * 2, id="extra"),
    ],
)
def test_invalid_envelope(session: Session, signatures: list[bytes]) -> None:
    offchain_message = solana.OffchainMessageV0(
        app=b"\x00" * solana.OffchainMessageV0.APP_LEN,
        signers=[solana.get_public_key(session, ADDRESS_N, show_display=False)],
        message="Invalid envelope!",
    ).to_bytes()

    solana.sign_message(session, ADDRESS_N, offchain_message)

    envelope = solana.Envelope(signatures, offchain_message).to_bytes()

    assert not solana.verify_message(session, envelope)
