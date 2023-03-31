from typing import TYPE_CHECKING

from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
from trezor.wire import DataError

if TYPE_CHECKING:
    from typing import TypeVar

    from typing_extensions import Self

    DefType = TypeVar("DefType", EthereumNetworkInfo, EthereumTokenInfo)


def decode_definition(definition: bytes, expected_type: type[DefType]) -> DefType:
    from trezor.crypto.cosi import verify as cosi_verify
    from trezor.crypto.hashlib import sha256
    from trezor.enums import EthereumDefinitionType
    from trezor.protobuf import decode as protobuf_decode
    from trezor.utils import BufferReader

    from apps.common import readers

    from . import definitions_constants as consts

    # check network definition
    r = BufferReader(definition)
    expected_type_number = EthereumDefinitionType.NETWORK
    # TODO: can't check equality of MsgDefObjs now, so we check the name
    if expected_type.MESSAGE_NAME == EthereumTokenInfo.MESSAGE_NAME:
        expected_type_number = EthereumDefinitionType.TOKEN

    try:
        # first check format version
        if r.read_memoryview(len(consts.FORMAT_VERSION)) != consts.FORMAT_VERSION:
            raise DataError("Invalid Ethereum definition")

        # second check the type of the data
        if r.get() != expected_type_number:
            raise DataError("Definition type mismatch")

        # third check data version
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
            hash_a = min(hash, proof_entry)
            hash_b = max(hash, proof_entry)
            hasher = sha256(b"\x01")
            hasher.update(hash_a)
            hasher.update(hash_b)
            hash = hasher.digest()

        sigmask = r.get()
        signature = r.read_memoryview(64)

        if r.remaining_count():
            raise DataError("Invalid Ethereum definition")

    except EOFError:
        raise DataError("Invalid Ethereum definition")

    # verify signature
    result = cosi_verify(signature, hash, consts.THRESHOLD, consts.PUBLIC_KEYS, sigmask)
    if __debug__:
        debug_result = cosi_verify(
            signature, hash, consts.THRESHOLD, consts.DEV_PUBLIC_KEYS, sigmask
        )
        result = result or debug_result
    if not result:
        raise DataError("Invalid definition signature")

    # decode it if it's OK
    try:
        return protobuf_decode(payload, expected_type, True)
    except ValueError:
        raise DataError("Invalid Ethereum definition")


class Definitions:
    """Class that holds Ethereum definitions - network and tokens.
    Prefers built-in definitions over encoded ones.
    """

    def __init__(
        self, network: EthereumNetworkInfo, tokens: dict[bytes, EthereumTokenInfo]
    ) -> None:
        self.network = network
        self._tokens = tokens

    @classmethod
    def from_encoded(
        cls,
        encoded_network: bytes | None,
        encoded_token: bytes | None,
        chain_id: int | None = None,
        slip44: int | None = None,
    ) -> Self:
        from .networks import UNKNOWN_NETWORK, by_chain_id, by_slip44

        network = UNKNOWN_NETWORK
        tokens: dict[bytes, EthereumTokenInfo] = {}

        # if we have a built-in definition, use it
        if chain_id is not None:
            network = by_chain_id(chain_id)
        elif slip44 is not None:
            network = by_slip44(slip44)
        else:
            # ignore encoded definitions if we can't match them to request details
            return cls(UNKNOWN_NETWORK, {})

        if network is UNKNOWN_NETWORK and encoded_network is not None:
            network = decode_definition(encoded_network, EthereumNetworkInfo)

        if network is UNKNOWN_NETWORK:
            # ignore tokens if we don't have a network
            return cls(UNKNOWN_NETWORK, {})

        if chain_id is not None and network.chain_id != chain_id:
            raise DataError("Network definition mismatch")
        if slip44 is not None and network.slip44 != slip44:
            raise DataError("Network definition mismatch")

        # get token definition
        if encoded_token is not None:
            token = decode_definition(encoded_token, EthereumTokenInfo)
            # Ignore token if it doesn't match the network instead of raising an error.
            # This might help us in the future if we allow multiple networks/tokens
            # in the same message.
            if token.chain_id == network.chain_id:
                tokens[token.address] = token

        return cls(network, tokens)

    def get_token(self, address: bytes) -> EthereumTokenInfo:
        from .tokens import UNKNOWN_TOKEN, token_by_chain_address

        # if we have a built-in definition, use it
        token = token_by_chain_address(self.network.chain_id, address)
        if token is not None:
            return token

        if address in self._tokens:
            return self._tokens[address]

        return UNKNOWN_TOKEN
