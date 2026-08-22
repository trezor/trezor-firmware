from typing import TYPE_CHECKING

from trezor.messages import (
    EthereumDisplayFormatInfo,
    EthereumNetworkInfo,
    EthereumTokenInfo,
    SolanaTokenInfo,
)
from trezor.wire import DataError

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import TypeVar

    # NOTE: it's important all DefType variants can't be cross-parsed
    DefType = TypeVar(
        "DefType",
        EthereumNetworkInfo,
        EthereumTokenInfo,
        SolanaTokenInfo,
        EthereumDisplayFormatInfo,
    )


def decode_definition(definition: AnyBytes, expected_type: type[DefType]) -> DefType:
    from trezor.crypto.hashlib import sha256
    from trezor.enums import DefinitionType
    from trezor.protobuf import decode as protobuf_decode
    from trezor.utils import BufferReader
    from trezordefinitions import verify

    from apps.common import readers

    from . import definitions_constants as consts

    r = BufferReader(definition)

    # determine the type number from the expected type
    expected_type_number = DefinitionType.ETHEREUM_NETWORK
    # TODO: can't check equality of MsgDefObjs now, so we check the name
    if expected_type.MESSAGE_NAME == EthereumTokenInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.ETHEREUM_TOKEN
    if expected_type.MESSAGE_NAME == SolanaTokenInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.SOLANA_TOKEN
    if expected_type.MESSAGE_NAME == EthereumDisplayFormatInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.ETHEREUM_DISPLAY_FORMAT

    try:
        # first check magic
        if r.read_memoryview(len(consts.MAGIC)) != consts.MAGIC:
            raise DataError("Invalid definition")

        # second check the format version
        format_version = r.get()
        if format_version not in consts.SUPPORTED_FORMAT_VERSIONS:
            raise DataError("Invalid definition")

        # third check the type of the data
        if r.get() != expected_type_number:
            raise DataError("Definition type mismatch")

        # fourth check data version
        if readers.read_uint32_le(r) < consts.MIN_DATA_VERSION:
            raise DataError("Definition is outdated")

        # get payload
        payload_length = readers.read_uint16_le(r)
        payload = r.read_memoryview(payload_length)

        # at the end compute Merkle tree root hash using
        # provided leaf data (payload with prefix) and proof
        hasher = sha256(b"\x00")
        hasher.update(memoryview(definition)[: r.offset])
        hash = hasher.digest()
        proof_length = r.get()
        for _ in range(proof_length):
            proof_entry = r.read_memoryview(32)
            hash_a = min(hash, proof_entry)  # type: ignore [not assignable to "bytes"]
            hash_b = max(hash, proof_entry)  # type: ignore [not assignable to "bytes"]
            hasher = sha256(b"\x01")
            hasher.update(hash_a)
            hasher.update(hash_b)
            hash = hasher.digest()

        sigmask = r.get()
        signature = r.read_memoryview(64)

        if r.remaining_count():
            raise DataError("Invalid definition")

    except EOFError:
        raise DataError("Invalid definition")

    # verify signature
    try:
        verify(hash, signature, sigmask, format_version)
    except ValueError:
        raise DataError("Invalid definition signature")

    # decode it if it's OK
    try:
        return protobuf_decode(payload, expected_type, True)
    except (ValueError, EOFError):
        raise DataError("Invalid definition")
