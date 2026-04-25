# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from . import exceptions, messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session


@workflow(capability=messages.Capability.Solana)
def get_public_key(
    session: "Session",
    address_n: List[int],
    show_display: bool,
) -> bytes:
    return session.call(
        messages.SolanaGetPublicKey(address_n=address_n, show_display=show_display),
        expect=messages.SolanaPublicKey,
    ).public_key


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


@workflow(capability=messages.Capability.Solana)
def get_authenticated_address(
    session: "Session",
    address_n: List[int],
    show_display: bool,
    chunkify: bool = False,
) -> messages.SolanaAddress:
    return session.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
            chunkify=chunkify,
        ),
        expect=messages.SolanaAddress,
    )


@workflow(capability=messages.Capability.Solana)
def sign_tx(
    session: "Session",
    address_n: List[int],
    serialized_tx: bytes,
    additional_info: Optional[messages.SolanaTxAdditionalInfo],
    payment_req: Optional[messages.PaymentRequest] = None,
    chunkify: bool = False,
) -> bytes:
    return session.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
            additional_info=additional_info,
            payment_req=payment_req,
            chunkify=chunkify,
        ),
        expect=messages.SolanaTxSignature,
    ).signature


class OffchainMessage(ABC):
    """Off-Chain Message Signing Base Class

    This implementation below is optimistic: for incorrect arguments,
    it will produce incorrect message. We leave it up to the wallet
    to verify the message conforms to the spec.
    """

    SIGNING_DOMAIN = b"\xffsolana offchain"
    VERSION: ClassVar[int]

    def __init__(self, signers: list[bytes], message: str) -> None:
        self.signers = signers
        self.message = message

    @abstractmethod
    def _write_preamble(self, buf: bytearray) -> None: ...

    def to_bytes(self) -> bytes:
        buf = bytearray(self.SIGNING_DOMAIN)
        buf.append(self.VERSION)
        self._write_preamble(buf)
        buf.extend(self.message.encode("utf-8"))
        return bytes(buf)


class OffchainMessageV0(OffchainMessage):
    """Off-Chain Message Signing v0

    https://docs.anza.xyz/proposals/off-chain-message-signing
    """

    VERSION = 0

    APP_LEN = 32
    PUB_KEY_LEN = 32
    MAX_MSG_LEN_SHORT = 1232

    def __init__(self, app: bytes, signers: list[bytes], message: str) -> None:
        super().__init__(signers, message)
        self.app = app

    class MessageFormat(IntEnum):
        RESTRICTED_ASCII = 0
        UTF8_SHORT = 1
        UTF8_LONG = 2

    def message_format(self) -> MessageFormat:
        preamble_len = 0x35 + len(self.signers) * self.PUB_KEY_LEN
        combined_len = preamble_len + len(self.message.encode("utf-8"))

        if combined_len <= self.MAX_MSG_LEN_SHORT:
            if all(0x20 <= ord(c) <= 0x7E for c in self.message):
                return self.MessageFormat.RESTRICTED_ASCII
            return self.MessageFormat.UTF8_SHORT
        return self.MessageFormat.UTF8_LONG

    def _write_preamble(self, buf: bytearray) -> None:
        buf.extend(self.app)
        buf.append(self.message_format())
        buf.append(len(self.signers))
        for signer in self.signers:
            buf.extend(signer)
        msg_len = len(self.message.encode("utf-8"))
        buf.extend(msg_len.to_bytes(2, "little"))


@workflow(capability=messages.Capability.Solana)
def sign_message(
    session: "Session",
    address_n: List[int],
    message: bytes,
    chunkify: bool = False,
) -> bytes:
    return session.call(
        messages.SolanaSignMessage(
            address_n=address_n, message=message, chunkify=chunkify
        ),
        expect=messages.SolanaMessageSignature,
    ).signature


class Envelope:
    """Signed Off-Chain Message Envelope

    Common format for spec v0 and v1:
    * https://docs.anza.xyz/proposals/off-chain-message-signing#envelope
    * https://github.com/solana-foundation/SRFCs/discussions/3
    """

    SIG_LEN = 64

    def __init__(self, signatures: list[bytes], message: bytes) -> None:
        self.signatures = signatures
        self.message = message

    def to_bytes(self) -> bytes:
        buf = bytearray()
        buf.append(len(self.signatures))
        for signature in self.signatures:
            buf.extend(signature)
        buf.extend(self.message)
        return bytes(buf)


@workflow(capability=messages.Capability.Solana)
def verify_message(
    session: "Session",
    envelope: bytes,
    chunkify: bool = False,
) -> bool:
    try:
        session.call(
            messages.SolanaVerifyMessage(envelope=envelope, chunkify=chunkify),
            expect=messages.Success,
        )
        return True
    except exceptions.TrezorFailure:
        return False
