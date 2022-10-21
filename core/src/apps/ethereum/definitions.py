from typing import TYPE_CHECKING
from ubinascii import unhexlify

from trezor import protobuf, utils, wire
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.enums import EthereumDefinitionType
from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

from apps.common import readers
from apps.ethereum import networks, tokens

if TYPE_CHECKING:
    from typing import Any, TypeVar

    DefType = TypeVar("DefType", EthereumNetworkInfo, EthereumTokenInfo)

DEFINITIONS_PUBLIC_KEY = b""
MIN_DATA_VERSION = 1
FORMAT_VERSION = b"trzd1"

if __debug__:
    DEFINITIONS_DEV_PUBLIC_KEY = unhexlify(
        "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d"
    )


def decode_definition(definition: bytes, expected_type: type[DefType]) -> DefType:
    # check network definition
    r = utils.BufferReader(definition)
    expected_type_number = EthereumDefinitionType.NETWORK
    if expected_type.MESSAGE_NAME == EthereumTokenInfo.MESSAGE_NAME:
        expected_type_number = EthereumDefinitionType.TOKEN

    try:
        # first check format version
        if r.read_memoryview(5) != FORMAT_VERSION:
            raise wire.DataError("Invalid definition format")

        # second check the type of the data
        if r.get() != expected_type_number:
            raise wire.DataError("Definition type mismatch")

        # third check data version
        if readers.read_uint32_be(r) < MIN_DATA_VERSION:
            raise wire.DataError("Definition is outdated")

        # get payload
        payload_length_in_bytes = readers.read_uint16_be(r)
        payload = r.read_memoryview(payload_length_in_bytes)
        end_of_payload = r.offset

        # at the end compute Merkle tree root hash using
        # provided leaf data (payload with prefix) and proof
        no_of_proofs = r.get()

        hash = sha256(b"\x00" + definition[:end_of_payload]).digest()
        for _ in range(no_of_proofs):
            proof = r.read_memoryview(32)
            hash_a = min(hash, proof)
            hash_b = max(hash, proof)
            hash = sha256(b"\x01" + hash_a + hash_b).digest()

        signed_tree_root = r.read_memoryview(64)

    except EOFError:
        raise wire.DataError("Invalid Ethereum definition")

    # verify signature
    if not ed25519.verify(DEFINITIONS_PUBLIC_KEY, signed_tree_root, hash):
        error_msg = wire.DataError("Invalid definition signature")
        if __debug__:
            # check against dev key
            if not ed25519.verify(
                DEFINITIONS_DEV_PUBLIC_KEY,
                signed_tree_root,
                hash,
            ):
                raise error_msg
        else:
            raise error_msg

    # decode it if it's OK
    info = protobuf.decode(payload, expected_type, True)

    return info


def get_and_check_definiton(
    encoded_definition: bytes,
    expected_type: type[DefType],
    ref_chain_id: int | None = None,
) -> DefType:
    decoded_def = decode_definition(encoded_definition, expected_type)

    # check referential chain_id with decoded chain_id
    if ref_chain_id is not None and decoded_def.chain_id != ref_chain_id:
        expected_type_name = "Network"
        if expected_type.MESSAGE_NAME == EthereumTokenInfo.MESSAGE_NAME:
            expected_type_name = "Token"
        raise wire.DataError(f"{expected_type_name} definition mismatch")

    return decoded_def


class Definitions:
    """Class that holds Ethereum definitions - network and tokens.
    Prefers built-in definitions over encoded ones.
    """

    def __init__(
        self,
        encoded_network_definition: bytes | None = None,
        encoded_token_definition: bytes | None = None,
        ref_chain_id: int | None = None,
    ) -> None:
        self.network = networks.UNKNOWN_NETWORK
        self._tokens: dict[bytes, EthereumTokenInfo] = {}

        # get network definition
        if ref_chain_id is not None:
            # if we have a built-in definition, use it
            self.network = (
                networks.by_chain_id(ref_chain_id) or networks.UNKNOWN_NETWORK
            )
        if (
            self.network is networks.UNKNOWN_NETWORK
            and encoded_network_definition is not None
        ):
            self.network = get_and_check_definiton(
                encoded_network_definition, EthereumNetworkInfo, ref_chain_id
            )

        # get token definition
        if encoded_token_definition is not None:
            token = get_and_check_definiton(
                encoded_token_definition, EthereumTokenInfo, self.network.chain_id
            )
            self._tokens[token.address] = token

    def get_token(self, address: bytes) -> EthereumTokenInfo:
        # if we have a built-in definition, use it
        token = tokens.token_by_chain_address(self.network.chain_id, address)
        if token is not None:
            return token

        if address in self._tokens:
            return self._tokens[address]

        return tokens.UNKNOWN_TOKEN


def get_definitions_from_msg(msg: Any) -> Definitions:
    encoded_network_definition: bytes | None = None
    encoded_token_definition: bytes | None = None
    chain_id: int | None = None

    # first try to get both definitions
    try:
        if msg.definitions is not None:
            encoded_network_definition = msg.definitions.encoded_network
            encoded_token_definition = msg.definitions.encoded_token
    except AttributeError:
        pass

    # check if we have network definition, if not give it a last try
    if encoded_network_definition is None:
        try:
            encoded_network_definition = msg.encoded_network
        except AttributeError:
            pass

    # get chain_id
    try:
        chain_id = msg.chain_id
    except AttributeError:
        pass

    return Definitions(encoded_network_definition, encoded_token_definition, chain_id)
