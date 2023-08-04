from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.ui.layouts import confirm_properties
from trezor.wire import ProcessError

from ..constants import ADDRESS_READ_ONLY, ADDRESS_RW
from . import STAKE_PROGRAM_ID, Instruction

if TYPE_CHECKING:
    from typing import Awaitable

    from ..types import RawInstruction

INS_INITIALIZE_STAKE = 0


def handle_stake_program_instruction(
    raw_instruction: RawInstruction, signer_pub_key: bytes
) -> Awaitable[None]:
    program_id, _, data = raw_instruction

    assert base58.encode(program_id) == STAKE_PROGRAM_ID
    assert data.remaining_count() >= 4

    instruction = _get_instruction(raw_instruction)

    instruction.parse()
    instruction.validate(signer_pub_key)
    return instruction.show()


def _get_instruction(raw_instruction: RawInstruction) -> Instruction:
    _, _, data = raw_instruction

    instruction_id = int.from_bytes(data.read(4), "little")
    data.seek(0)

    if instruction_id == INS_INITIALIZE_STAKE:
        return InitializeStakeInstruction(raw_instruction)
    else:
        # TODO SOL: blind signing
        raise ProcessError("Unknown system program instruction")


class InitializeStakeInstruction(Instruction):
    PROGRAM_ID = STAKE_PROGRAM_ID
    INSTRUCTION_ID = INS_INITIALIZE_STAKE

    staker: bytes
    withdrawer: bytes
    unix_timestamp: int
    epoch: int
    custodian: bytes
    uninitialized_stake_account: bytes
    rent_sysvar: bytes

    def parse(self) -> None:
        assert self.data.remaining_count() == 116
        assert len(self.accounts) == 2

        instruction_id = int.from_bytes(self.data.read(4), "little")
        assert instruction_id == INS_INITIALIZE_STAKE

        # TODO SOL: validate staker, withdrawer, custodian
        self.staker = self.data.read(32)
        self.withdrawer = self.data.read(32)
        # TODO SOL: should be signed int but from_bytes doesn't take the third arg
        self.unix_timestamp = int.from_bytes(self.data.read(8), "little")
        self.epoch = int.from_bytes(self.data.read(8), "little")
        self.custodian = self.data.read(32)

        (
            self.uninitialized_stake_account,
            uninitialized_stake_account_type,
        ) = self.accounts[0]
        assert uninitialized_stake_account_type == ADDRESS_RW

        self.rent_sysvar, rent_sysvar_type = self.accounts[1]
        assert rent_sysvar_type == ADDRESS_READ_ONLY

    def validate(self, signer_pub_key: bytes) -> None:
        # TODO SOL: validation
        pass

    def show(self) -> Awaitable[None]:
        return confirm_properties(
            "initialize_stake",
            "Initialize Stake",
            (
                ("Staker", base58.encode(self.staker)),
                ("Withdrawer", base58.encode(self.withdrawer)),
                ("Unix Timestamp", str(self.unix_timestamp)),
                ("Epoch", str(self.epoch)),
                ("Custodian", base58.encode(self.custodian)),
                ("Stake Account", base58.encode(self.uninitialized_stake_account)),
                # TODO SOL: probably doesn't need to be displayed
                ("Rent Sysvar", base58.encode(self.rent_sysvar)),
            ),
        )
