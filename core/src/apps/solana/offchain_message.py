from typing import TYPE_CHECKING

from trezor.utils import empty_bytearray
from trezor.wire import DataError

from .constants import ADDRESS_SIZE

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import SolanaOffchainMessageV1

_SIGNING_DOMAIN = b"\xffsolana offchain"


def serialize_offchain_message(message: SolanaOffchainMessageV1) -> AnyBytes:
    if not 0 < len(message.signers) < 256:
        raise DataError("Invalid number of signers")
    if not all(len(signer) == ADDRESS_SIZE for signer in message.signers):
        raise DataError("Invalid signer address length")
    signers = sorted(set(map(bytes, message.signers)))
    if len(signers) != len(message.signers):
        raise DataError("Signer list must not contain duplicates")

    if not message.message:
        raise DataError("Message cannot be empty")

    msg_bytes = message.message.encode()

    size = len(_SIGNING_DOMAIN) + 2 + ADDRESS_SIZE * len(signers) + len(msg_bytes)
    buf = empty_bytearray(size)

    buf.extend(_SIGNING_DOMAIN)
    buf.append(1)  # version
    buf.append(len(signers))
    for signer in signers:
        buf.extend(signer)
    buf.extend(msg_bytes)

    return buf
