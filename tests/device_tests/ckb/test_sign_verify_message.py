import pytest

from trezorlib import ckb
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

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


def test_sign_message_mainnet(session: Session):
    sig = ckb.sign_message(
        session,
        parse_path(PATH_0),
        "This is an example of a signed message.",
        network="Mainnet",
        chunkify=True,
    )
    assert sig.address == MAINNET_ADDRESS_0
    assert len(sig.signature) == 65


def test_sign_message_testnet(session: Session):
    sig = ckb.sign_message(
        session,
        parse_path(PATH_0),
        "This is an example of a signed message.",
        network="Testnet",
        chunkify=True,
    )
    assert sig.address == TESTNET_ADDRESS_0
    assert len(sig.signature) == 65


def test_sign_verify_roundtrip_mainnet(session: Session):
    message = "This is an example of a signed message."
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
    message = "This is an example of a signed message."
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
    message = "This is an example of a signed message."
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    bad_sig = sig.signature[:-1] + bytes([sig.signature[-1] ^ 0xFF])
    result = ckb.verify_message(
        session,
        sig.address,
        bad_sig,
        message,
        network="Mainnet",
        chunkify=True,
    )
    assert result is False


def test_verify_wrong_address(session: Session):
    message = "This is an example of a signed message."
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
    message = "This is an example of a signed message."
    sig = ckb.sign_message(
        session, parse_path(PATH_0), message, network="Mainnet", chunkify=True
    )
    result = ckb.verify_message(
        session,
        sig.address,
        sig.signature,
        message,
        network="Devnet",
        chunkify=True,
    )
    assert result is False
