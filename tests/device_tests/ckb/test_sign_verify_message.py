import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from . import prevtx

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("t3w1")]

MAINNET_ADDRESS_0 = (
    "ckb1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsq"
    "g2l882x57v5q8tzu78ggz50c6c46k39rcdwx5zg"
)
TESTNET_ADDRESS_0 = (
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsq"
    "g2l882x57v5q8tzu78ggz50c6c46k39rcrudmgs"
)
PATH_0 = "m/44h/309h/0h/0/0"
MESSAGE = "This is an example of a signed message."
# blake160 of the public key at PATH_0; the payload both addresses above encode.
LOCK_ARGS_0 = bytes.fromhex("0af9cea353cca00eb173c7420547e358aead128f")


def assert_signs_ckb_digest(signature: bytes, message: str) -> None:
    """The signature must cover the digest CKB wallets sign for ``message``.

    The device's own verify_message cannot check this: it derives the digest
    with the same helper the signing side uses, so both would move together.
    """
    digest = prevtx.message_digest(message.encode())
    assert prevtx.recover_lock_args(signature, digest) == LOCK_ARGS_0


def test_sign_message_mainnet(session: Session):
    sig = ckb.sign_message(
        session,
        parse_path(PATH_0),
        MESSAGE,
        network="Mainnet",
        chunkify=True,
    )
    assert sig.address == MAINNET_ADDRESS_0
    assert len(sig.signature) == 65
    assert_signs_ckb_digest(sig.signature, MESSAGE)


def test_sign_message_testnet(session: Session):
    sig = ckb.sign_message(
        session,
        parse_path(PATH_0),
        MESSAGE,
        network="Testnet",
        chunkify=True,
    )
    assert sig.address == TESTNET_ADDRESS_0
    assert len(sig.signature) == 65
    assert_signs_ckb_digest(sig.signature, MESSAGE)


def test_sign_verify_roundtrip_mainnet(session: Session):
    message = MESSAGE
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    result = ckb.verify_message(
        session,
        sig.address,
        sig.signature,
        message,
        network="Mainnet",
        chunkify=True,
    )
    assert result is True


def test_sign_verify_roundtrip_testnet(session: Session):
    message = "Hello CKB Testnet!"
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Testnet", chunkify=True
    )
    result = ckb.verify_message(
        session,
        sig.address,
        sig.signature,
        message,
        network="Testnet",
        chunkify=True,
    )
    assert result is True


def test_verify_wrong_message(session: Session):
    message = MESSAGE
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    result = ckb.verify_message(
        session,
        sig.address,
        sig.signature,
        message + "tampered",
        network="Mainnet",
        chunkify=True,
    )
    assert result is False


def test_verify_wrong_signature(session: Session):
    message = MESSAGE
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    # Corrupt S: a mangled R fails nondeterministically (recovery or address
    # comparison, depending on whether it is a valid x coordinate); a mangled S
    # always recovers to a different key and fails the address comparison.
    bad_sig = (
        sig.signature[:32] + bytes([sig.signature[32] ^ 0xFF]) + sig.signature[33:]
    )
    result = ckb.verify_message(
        session,
        sig.address,
        bad_sig,
        message,
        network="Mainnet",
        chunkify=True,
    )
    assert result is False


@pytest.mark.parametrize("recid", [4, 0xFF])
def test_verify_rejects_out_of_range_recovery_id(session: Session, recid):
    # 4 is the boundary case: only 0..3 are meaningful, so a check written as
    # `> 4` would let it through while still rejecting 0xFF.
    sig = ckb.sign_message(
        session, parse_path(PATH_0), MESSAGE, network="Mainnet", chunkify=True
    )
    bad_sig = sig.signature[:64] + bytes([recid])

    with pytest.raises(TrezorFailure, match="Invalid recovery ID"):
        session.call(
            messages.CKBVerifyMessage(
                address=sig.address,
                signature=bad_sig,
                message=MESSAGE.encode(),
                network="Mainnet",
                chunkify=True,
            )
        )


def test_verify_rejects_unrecoverable_signature(session: Session):
    # r = 0 and s = 0 are outside [1, n-1], so the recovery routine rejects them
    # before any curve arithmetic. Corrupting a byte of a real signature never
    # reaches this branch: it stays in range and fails the address comparison.
    sig = ckb.sign_message(
        session, parse_path(PATH_0), MESSAGE, network="Mainnet", chunkify=True
    )
    unrecoverable = bytes(64) + sig.signature[64:]

    # Anchored: "Invalid signature length" would satisfy a bare
    # "Invalid signature", so the length check failing would look like a pass.
    with pytest.raises(TrezorFailure, match="Invalid signature$"):
        session.call(
            messages.CKBVerifyMessage(
                address=sig.address,
                signature=unrecoverable,
                message=MESSAGE.encode(),
                network="Mainnet",
                chunkify=True,
            )
        )


def test_verify_rejects_wrong_signature_length(session: Session):
    sig = ckb.sign_message(
        session, parse_path(PATH_0), MESSAGE, network="Mainnet", chunkify=True
    )

    with pytest.raises(TrezorFailure, match="Invalid signature length"):
        session.call(
            messages.CKBVerifyMessage(
                address=sig.address,
                signature=sig.signature[:-1],
                message=MESSAGE.encode(),
                network="Mainnet",
                chunkify=True,
            )
        )


def test_verify_wrong_address(session: Session):
    message = MESSAGE
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    sig_other = ckb.sign_message(
        session,
        parse_path("m/44h/309h/0h/0/1"),
        message,
        network="Mainnet",
        chunkify=True,
    )
    result = ckb.verify_message(
        session,
        sig_other.address,
        sig.signature,
        message,
        network="Mainnet",
        chunkify=True,
    )
    assert result is False


def test_rejects_sign_invalid_network(session: Session):
    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        ckb.sign_message(
            session,
            parse_path(PATH_0),
            "test",
            network="Devnet",
            chunkify=True,
        )


def test_rejects_sign_invalid_path(session: Session):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ckb.sign_message(
            session,
            parse_path("m/44h/999h/0h/0/0"),
            "test",
            network="Mainnet",
            chunkify=True,
        )


def test_rejects_verify_invalid_network(session: Session):
    # Raw call: the helper collapses failures to False, and an unknown network
    # also fails the later address comparison (the HRP falls back to testnet),
    # so a boolean assert would stay green with the network check removed.
    sig = ckb.sign_message(
        session, parse_path(PATH_0), MESSAGE, network="Mainnet", chunkify=True
    )

    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        session.call(
            messages.CKBVerifyMessage(
                address=sig.address,
                signature=sig.signature,
                message=MESSAGE.encode(),
                network="Devnet",
                chunkify=True,
            )
        )
