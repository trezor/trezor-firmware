from micropython import const
from typing import TYPE_CHECKING, Sequence

from trezor.utils import BufferReader
from trezor.wire import DataError

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from enum import IntEnum

    from typing_extensions import Self
else:
    IntEnum = object


class OffchainMessage:
    SIGNING_DOMAIN = b"\xffsolana offchain"

    def __init__(self, signers: Sequence[AnyBytes], message: str) -> None:
        self.signers = signers
        self.message = message

    @classmethod
    def _from_reader(cls, reader: BufferReader) -> "OffchainMessage":
        if reader.read_memoryview(len(cls.SIGNING_DOMAIN)) != cls.SIGNING_DOMAIN:
            raise DataError("Invalid signing domain")

        version = reader.get()
        if version == 0:
            return OffchainMessageV0._from_reader(reader)
        raise DataError(f"Unsupported version: {version}")

    @classmethod
    def from_bytes(cls, data: AnyBytes) -> "OffchainMessage":
        try:
            return cls._from_reader(BufferReader(data))
        except EOFError:
            raise DataError("Message too short")


class OffchainMessageV0(OffchainMessage):

    APP_DOMAIN_LEN = const(32)
    MAX_COMBINED_MSG_LEN_SHORT = const(1232)
    MAX_COMBINED_MSG_LEN = const(65535)

    def __init__(
        self, signers: Sequence[AnyBytes], message: str, app: AnyBytes, format: int
    ) -> None:
        super().__init__(signers, message)
        self.app = app
        self.format = format

    class MessageFormat(IntEnum):
        ASCII_SHORT = const(0)
        UTF8_SHORT = const(1)
        UTF8_LONG = const(2)

        @classmethod
        def max_len(cls, format: int) -> int:
            if format in (cls.ASCII_SHORT, cls.UTF8_SHORT):
                return OffchainMessageV0.MAX_COMBINED_MSG_LEN_SHORT
            if format == cls.UTF8_LONG:
                return OffchainMessageV0.MAX_COMBINED_MSG_LEN
            raise DataError(f"Invalid message format: {format}")

    @classmethod
    def _from_reader(cls, reader: BufferReader) -> Self:
        from apps.common.readers import read_uint16_le
        from apps.common.signverify import is_printable_ascii

        from .constants import ADDRESS_SIZE

        app = reader.read_memoryview(cls.APP_DOMAIN_LEN)

        format = reader.get()
        combined_len = len(reader.buffer)
        if combined_len > cls.MessageFormat.max_len(format):
            raise DataError("Message is too long")

        n_signers = reader.get()
        if n_signers == 0:
            raise DataError("At least one signer is required")
        signers = [reader.read_memoryview(ADDRESS_SIZE) for _ in range(n_signers)]

        message_len = read_uint16_le(reader)
        if message_len == 0:
            raise DataError("Message cannot be empty")
        message_bytes = reader.read_memoryview(message_len)
        if reader.remaining_count() != 0:
            raise DataError("Invalid message length")
        if format == cls.MessageFormat.ASCII_SHORT and not is_printable_ascii(
            message_bytes
        ):
            raise DataError("Invalid message format")
        try:
            message = str(message_bytes, "utf-8")
        except UnicodeError:
            raise DataError("Invalid message encoding")

        return cls(signers, message, app, format)


class Envelope:
    def __init__(
        self,
        signatures: Sequence[AnyBytes],
        message_bytes: AnyBytes,
    ) -> None:
        self.signatures = signatures
        self.message = OffchainMessage.from_bytes(message_bytes)
        # we keep the raw bytes around for signature verification
        self._message_bytes = message_bytes

        if len(self.signatures) != len(self.message.signers):
            raise DataError("Number of signatures must match number of signers")

    @classmethod
    def _from_reader(cls, reader: BufferReader) -> Self:
        from .constants import SIGNATURE_SIZE

        n_signatures = reader.get()
        signatures = [
            reader.read_memoryview(SIGNATURE_SIZE) for _ in range(n_signatures)
        ]

        message_bytes = reader.read_memoryview()

        return cls(signatures, message_bytes)

    @classmethod
    def from_bytes(cls, data: AnyBytes) -> Self:
        try:
            return cls._from_reader(BufferReader(data))
        except EOFError:
            raise DataError("Envelope too short")

    def verify(self) -> None:
        from trezor.crypto.curve import ed25519

        for signature, signer in zip(self.signatures, self.message.signers):
            if not ed25519.verify(signer, signature, self._message_bytes):
                raise DataError("Invalid signature")
