from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_output, confirm_properties
from trezor.wire import ProcessError

from ..constants import ADDRESS_RW, ADDRESS_SIG, ADDRESS_SIG_READ_ONLY
from ..parsing.utils import read_string
from . import SYSTEM_PROGRAM_ID

if TYPE_CHECKING:
    from typing import Awaitable

    from ..types import Instruction

INS_CREATE_ACCOUNT = 0
INS_TRANSFER = 2
INS_CREATE_ACCOUNT_WITH_SEED = 3


def handle_system_program_instruction(
    instruction: Instruction, signer_pub_key: bytes
) -> Awaitable[None]:
    program_id, _, data = instruction

    assert base58.encode(program_id) == SYSTEM_PROGRAM_ID
    assert data.remaining_count() >= 4

    instruction_id = int.from_bytes(data.read(4), "little")
    data.seek(0)

    if instruction_id == INS_CREATE_ACCOUNT:
        return _handle_create_account(instruction, signer_pub_key)
    if instruction_id == INS_TRANSFER:
        return _handle_transfer(instruction, signer_pub_key)
    if instruction_id == INS_CREATE_ACCOUNT_WITH_SEED:
        return _handle_create_account_with_seed(instruction, signer_pub_key)
    else:
        # TODO SOL: blind signing
        raise ProcessError("Unknown system program instruction")


def _handle_create_account(
    instruction: Instruction, signer_pub_key: bytes
) -> Awaitable[None]:
    lamports, space, owner, funding_account, new_account = _parse_create_account(
        instruction
    )
    _validate_create_account(funding_account, signer_pub_key)
    return _show_create_account(lamports, space, owner, funding_account, new_account)


def _parse_create_account(
    instruction: Instruction,
) -> tuple[int, int, bytes, bytes, bytes]:
    _, accounts, data = instruction

    assert data.remaining_count() == 52
    assert len(accounts) == 2

    instruction_id = int.from_bytes(data.read(4), "little")
    assert instruction_id == INS_CREATE_ACCOUNT

    lamports = int.from_bytes(data.read(8), "little")
    space = int.from_bytes(data.read(8), "little")
    owner = data.read(32)

    funding_account, funding_account_type = accounts[0]
    assert funding_account_type == ADDRESS_SIG

    new_account, new_account_type = accounts[1]
    assert new_account_type == ADDRESS_RW

    return lamports, space, owner, funding_account, new_account


def _validate_create_account(funding_account: bytes, signer_pub_key: bytes) -> None:
    if funding_account != signer_pub_key:
        raise ProcessError("Invalid funding account")


def _show_create_account(
    lamports: int, space: int, owner: bytes, funding_account: bytes, new_account: bytes
) -> Awaitable[None]:
    return confirm_properties(
        "create_account",
        "Create Account",
        (
            ("Lamports", str(lamports)),
            ("Space", str(space)),
            ("Owner", base58.encode(owner)),
            ("Funding Account", base58.encode(funding_account)),
            ("New Account", base58.encode(new_account)),
        ),
    )


def _handle_transfer(
    instruction: Instruction, signer_pub_key: bytes
) -> Awaitable[None]:
    amount, source, destination = _parse_transfer(instruction)
    _validate_transfer(source, signer_pub_key)
    return _show_transfer(destination, amount)


def _parse_transfer(instruction: Instruction) -> tuple[int, bytes, bytes]:
    _, accounts, data = instruction

    assert data.remaining_count() == 12
    assert len(accounts) == 2

    instruction_id = int.from_bytes(data.read(4), "little")
    assert instruction_id == INS_TRANSFER

    amount = int.from_bytes(data.read(8), "little")

    source, source_account_type = accounts[0]
    assert source_account_type == ADDRESS_SIG

    destination, destination_account_type = accounts[1]
    assert destination_account_type == ADDRESS_RW

    return amount, source, destination


def _validate_transfer(source: bytes, signer_pub_key: bytes):
    if source != signer_pub_key:
        raise ProcessError("Invalid source account")

    # TODO SOL: validate max amount?


def _show_transfer(destination: bytes, amount: int) -> Awaitable[None]:
    return confirm_output(
        base58.encode(destination),
        f"{format_amount(amount, 8)} SOL",
        br_code=ButtonRequestType.Other,
    )


def _handle_create_account_with_seed(
    instruction: Instruction, signer_address: bytes
) -> Awaitable[None]:
    (
        base,
        seed,
        lamports,
        space,
        owner,
        funding_account,
        created_account,
        base_account,
    ) = _parse_create_account_with_seed(instruction)
    _validate_create_account_with_seed(funding_account, signer_address)
    return _show_create_account_with_seed(
        base,
        seed,
        lamports,
        space,
        owner,
        funding_account,
        created_account,
        base_account,
    )


def _parse_create_account_with_seed(
    instruction: Instruction,
) -> tuple[bytes, str, int, int, bytes, bytes, bytes, bytes | None]:
    _, accounts, data = instruction

    # assert len(data) == 52
    assert len(accounts) == 2

    instruction_id = int.from_bytes(data.read(4), "little")
    assert instruction_id == INS_CREATE_ACCOUNT_WITH_SEED

    base = data.read(32)
    seed = read_string(data)
    lamports = int.from_bytes(data.read(8), "little")
    space = int.from_bytes(data.read(8), "little")
    owner = data.read(32)

    funding_account, funding_account_type = accounts[0]
    assert funding_account_type == ADDRESS_SIG

    created_account, created_account_type = accounts[1]
    assert created_account_type == ADDRESS_RW

    base_account = None
    if len(accounts) == 3:
        base_account, base_account_type = accounts[2]
        assert base_account_type == ADDRESS_SIG_READ_ONLY

    return (
        base,
        seed,
        lamports,
        space,
        owner,
        funding_account,
        created_account,
        base_account,
    )


def _validate_create_account_with_seed(
    funding_account: bytes, signer_pub_key: bytes
) -> None:
    # TODO SOL: pass for now since we don't have the proper mnemonic
    pass
    # if funding_account != signer_pub_key:
    #     raise ProcessError("Invalid funding account")


def _show_create_account_with_seed(
    base: bytes,
    seed: str,
    lamports: int,
    space: int,
    owner: bytes,
    funding_account: bytes,
    created_account: bytes,
    base_account: bytes | None,
) -> Awaitable[None]:
    props = [
        ("Base", base58.encode(base)),
        ("Seed", seed),
        ("Lamports", str(lamports)),
        ("Space", str(space)),
        ("Owner", base58.encode(owner)),
        ("Funding Account", base58.encode(funding_account)),
        ("Created Account", base58.encode(created_account)),
    ]

    if base_account:
        props.append(("Base Account", base58.encode(base_account)))

    return confirm_properties("create_account", "Create Account", props)
