from ubinascii import unhexlify
from typing import TYPE_CHECKING

from apps.ethereum import tokens

from trezor import protobuf, wire
from trezor.crypto.curve import ed25519
from trezor.enums import EthereumDefinitionType
from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

from . import helpers, networks

if TYPE_CHECKING:
    from trezor.protobuf import MessageType

    from .networks import NetworkInfo
    from .tokens import TokenInfo


DEFINITIONS_PUBLIC_KEY = b""
MIN_DATA_VERSION = 1
FORMAT_VERSION = "trzd1"

if __debug__:
    DEFINITIONS_DEV_PUBLIC_KEY = unhexlify("db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d")


class EthereumDefinitionParser:
    def __init__(self, definition_bytes: bytes) -> None:
        if len(definition_bytes) <= (8 + 1 + 4 + 64):
            raise wire.DataError("Received Ethereum definition is probably malformed (too few data).")

        self.format_version: str = definition_bytes[:8].rstrip(b'\0').decode("utf-8")
        self.definition_type: int = definition_bytes[8]
        self.data_version: int = int.from_bytes(definition_bytes[9:13], 'big')
        self.clean_payload = definition_bytes[13:-64]
        self.payload = definition_bytes[:-64]
        self.signature = definition_bytes[-64:]


def decode_definition(
    definition: bytes, expected_type: EthereumDefinitionType
) -> NetworkInfo | TokenInfo:
    # check network definition
    parsed_definition = EthereumDefinitionParser(definition)

    # first check format version
    if parsed_definition.format_version != FORMAT_VERSION:
        raise wire.DataError("Used different Ethereum definition format version.")

    # second check the type of the data
    if parsed_definition.definition_type != expected_type:
        raise wire.DataError("Definition of invalid type for Ethereum.")

    # third check data version
    if parsed_definition.data_version < MIN_DATA_VERSION:
        raise wire.DataError("Used Ethereum definition data version too low.")

    # at the end verify the signature
    if not ed25519.verify(DEFINITIONS_PUBLIC_KEY, parsed_definition.signature, parsed_definition.payload):
        error_msg = wire.DataError("Ethereum definition signature is invalid.")
        if __debug__:
            # check against dev key
            if not ed25519.verify(DEFINITIONS_DEV_PUBLIC_KEY, parsed_definition.signature, parsed_definition.payload):
                raise error_msg
        else:
            raise error_msg

    # decode it if it's OK
    if expected_type == EthereumDefinitionType.NETWORK:
        info = protobuf.decode(parsed_definition.clean_payload, EthereumNetworkInfo, True)

        # TODO: temporarily convert to internal class
        if info is not None:
            from .networks import NetworkInfo
            info = NetworkInfo(
                chain_id=info.chain_id,
                slip44=info.slip44,
                shortcut=info.shortcut,
                name=info.name,
                rskip60=info.rskip60
            )
    else:
        info = protobuf.decode(parsed_definition.clean_payload, EthereumTokenInfo, True)

        # TODO: temporarily convert to internal class
        if info is not None:
            from .tokens import TokenInfo
            info = TokenInfo(
                symbol=info.symbol,
                decimals=info.decimals,
                address=info.address,
                chain_id=info.chain_id,
                name=info.name,
            )

    return info


def _get_network_definiton(encoded_network_definition: bytes | None, ref_chain_id: int | None = None) -> NetworkInfo | None:
    if encoded_network_definition is None and ref_chain_id is None:
        return None

    if ref_chain_id is not None:
        # if we have a built-in definition, use it
        network = networks.by_chain_id(ref_chain_id)
        if network is not None:
            return network

    if encoded_network_definition is not None:
        # get definition if it was send
        network = decode_definition(encoded_network_definition, EthereumDefinitionType.NETWORK)

        # check referential chain_id with encoded chain_id
        if ref_chain_id is not None and network.chain_id != ref_chain_id:
            raise wire.DataError("Invalid network definition - chain IDs not equal.")

        return network

    return None


def _get_token_definiton(encoded_token_definition: bytes | None, ref_chain_id: int | None = None, ref_address: bytes | None = None) -> TokenInfo:
    if encoded_token_definition is None and (ref_chain_id is None or ref_address is None):
        return tokens.UNKNOWN_TOKEN

    # if we have a built-in definition, use it
    if ref_chain_id is not None and ref_address is not None:
        token = tokens.token_by_chain_address(ref_chain_id, ref_address)
        if token is not tokens.UNKNOWN_TOKEN:
            return token

    if encoded_token_definition is not None:
        # get definition if it was send
        token = decode_definition(encoded_token_definition, EthereumDefinitionType.TOKEN)

        # check token against ref_chain_id and ref_address
        if (
            (ref_chain_id is None or token.chain_id == ref_chain_id)
            and (ref_address is None or token.address == ref_address)
        ):
            return token

    return tokens.UNKNOWN_TOKEN


class EthereumDefinitions:
    """Class that holds Ethereum definitions - network and tokens. Prefers built-in definitions over encoded ones."""
    def __init__(
        self,
        encoded_network_definition: bytes | None = None,
        encoded_token_definition: bytes | None = None,
        ref_chain_id: int | None = None,
        ref_token_address: bytes | None = None,
    ) -> None:
        self.network = _get_network_definiton(encoded_network_definition, ref_chain_id)
        self.token_dict: dict[bytes, TokenInfo] = dict()

        # if we have some network, we can try to get token
        if self.network is not None:
            token = _get_token_definiton(encoded_token_definition, self.network.chain_id, ref_token_address)
            if token is not tokens.UNKNOWN_TOKEN:
                self.token_dict[token.address] = token


def get_definitions_from_msg(msg: MessageType) -> EthereumDefinitions:
    encoded_network_definition: bytes | None = None
    encoded_token_definition: bytes | None = None
    chain_id: int | None = None
    token_address: str | None = None

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

    # get token_address
    try:
        token_address = helpers.bytes_from_address(msg.to)
    except AttributeError:
        pass

    return EthereumDefinitions(encoded_network_definition, encoded_token_definition, chain_id, token_address)
