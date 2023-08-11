from trezor.utils import BufferReader

from .utils import read_compact_u16


def parse_instructions(
    serialized_tx: BufferReader,
) -> list[tuple[int, list[int], BufferReader]]:
    num_of_instructions = read_compact_u16(serialized_tx)

    instructions: list[tuple[int, list[int], BufferReader]] = []
    for _ in range(num_of_instructions):
        program_index = serialized_tx.get()

        num_of_accounts = read_compact_u16(serialized_tx)
        accounts: list[int] = []
        for _ in range(num_of_accounts):
            assert serialized_tx.remaining_count() > 0
            account_index = serialized_tx.get()
            accounts.append(account_index)

        data_length = read_compact_u16(serialized_tx)
        data = BufferReader(serialized_tx.read(data_length))

        instructions.append((program_index, accounts, data))

    return instructions
