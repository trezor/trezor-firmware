from typing import TYPE_CHECKING

from trezor.crypto import base58

if TYPE_CHECKING:
    from trezor.messages import SolanaTxTokenAccountInfo

ASSOCIATED_TOKEN_ACCOUNT_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"

SEED_CONSTANT = "ProgramDerivedAddress"


def assert_is_associated_token_account(
    base_address: bytes,
    token_account_address: bytes,
    token_program: bytes,
    token_mint: bytes,
) -> None:
    from trezor.crypto.hashlib import sha256

    # based on the following sources:
    # https://spl.solana.com/associated-token-account#finding-the-associated-token-account-address
    # https://github.com/solana-labs/solana/blob/8fbe033eaca693ed8c3e90b19bc3f61b32885e5e/sdk/program/src/pubkey.rs#L495
    for seed_bump in range(255, 0, -1):
        seed = (
            base_address
            + token_program
            + token_mint
            + bytes([seed_bump])
            + base58.decode(ASSOCIATED_TOKEN_ACCOUNT_PROGRAM)
            + SEED_CONSTANT.encode("utf-8")
        )

        account = sha256(seed).digest()

        if account == token_account_address:
            return

    raise ValueError


def try_get_token_account_base_address(
    token_account_address: bytes,
    token_program: bytes,
    token_mint: bytes,
    token_accounts_infos: list[SolanaTxTokenAccountInfo],
) -> bytes | None:
    for token_account_info in token_accounts_infos:
        if (
            base58.decode(token_account_info.token_account) == token_account_address
            and base58.decode(token_account_info.token_program) == token_program
            and base58.decode(token_account_info.token_mint) == token_mint
        ):
            base_address = base58.decode(token_account_info.base_address)

            assert_is_associated_token_account(
                base_address,
                token_account_address,
                token_program,
                token_mint,
            )

            return base_address

    return None
