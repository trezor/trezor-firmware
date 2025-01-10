from typing import TYPE_CHECKING

from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo
from trezor.wire import DataError

if TYPE_CHECKING:
    from typing_extensions import Self


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
        from apps.common.definitions import decode_definition

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
