import pytest
from card_inner import (
    MAX_PIN_ATTEMPTS,
    CardInner,
    InvalidPinError,
    LogRecord,
    NotAuthenticatedError,
    Pin,
    PinAttemptsExceededError,
)

from crypto import PublicKey, aead_decrypt, aead_encrypt


def test_card_inner():
    card = CardInner()

    reader_public_key = PublicKey(b"dummy_reader_public_key")
    note = b"dummy_note"

    seed = b"dummy_seed"
    metadata = b"dummy_metadata"
    pin = Pin(b"1234")
    empty_pin = Pin(b"")

    # Backup
    with card.powered(reader_public_key) as powered_card:
        powered_card.wipe()
        powered_card.authenticate(empty_pin, note)
        encryption_key = powered_card.set_pin(pin)
        powered_card.write_encrypted_seed(aead_encrypt(encryption_key, seed))
        powered_card.write_metadata(metadata)

    # Healthcheck (without authentication)
    with card.powered(reader_public_key) as powered_card:
        assert powered_card.read_metadata() == metadata
        assert powered_card.read_pin_counter() == MAX_PIN_ATTEMPTS
        assert powered_card.read_successful_access_log_record() == LogRecord(
            reader_public_key, note
        )
        assert (
            powered_card.read_unsuccessful_access_log_records()
            == [None] * MAX_PIN_ATTEMPTS
        )

    # MAX_PIN_ATTEMPTS - 1 unsuccessful recovery attempts
    attacker_public_key = PublicKey(b"attacker_reader_public_key")
    for _ in range(MAX_PIN_ATTEMPTS - 1):
        with card.powered(attacker_public_key) as powered_card:
            with pytest.raises(InvalidPinError):
                powered_card.authenticate(empty_pin, note)

    # Healthcheck
    with card.powered(reader_public_key) as powered_card:
        assert powered_card.read_metadata() == metadata
        assert powered_card.read_pin_counter() == 1
        assert powered_card.read_successful_access_log_record() == LogRecord(
            reader_public_key, note
        )
        assert powered_card.read_unsuccessful_access_log_records() == [
            LogRecord(attacker_public_key, note)
        ] * (MAX_PIN_ATTEMPTS - 1) + [None]

    # Recovery
    with card.powered(reader_public_key) as powered_card:
        encryption_key = powered_card.authenticate(pin, note)
        decrypted_seed = aead_decrypt(
            encryption_key, powered_card.read_encrypted_seed()
        )
    assert decrypted_seed == seed

    # Healthcheck
    with card.powered(reader_public_key) as powered_card:
        record = powered_card.read_successful_access_log_record()
        assert record is not None
        assert record.public_key == reader_public_key
        assert record.note == note
        assert (
            powered_card.read_unsuccessful_access_log_records()
            == [None] * MAX_PIN_ATTEMPTS
        )

    # Operations forbidden without authentication
    with card.powered() as powered_card:
        with pytest.raises(NotAuthenticatedError):
            powered_card.authenticate(empty_pin, note)
    with card.powered(reader_public_key) as powered_card:
        with pytest.raises(NotAuthenticatedError):
            powered_card.set_pin(empty_pin)
        with pytest.raises(NotAuthenticatedError):
            powered_card.write_encrypted_seed(b"")
        with pytest.raises(NotAuthenticatedError):
            powered_card.write_metadata(metadata)
        with pytest.raises(NotAuthenticatedError):
            powered_card.read_encrypted_seed()

    # Wipe and backup again
    with card.powered(reader_public_key) as powered_card:
        powered_card.wipe()
        powered_card.authenticate(empty_pin, note)
        encryption_key = powered_card.set_pin(pin)
        powered_card.write_encrypted_seed(aead_encrypt(encryption_key, seed))
        powered_card.write_metadata(metadata)

    # MAX_PIN_ATTEMPTS unsuccessful recovery attempts
    for _ in range(MAX_PIN_ATTEMPTS - 1):
        with card.powered(attacker_public_key) as powered_card:
            with pytest.raises(InvalidPinError):
                powered_card.authenticate(Pin(b""), note)

    with card.powered(attacker_public_key) as powered_card:
        with pytest.raises(PinAttemptsExceededError):
            powered_card.authenticate(Pin(b""), note)

    # Card is wiped after exceeding pin attempts
    with card.powered(reader_public_key) as powered_card:
        assert powered_card.read_pin_counter() == MAX_PIN_ATTEMPTS
        assert not powered_card.authenticated
