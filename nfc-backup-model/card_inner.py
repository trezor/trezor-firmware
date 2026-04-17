import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import NewType

from crypto import (
    AEAD_NONCE_SIZE_BYTES,
    DecryptionError,
    PublicKey,
    aead_decrypt,
    aead_encrypt,
    hmac_hash,
    random_bytes,
)

logger = logging.getLogger(__name__)

Pin = NewType("Pin", bytes)
Timestamp = NewType("Timestamp", bytes)

MAX_PIN_ATTEMPTS = 10
DEFAULT_PIN = Pin(b"")
STRETCHING_KEY_SIZE_BYTES = 16
SALT_SIZE_BYTES = 16
AEAD_KEY_SIZE_BYTES = 32


class NfcBackupModelError(Exception):
    pass


class NotAuthenticatedError(NfcBackupModelError):
    pass


class PinAttemptsExceededError(NfcBackupModelError):
    pass


class InvalidPinError(NfcBackupModelError):
    pass


@dataclass
class Storage:
    @contextmanager
    def atomic_session(self) -> Iterator[None]:
        # This should be implemented so that, in the event of a tear-off,
        # all changes to storage made during the session are rolled back.
        yield

    # The storage is divided into six atomic sections. Some sections may
    # be merged if this is advantageous from an implementation perspective.

    # First atomic section
    salt: bytes = b""
    encrypted_data_encryption_key: bytes = b""

    # Second atomic section
    pin_counter: int = MAX_PIN_ATTEMPTS
    # `pin_counter` is reduntant since
    # `pin_counter = len([r for r in unsuccessful_access_log_records if r is not None])`
    successful_access_log_record: PublicKey | None = None
    unsuccessful_access_log_records: list[PublicKey | None] = field(
        default_factory=lambda: [None] * MAX_PIN_ATTEMPTS
    )

    # Third atomic section
    seed_metadata: bytes = b""

    # Forth section
    encrypted_seed: bytes = b""

    # Fifth section
    last_refresh_timestamp: Timestamp = Timestamp(b"")

    # Sixth section
    # This is the part of memory that is written to most often if the user
    # only performs integrity checks
    flash_bit_error_count: int = 0

    # This function should be automatically called when a flash error is detected
    # while reading data or code from flash
    def increment_flash_bit_error_count(self, count: int = 1) -> None:
        with self.atomic_session():
            self.flash_bit_error_count += count

    def check_integrity(self) -> bool:
        # Go through both the data and program in flash, repair any corruption,
        # and return whether all data is readable after repair
        return True

    def refresh_flash(self) -> None:
        # Go through all the data and program in flash and refresh them to
        # improve data retention
        pass


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
            self.data_encryption_key: bytes | None = None

        # | Method                                | Requires PIN | Requires Trezor |
        # | ------------------------------------- | -----------: | --------------: |
        # | check_integrity                       |           no |              no |
        # | refresh_memory                        |           no |              no |
        # | read_last_refresh_timestamp           |           no |              no |
        # | read_flash_bit_error_count            |           no |              no |
        # | wipe                                  |           no |             yes |
        # | authenticate                          |           no |             yes |
        # | set_pin                               |          yes |             yes |
        # | read_pin_counter                      |           no |              no |
        # | read_successful_access_log_record     |           no |              no |
        # | read_unsuccessful_access_log_records  |           no |              no |
        # | read_metadata                         |           no |              no |
        # | read_seed                             |          yes |             yes |
        # | write_metadata                        |          yes |             yes |
        # | write_seed                            |          yes |             yes |

        @classmethod
        def wrap_data_encryption_key(
            cls, pin: Pin, encryption_key: bytes
        ) -> tuple[bytes, bytes]:
            salt = random_bytes(SALT_SIZE_BYTES)
            # The purpose of the salt is to prevent the use of precomputed tables
            # to brute-force the PIN if an attacker manages to read `salt` and
            # `encrypted_data_encryption_key`
            salted_pin = hmac_hash(pin, salt)
            # The nonce is intentionally constant because the encryption key
            # (`salted_pin`) is guaranteed never to be used twice
            encrypted_data_encryption_key = aead_encrypt(
                salted_pin, bytes(AEAD_NONCE_SIZE_BYTES), encryption_key
            )
            return salt, encrypted_data_encryption_key

        @classmethod
        def unwrap_data_encryption_key(
            cls, pin: Pin, salt: bytes, encrypted_data_encryption_key: bytes
        ) -> bytes:
            salted_pin = hmac_hash(pin, salt)
            data_encryption_key = aead_decrypt(
                salted_pin, bytes(AEAD_NONCE_SIZE_BYTES), encrypted_data_encryption_key
            )
            return data_encryption_key

        def check_integrity(self) -> bool:
            logger.info("CardInner.check_integrity()")
            result = self.storage.check_integrity()
            logger.debug(f"integrity_status={result}")
            return result

        def refresh_memory(self, timestamp: Timestamp) -> None:
            logger.info("CardInner.refresh_memory()")
            logger.debug(f"timestamp={timestamp!r}")
            self.storage.refresh_flash()
            with self.storage.atomic_session():
                self.storage.last_refresh_timestamp = timestamp

        def read_last_refresh_timestamp(self) -> Timestamp:
            logger.info("CardInner.read_last_refresh_timestamp()")
            timestamp = self.storage.last_refresh_timestamp
            logger.debug(f"timestamp={timestamp!r}")
            return timestamp

        def read_flash_bit_error_count(self) -> int:
            logger.info("CardInner.read_flash_bit_error_count()")
            count = self.storage.flash_bit_error_count
            logger.debug(f"flash_bit_error_count={count}")
            return count

        def wipe(self) -> None:
            logger.info("CardInner.PoweredInnerCard.wipe()")

            if self.reader_public_key is None:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                # If `encrypted_data_encryption_key` or `salt` are written in
                # multiple banks, the old values have to be wiped from all
                # banks
                (
                    self.storage.salt,
                    self.storage.encrypted_data_encryption_key,
                ) = self.wrap_data_encryption_key(
                    DEFAULT_PIN, random_bytes(AEAD_KEY_SIZE_BYTES)
                )

            with self.storage.atomic_session():
                self.storage.encrypted_seed = b""

            with self.storage.atomic_session():
                self.storage.seed_metadata = b""

            with self.storage.atomic_session():
                self.storage.pin_counter = MAX_PIN_ATTEMPTS
                self.storage.successful_access_log_record = None
                self.storage.unsuccessful_access_log_records = [None] * MAX_PIN_ATTEMPTS

            # TODO: Decide whether to reset the flash bit error count and
            # last refresh timestamp

            self.authenticated = False

        def authenticate(self, pin: Pin) -> None:
            logger.info("CardInner.authenticate()")
            logger.debug(f"pin={pin!r}")

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
                ] = self.reader_public_key

            try:
                self.data_encryption_key = self.unwrap_data_encryption_key(
                    pin, self.storage.salt, self.storage.encrypted_data_encryption_key
                )
            except DecryptionError:
                if self.storage.pin_counter == 0:
                    self.wipe()
                    self.data_encryption_key = None
                    raise PinAttemptsExceededError()
                raise InvalidPinError()

            with self.storage.atomic_session():
                self.storage.successful_access_log_record = self.reader_public_key
                self.storage.unsuccessful_access_log_records = [None] * MAX_PIN_ATTEMPTS
                self.storage.pin_counter = MAX_PIN_ATTEMPTS

        def set_pin(self, pin: Pin) -> None:
            logger.info("CardInner.set_pin()")
            logger.debug(f"pin={pin!r}")

            if self.data_encryption_key is None:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                # If `encrypted_data_encryption_key` or `salt` are written in
                # multiple banks, the old values have to be wiped from all
                # banks
                (
                    self.storage.salt,
                    self.storage.encrypted_data_encryption_key,
                ) = self.wrap_data_encryption_key(pin, self.data_encryption_key)

        def read_pin_counter(self) -> int:
            logger.info("CardInner.read_pin_counter()")
            pin_counter = self.storage.pin_counter
            logger.debug(f"pin_counter={pin_counter}")
            return pin_counter

        def read_successful_access_log_record(self) -> PublicKey | None:
            logger.info("CardInner.read_successful_access_log_record()")
            record = self.storage.successful_access_log_record
            logger.debug(f"record={record!r}")
            return record

        def read_unsuccessful_access_log_records(self) -> list[PublicKey | None]:
            logger.info("CardInner.read_unsuccessful_access_log_records()")
            records = list(self.storage.unsuccessful_access_log_records)
            logger.debug(f"records={records!r}")
            return records

        def read_metadata(self) -> bytes:
            logger.info("CardInner.read_metadata()")
            seed_metadata = self.storage.seed_metadata
            logger.debug(f"seed_metadata={seed_metadata!r}")
            return seed_metadata

        def read_seed(self) -> bytes:
            logger.info("CardInner.read_seed()")

            if self.data_encryption_key is None:
                raise NotAuthenticatedError()

            seed = aead_decrypt(
                self.data_encryption_key,
                self.storage.encrypted_seed[:AEAD_NONCE_SIZE_BYTES],
                self.storage.encrypted_seed[AEAD_NONCE_SIZE_BYTES:],
            )
            logger.debug(f"seed={seed!r}")
            return seed

        def write_metadata(self, seed_metadata: bytes) -> None:
            logger.info("CardInner.write_metadata()")
            logger.debug(f"seed_metadata={seed_metadata!r}")

            if self.data_encryption_key is None:
                raise NotAuthenticatedError()

            with self.storage.atomic_session():
                self.storage.seed_metadata = seed_metadata

        def write_seed(self, seed: bytes) -> None:
            logger.info("CardInner.write_seed()")
            logger.debug(f"seed={seed!r}")

            if self.data_encryption_key is None:
                raise NotAuthenticatedError()

            nonce = random_bytes(AEAD_NONCE_SIZE_BYTES)
            encrypted_seed = nonce + aead_encrypt(self.data_encryption_key, nonce, seed)

            with self.storage.atomic_session():
                self.storage.encrypted_seed = encrypted_seed

        # TODO: Add methods for setting and getting NDEF record
