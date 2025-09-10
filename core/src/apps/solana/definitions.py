from typing import TYPE_CHECKING

from trezor.messages import SolanaTokenInfo

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from typing_extensions import Self


class Definitions:
    """Class that holds Solana token definitions."""

    def __init__(self, tokens: dict[bytes, SolanaTokenInfo] | None = None) -> None:
        self._tokens = tokens or {}

    @classmethod
    def from_encoded(cls, encoded_token: AnyBytes | None) -> Self:
        from apps.common.definitions import decode_definition

        tokens: dict[bytes, SolanaTokenInfo] = {}

        # get token definition
        if encoded_token is not None:
            token = decode_definition(encoded_token, SolanaTokenInfo)
            tokens[bytes(token.mint)] = token

        return cls(tokens)

    def get_token(self, mint: bytes) -> SolanaTokenInfo | None:
        return self._tokens.get(mint)


def unknown_token(mint: bytes) -> SolanaTokenInfo:
    return SolanaTokenInfo(
        mint=mint,
        symbol="[UNKN]",
        name="Unknown token",
    )
