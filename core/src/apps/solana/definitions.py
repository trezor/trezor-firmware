from typing import TYPE_CHECKING

from trezor.messages import SolanaTokenInfo

if TYPE_CHECKING:
    from typing_extensions import Self


class Definitions:
    """Class that holds Solana token definitions."""

    def __init__(self, tokens: dict[bytes, SolanaTokenInfo]) -> None:
        self._tokens = tokens

    @classmethod
    def from_encoded(
        cls,
        encoded_token: bytes | None,
    ) -> Self:
        from apps.common.definitions import decode_definition

        tokens: dict[bytes, SolanaTokenInfo] = {}

        # get token definition
        if encoded_token is not None:
            token = decode_definition(encoded_token, SolanaTokenInfo)
            tokens[token.mint] = token

        return cls(tokens)

    def get_token(self, mint: bytes) -> SolanaTokenInfo:
        UNKNOWN_TOKEN = SolanaTokenInfo(
            mint=b"",
            program_id="",
            name="Unknown token",
            ticker="[UNKN]",
        )
        return self._tokens.get(mint, UNKNOWN_TOKEN)
