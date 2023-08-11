from typing import TYPE_CHECKING

from .parse_template import parse_accounts_template, parse_data_template

if TYPE_CHECKING:
    from ..types import Address, AddressReference, Data, RawInstruction

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"

SYSTEM_TRANSFER_ID = 2


class Instruction:
    PROGRAM_ID = -1
    INSTRUCTION_ID = -1

    program_id: bytes
    accounts: list[Address | AddressReference]
    data: Data

    def __init__(self, raw_instruction: RawInstruction):
        self.program_id, self.accounts, self.data = raw_instruction

    def get_data_template(self) -> list[tuple]:
        return []

    def get_accounts_template(self) -> list[tuple[str, int]]:
        return []

    def parse(self) -> None:
        parse_data_template(self)
        parse_accounts_template(self)

    def validate(self, signer_pub_key: bytes) -> None:
        pass

    async def show(self) -> None:
        # TODO SOL: blind signing could be here?
        pass


async def handle_instructions(
    instructions: list[RawInstruction], signer_pub_key: bytes
) -> None:
    from trezor.crypto import base58
    from trezor.wire import ProcessError

    from .system_program import handle_system_program_instruction
    from .stake_program import handle_stake_program_instruction

    for raw_instruction in instructions:
        program_id, _, _ = raw_instruction

        encoded_program_id = base58.encode(program_id)

        if encoded_program_id == SYSTEM_PROGRAM_ID:
            await handle_system_program_instruction(raw_instruction, signer_pub_key)
        elif encoded_program_id == STAKE_PROGRAM_ID:
            await handle_stake_program_instruction(raw_instruction, signer_pub_key)
        else:
            # TODO SOL: blind signing for unknown programs
            raise ProcessError(f"Unknown program id: {encoded_program_id}")
