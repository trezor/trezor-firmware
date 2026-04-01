import pytest

from card import Card
from card_inner import (
    MAX_PIN_ATTEMPTS,
    InvalidPinError,
    LogRecord,
    NotAuthenticatedError,
    Pin,
    PinAttemptsExceededError,
)
from crypto import aead_decrypt, aead_encrypt, generate_keypair, public_key
from reader import session


def test_card():
    card_private, _ = generate_keypair()
    card = Card(card_private)

    reader_private, _ = generate_keypair()
    attacker_private, _ = generate_keypair()

    note = b"dummy_note"
    seed = b"dummy_seed"
    metadata = b"dummy_metadata"
    pin = Pin(b"1234")
    empty_pin = Pin(b"")

    # Backup
    with session(card, reader_private) as reader:
        reader.wipe()
        reader.authenticate(empty_pin, note)
        encryption_key = reader.set_pin(pin)
        reader.write_encrypted_seed(aead_encrypt(encryption_key, seed))
        reader.write_metadata(metadata)

    # Healthcheck (without authentication)
    with session(card, reader_private) as reader:
        assert reader.read_metadata() == metadata
        assert reader.read_pin_counter() == MAX_PIN_ATTEMPTS
        assert reader.read_successful_access_log_record() == LogRecord(reader.static_public, note)
        assert reader.read_unsuccessful_access_log_records() == [None] * MAX_PIN_ATTEMPTS

    # MAX_PIN_ATTEMPTS - 1 unsuccessful recovery attempts
    for _ in range(MAX_PIN_ATTEMPTS - 1):
        with session(card, attacker_private) as reader:
            with pytest.raises(InvalidPinError):
                reader.authenticate(empty_pin, note)

    attacker_public = public_key(attacker_private)
    reader_public = public_key(reader_private)

    # Healthcheck
    with session(card, reader_private) as reader:
        assert reader.read_metadata() == metadata
        assert reader.read_pin_counter() == 1
        assert reader.read_successful_access_log_record() == LogRecord(reader_public, note)
        assert reader.read_unsuccessful_access_log_records() == [LogRecord(attacker_public, note)] * (
            MAX_PIN_ATTEMPTS - 1
        ) + [None]

    # Recovery
    with session(card, reader_private) as reader:
        encryption_key = reader.authenticate(pin, note)
        decrypted_seed = aead_decrypt(encryption_key, reader.read_encrypted_seed())
    assert decrypted_seed == seed

    # Healthcheck
    with session(card, reader_private) as reader:
        record = reader.read_successful_access_log_record()
        assert record is not None
        assert record.public_key == reader_public
        assert record.note == note
        assert reader.read_unsuccessful_access_log_records() == [None] * MAX_PIN_ATTEMPTS

    # Operations forbidden without authentication
    with session(card, reader_private) as reader:
        with pytest.raises(NotAuthenticatedError):
            reader.set_pin(empty_pin)
        with pytest.raises(NotAuthenticatedError):
            reader.write_encrypted_seed(b"")
        with pytest.raises(NotAuthenticatedError):
            reader.write_metadata(metadata)
        with pytest.raises(NotAuthenticatedError):
            reader.read_encrypted_seed()

    # Wipe and backup again
    with session(card, reader_private) as reader:
        reader.wipe()
        reader.authenticate(empty_pin, note)
        encryption_key = reader.set_pin(pin)
        reader.write_encrypted_seed(aead_encrypt(encryption_key, seed))
        reader.write_metadata(metadata)

    # MAX_PIN_ATTEMPTS unsuccessful recovery attempts
    for _ in range(MAX_PIN_ATTEMPTS - 1):
        with session(card, attacker_private) as reader:
            with pytest.raises(InvalidPinError):
                reader.authenticate(Pin(b""), note)

    with session(card, attacker_private) as reader:
        with pytest.raises(PinAttemptsExceededError):
            reader.authenticate(Pin(b""), note)

    # Card is wiped after exceeding pin attempts
    with session(card, reader_private) as reader:
        assert reader.read_pin_counter() == MAX_PIN_ATTEMPTS
