import pytest
from card_inner import (
    MAX_PIN_ATTEMPTS,
    CardInner,
    InvalidPinError,
    LogRecord,
    NotAuthenticatedError,
    Pin,
    PinAttemptsExceededError,
    Timestamp,
)

from crypto import (
    PublicKey,
)


def test_card_inner() -> None:
    card = CardInner()

    reader_public_key = PublicKey(b"dummy_reader_public_key")
    note = b"dummy_note"

    seed = b"dummy_seed"
    metadata = b"dummy_metadata"
    pin = Pin(b"1234")
    empty_pin = Pin(b"")
    timestamp = Timestamp((1775661638).to_bytes(4, "big"))

    # Backup
    with card.powered(reader_public_key) as powered_card:
        powered_card.wipe()
        powered_card.authenticate(empty_pin, note)
        powered_card.set_pin(pin)
        powered_card.write_seed(seed)
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
        assert powered_card.read_flash_bit_error_count() == 0
        assert powered_card.read_last_refresh_timestamp() == Timestamp(b"")
        assert powered_card.check_integrity() is True
        powered_card.refresh_memory(timestamp)

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
        assert powered_card.read_flash_bit_error_count() == 0
        assert powered_card.read_last_refresh_timestamp() == timestamp
        assert powered_card.check_integrity() is True

    # Recovery
    with card.powered(reader_public_key) as powered_card:
        powered_card.authenticate(pin, note)
        assert powered_card.read_seed() == seed

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
            powered_card.write_seed(b"")
        with pytest.raises(NotAuthenticatedError):
            powered_card.write_metadata(metadata)
        with pytest.raises(NotAuthenticatedError):
            powered_card.read_seed()

    # Wipe and backup again
    with card.powered(reader_public_key) as powered_card:
        powered_card.wipe()
        powered_card.authenticate(empty_pin, note)
        powered_card.set_pin(pin)
        powered_card.write_seed(seed)
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
        assert not powered_card.data_encryption_key
