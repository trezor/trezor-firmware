from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.ui.layouts import confirm_properties
from trezor.wire import ProcessError

from ..constants import ADDRESS_READ_ONLY, ADDRESS_RW
from . import STAKE_PROGRAM_ID

if TYPE_CHECKING:
    from typing import Awaitable

    from ..types import Instruction

INS_INITIALIZE_STAKE = 0


def handle_stake_program_instruction(
    instruction: Instruction, signer_pub_key: bytes
) -> Awaitable[None]:
    program_id, _, data = instruction

    assert base58.encode(program_id) == STAKE_PROGRAM_ID
    assert data.remaining_count() >= 4

    instruction_id = int.from_bytes(data.read(4), "little")
    data.seek(0)

    if instruction_id == INS_INITIALIZE_STAKE:
        return _handle_initialize_stake(instruction, signer_pub_key)
    else:
        # TODO SOL: blind signing
        raise ProcessError("Unknown stake program instruction")


def _handle_initialize_stake(instruction: Instruction, signer_address: bytes):
    _, accounts, data = instruction

    assert data.remaining_count() == 116
    assert len(accounts) == 2

    instruction_id = int.from_bytes(data.read(4), "little")
    assert instruction_id == INS_INITIALIZE_STAKE

    # TODO SOL: validate staker, withdrawer, custodian
    staker = data.read(32)
    withdrawer = data.read(32)
    # TODO SOL: should be signed int but from_bytes doesn't take the third arg
    unix_timestamp = int.from_bytes(data.read(8), "little")
    epoch = int.from_bytes(data.read(8), "little")
    custodian = data.read(32)

    uninitialized_stake_account, uninitialized_stake_account_type = accounts[0]
    assert uninitialized_stake_account_type == ADDRESS_RW

    rent_sysvar, rent_sysvar_type = accounts[1]
    assert rent_sysvar_type == ADDRESS_READ_ONLY

    return confirm_properties(
        "initialize_stake",
        "Initialize Stake",
        (
            ("Staker", base58.encode(staker)),
            ("Withdrawer", base58.encode(withdrawer)),
            ("Unix Timestamp", str(unix_timestamp)),
            ("Epoch", str(epoch)),
            ("Custodian", base58.encode(custodian)),
            ("Stake Account", base58.encode(uninitialized_stake_account)),
            # TODO SOL: probably doesn't need to be displayed
            ("Rent Sysvar", base58.encode(rent_sysvar)),
        ),
    )
