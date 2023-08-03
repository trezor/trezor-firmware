from trezor.utils import BufferReader

from .utils import read_compact_u16


def parse_instructions(
    serialized_tx: BufferReader, addresses: list[tuple[bytes, int]]
) -> list[tuple[bytes, list[tuple[bytes, int]], BufferReader]]:
    num_of_instructions = read_compact_u16(serialized_tx)

    instructions: list[tuple[bytes, list[tuple[bytes, int]], BufferReader]] = []
    for _ in range(num_of_instructions):
        program_index = serialized_tx.get()
        assert program_index < len(addresses)

        program_id = addresses[program_index][0]

        num_of_accounts = read_compact_u16(serialized_tx)

        instruction_accounts: list[tuple[bytes, int]] = []
        for _ in range(num_of_accounts):
            assert serialized_tx.remaining_count() > 0
            account_index = serialized_tx.get()
            assert account_index < len(addresses)

            account = addresses[account_index]

            instruction_accounts.append(account)

        data_length = read_compact_u16(serialized_tx)
        data = BufferReader(serialized_tx.read(data_length))

        instructions.append((program_id, instruction_accounts, data))

    return instructions
