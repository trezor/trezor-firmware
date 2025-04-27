from typing import TYPE_CHECKING

from trezor.messages import SolanaTokenInfo

if TYPE_CHECKING:
    from typing_extensions import Self


class Definitions:
    """Class that holds Solana token definitions."""

    def __init__(self, tokens: dict[bytes, SolanaTokenInfo] | None = None) -> None:
        self._tokens = tokens or {}

    @classmethod
    def from_encoded(cls, encoded_token: bytes | None) -> Self:
        from apps.common.definitions import decode_definition

        tokens: dict[bytes, SolanaTokenInfo] = {}

        # get token definition
        if encoded_token is not None:
            token = decode_definition(encoded_token, SolanaTokenInfo)
            tokens[token.mint] = token

        return cls(tokens)

    def has_token(self, mint: bytes) -> bool:
        return mint in self._tokens

    def get_token(self, mint: bytes) -> SolanaTokenInfo:
        token = self._tokens.get(mint)
        if token is not None:
            return token

        return SolanaTokenInfo(
            mint=mint,
            symbol="[UNKN]",
            name="Unknown token",
        )
