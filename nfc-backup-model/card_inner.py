import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import NewType

from crypto import PublicKey, hmac_hash, random_bytes

logger = logging.getLogger(__name__)

Pin = NewType("Pin", bytes)

MAX_PIN_ATTEMPTS = 10
DEFAULT_PIN = Pin(b"")
STRETCHING_KEY_SIZE_BYTES = 16


class NfcBackupModelError(Exception):
    pass


class NotAuthenticatedError(NfcBackupModelError):
    pass


class PinAttemptsExceededError(NfcBackupModelError):
    pass


class InvalidPinError(NfcBackupModelError):
    pass


@dataclass
class LogRecord:
    public_key: PublicKey
    note: bytes

    def to_bytes(self) -> bytes:
        return self.public_key + self.note


@dataclass
class Storage:
    pin_counter: int = MAX_PIN_ATTEMPTS
    successful_access_log_record: LogRecord | None = None
    unsuccessful_access_log_records: list[LogRecord | None] = field(
        default_factory=lambda: [None] * MAX_PIN_ATTEMPTS
    )
    seed_metadata: bytes = b""
    stretching_key: bytes = b""
    pin_tag: bytes = b""
    encrypted_seed: bytes = b""

    def check_integrity(self) -> bool:
        return True

    @contextmanager
    def atomic_session(self) -> Iterator[None]:
        # This should be implemented so that, in the event of a tear-off,
        # all changes to storage made during the session are rolled back.
        yield


class CardInner:
    def __init__(self) -> None:
        self.storage = Storage()

    @contextmanager
    def powered(
        self, reader_public_key: PublicKey | None = None
    ) -> Iterator["CardInner.PoweredInnerCard"]:
        # `reader_public_key` is not `None` if and only if a secure channel has been
        # initiated between the card and a trezor
        logger.info("CardInner.powered()")
        logger.debug(f"reader_public_key={reader_public_key!r}")
        yield CardInner.PoweredInnerCard(self.storage, reader_public_key)

    class PoweredInnerCard:
        def __init__(
            self, storage: Storage, reader_public_key: PublicKey | None
        ) -> None:
            # This is stored in flash
            self.storage = storage

            # This is stored in RAM
            self.reader_public_key = reader_public_key
            self.authenticated = False

        # | Method                                | Requires PIN | Requires Trezor |
        # | ------------------------------------- | -----------: | --------------: |
        # | check_integrity                       |           no |              no |
        # | wipe                                  |           no |             yes |
        # | authenticate                          |           no |             yes |
        # | set_pin                               |          yes |             yes |
        # | read_pin_counter                      |           no |              no |
        # | read_successful_access_log_record     |           no |              no |
        # | read_unsuccessful_access_log_records  |           no |              no |
        # | read_metadata                         |           no |              no |
        # | read_encrypted_seed                   |          yes |             yes |
        # | write_metadata                        |          yes |             yes |
        # | write_encrypted_seed                  |          yes |             yes |

        def _stretch_pin(self, pin: Pin) -> tuple[bytes, bytes]:
            stretched = hmac_hash(self.storage.stretching_key, pin)
            return stretched[:16], stretched[16:]

        def check_integrity(self) -> bool:
            logger.info("CardInner.check_integrity()")
            result = self.storage.check_integrity()
            logger.debug(f"integrity_status={result}")
            return result

        def wipe(self) -> None:
            logger.info("CardInner.PoweredInnerCard.wipe()")

            if self.reader_public_key is None:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                # This does not necessarily have to be atomic if `encrypted_seed`
                # and `stretching_key` are wiped before `pin_counter` is set
                # to its maximum value
                self.storage.encrypted_seed = b""
                self.storage.stretching_key = random_bytes(STRETCHING_KEY_SIZE_BYTES)
                self.storage.seed_metadata = b""
                self.storage.pin_counter = MAX_PIN_ATTEMPTS
                self.storage.successful_access_log_record = None
                self.storage.unsuccessful_access_log_records = [None] * MAX_PIN_ATTEMPTS
                self.storage.pin_tag, _ = self._stretch_pin(Pin(b""))

            self.authenticated = False

        def authenticate(self, pin: Pin, note: bytes) -> bytes:
            logger.info("CardInner.authenticate()")
            logger.debug(f"pin={pin!r}, note={note!r}")

            if self.reader_public_key is None:
                raise NotAuthenticatedError()

            if self.storage.pin_counter == 0:
                # This is not called unless during the previous PIN attempt the card
                # was powered off after verifying the PIN and before wiping the storage
                self.wipe()
                raise PinAttemptsExceededError()

            # The PIN counter is decremented before the PIN is verified so that an
            # attacker cannot power off the card after PIN verification but before
            # the counter is decremented, thereby bypassing the attempt limit
            with self.storage.atomic_session():
                self.storage.pin_counter -= 1
                self.storage.unsuccessful_access_log_records[
                    MAX_PIN_ATTEMPTS - self.storage.pin_counter - 1
                ] = LogRecord(self.reader_public_key, note)

            tag, stretched_pin = self._stretch_pin(pin)
            if tag != self.storage.pin_tag:
                if self.storage.pin_counter == 0:
                    self.wipe()
                    self.authenticated = False
                    raise PinAttemptsExceededError()
                raise InvalidPinError()

            with self.storage.atomic_session():
                self.storage.successful_access_log_record = LogRecord(
                    self.reader_public_key, note
                )
                self.storage.unsuccessful_access_log_records = [None] * MAX_PIN_ATTEMPTS
                self.storage.pin_counter = MAX_PIN_ATTEMPTS

            self.authenticated = True
            logger.debug(f"stretched_pin={stretched_pin!r}")
            return stretched_pin

        def set_pin(self, pin: Pin) -> bytes:
            logger.info("CardInner.set_pin()")
            logger.debug(f"pin={pin!r}")

            if not self.authenticated:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                self.storage.stretching_key = random_bytes(STRETCHING_KEY_SIZE_BYTES)
                self.storage.pin_tag, stretched_pin = self._stretch_pin(pin)
            logger.debug(f"stretched_pin={stretched_pin!r}")
            return stretched_pin

        def read_pin_counter(self) -> int:
            logger.info("CardInner.read_pin_counter()")
            with self.storage.atomic_session():
                pin_counter = self.storage.pin_counter
            logger.debug(f"pin_counter={pin_counter}")
            return pin_counter

        def read_successful_access_log_record(self) -> LogRecord | None:
            logger.info("CardInner.read_successful_access_log_record()")
            record = self.storage.successful_access_log_record
            logger.debug(f"record={record!r}")
            return record

        def read_unsuccessful_access_log_records(self) -> list[LogRecord | None]:
            logger.info("CardInner.read_unsuccessful_access_log_records()")
            records = list(self.storage.unsuccessful_access_log_records)
            logger.debug(f"records={records!r}")
            return records

        def read_metadata(self) -> bytes:
            logger.info("CardInner.read_metadata()")
            seed_metadata = self.storage.seed_metadata
            logger.debug(f"seed_metadata={seed_metadata!r}")
            return seed_metadata

        def read_encrypted_seed(self) -> bytes:
            logger.info("CardInner.read_encrypted_seed()")

            if not self.authenticated:
                raise NotAuthenticatedError()

            encrypted_seed = self.storage.encrypted_seed
            logger.debug(f"encrypted_seed={encrypted_seed!r}")
            return encrypted_seed

        def write_metadata(self, seed_metadata: bytes) -> None:
            logger.info("CardInner.write_metadata()")
            logger.debug(f"seed_metadata={seed_metadata!r}")

            if not self.authenticated:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                self.storage.seed_metadata = seed_metadata

        def write_encrypted_seed(self, encrypted_seed: bytes) -> None:
            logger.info("CardInner.write_encrypted_seed()")
            logger.debug(f"encrypted_seed={encrypted_seed!r}")

            if not self.authenticated:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                self.storage.encrypted_seed = bytes(encrypted_seed)

        # TODO: Add methods for setting and getting NDEF record
