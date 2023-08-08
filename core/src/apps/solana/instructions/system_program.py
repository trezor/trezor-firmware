from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_output, confirm_properties
from trezor.wire import ProcessError

from ..constants import ADDRESS_RW, ADDRESS_SIG, ADDRESS_SIG_READ_ONLY
from . import SYSTEM_PROGRAM_ID, Instruction

if TYPE_CHECKING:
    from typing import Awaitable

    from ..types import RawInstruction

INS_CREATE_ACCOUNT = 0
INS_TRANSFER = 2
INS_CREATE_ACCOUNT_WITH_SEED = 3


def handle_system_program_instruction(
    raw_instruction: RawInstruction, signer_pub_key: bytes
) -> Awaitable[None]:
    program_id, _, _ = raw_instruction
    assert base58.encode(program_id) == SYSTEM_PROGRAM_ID

    instruction = _get_instruction(raw_instruction)

    instruction.parse()
    instruction.validate(signer_pub_key)
    return instruction.show()


def _get_instruction(raw_instruction: RawInstruction) -> Instruction:
    _, _, data = raw_instruction

    assert data.remaining_count() >= 4
    instruction_id = int.from_bytes(data.read(4), "little")
    data.seek(0)

    if instruction_id == INS_CREATE_ACCOUNT:
        return CreateAccountInstruction(raw_instruction)
    elif instruction_id == INS_TRANSFER:
        return TransferInstruction(raw_instruction)
    elif instruction_id == INS_CREATE_ACCOUNT_WITH_SEED:
        return CreateAccountWithSeedInstruction(raw_instruction)
    else:
        # TODO SOL: blind signing
        raise ProcessError("Unknown system program instruction")


class CreateAccountInstruction(Instruction):
    PROGRAM_ID = SYSTEM_PROGRAM_ID
    INSTRUCTION_ID = INS_CREATE_ACCOUNT

    lamports: int
    space: int
    owner: bytes
    funding_account: bytes
    created_account: bytes

    def get_data_template(self) -> list[tuple]:
        return [
            ("lamports", "u64"),
            ("space", "u64"),
            ("owner", "pubkey"),
        ]

    def get_accounts_template(self) -> list[tuple[str, int]]:
        return [("funding_account", ADDRESS_SIG), ("created_account", ADDRESS_RW)]

    def validate(self, signer_pub_key: bytes) -> None:
        if self.funding_account != signer_pub_key:
            raise ProcessError("Invalid funding account")

    def show(self) -> Awaitable[None]:
        return confirm_properties(
            "create_account",
            "Create Account",
            (
                ("Lamports", str(self.lamports)),
                ("Space", str(self.space)),
                ("Owner", base58.encode(self.owner)),
                ("Funding Account", base58.encode(self.funding_account)),
                ("New Account", base58.encode(self.created_account)),
            ),
        )


class TransferInstruction(Instruction):
    PROGRAM_ID = SYSTEM_PROGRAM_ID
    INSTRUCTION_ID = INS_TRANSFER

    amount: int

    source: bytes
    destination: bytes

    def get_data_template(self) -> list[tuple]:
        return [
            ("amount", "u64"),
        ]

    def get_accounts_template(self) -> list[tuple[str, int]]:
        return [("source", ADDRESS_SIG), ("destination", ADDRESS_RW)]

    def validate(self, signer_pub_key: bytes) -> None:
        if self.source != signer_pub_key:
            raise ProcessError("Invalid source account")

        # TODO SOL: validate max amount?

    def show(self) -> Awaitable[None]:
        return confirm_output(
            base58.encode(self.destination),
            f"{format_amount(self.amount, 8)} SOL",
            br_code=ButtonRequestType.Other,
        )


class CreateAccountWithSeedInstruction(Instruction):
    PROGRAM_ID = SYSTEM_PROGRAM_ID
    INSTRUCTION_ID = INS_CREATE_ACCOUNT_WITH_SEED

    base: bytes
    seed: str
    lamports: int
    space: int
    owner: bytes

    funding_account: bytes
    created_account: bytes
    base_account: bytes | None

    def get_data_template(self) -> list[tuple]:
        return [
            ("base", "pubkey"),
            ("seed", "str"),
            ("lamports", "u64"),
            ("space", "u64"),
            ("owner", "pubkey"),
        ]

    def get_accounts_template(self) -> list[tuple]:
        return [
            ("funding_account", ADDRESS_SIG),
            ("created_account", ADDRESS_RW),
            ("base_account", ADDRESS_SIG_READ_ONLY, True),
        ]

    def validate(self, signer_pub_key: bytes) -> None:
        if self.funding_account != signer_pub_key:
            raise ProcessError("Invalid funding account")

    def show(self) -> Awaitable[None]:
        props = [
            ("Base", base58.encode(self.base)),
            ("Seed", self.seed),
            ("Lamports", str(self.lamports)),
            ("Space", str(self.space)),
            ("Owner", base58.encode(self.owner)),
            ("Funding Account", base58.encode(self.funding_account)),
            ("Created Account", base58.encode(self.created_account)),
        ]

        if self.base_account is not None:
            props.append(("Base Account", base58.encode(self.base_account)))

        return confirm_properties("create_account", "Create Account", props)
