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

    instruction = _get_instruction(raw_instruction)

    instruction.parse()
    instruction.validate(signer_pub_key)
    return instruction.show()


def _get_instruction(raw_instruction: RawInstruction) -> Instruction:
    _, _, data = raw_instruction

    assert data.remaining_count() >= 4
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

    def get_data_template(self) -> list[tuple]:
        return [
            ("staker", "pubkey"),
            ("withdrawer", "pubkey"),
            # TODO SOL: should be signed int but from_bytes doesn't take the third arg
            ("unix_timestamp", "u64"),
            ("epoch", "u64"),
            ("custodian", "pubkey"),
        ]

    def get_accounts_template(self) -> list[tuple]:
        return [
            ("uninitialized_stake_account", ADDRESS_RW),
            ("rent_sysvar", ADDRESS_READ_ONLY),
        ]

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
