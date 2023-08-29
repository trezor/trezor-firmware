from typing import TYPE_CHECKING

from ..constants import ADDRESS_SIZE
from ..parsing.utils import read_string

if TYPE_CHECKING:
    from . import Instruction


def parse_data_template(instruction: Instruction) -> None:
    template = instruction.data_template

    instruction_id = int.from_bytes(instruction.data.read(4), "little")
    assert instruction_id == instruction.instruction_id

    data = instruction.data

    for template_item in template:
        assert len(template_item) >= 2

        attribute = template_item[0]
        type = template_item[1]
        size = int(template_item[2]) if len(template_item) > 2 else None
        is_optional = template_item[3] if len(template_item) > 3 else False

        if type in ("u64", "i64"):
            if data.remaining_count() < 8:
                if is_optional:
                    continue
                else:
                    raise Exception(f"Missing value for {attribute}")

            value = int.from_bytes(data.read(8), "little")
            instruction.set_parsed_data(attribute, value)
        elif type == "pubkey":
            if data.remaining_count() < ADDRESS_SIZE:
                if is_optional:
                    continue
                else:
                    raise Exception(f"Missing value for {attribute}")

            value = data.read(ADDRESS_SIZE)
            instruction.set_parsed_data(attribute, value)
        elif type == "bytes":
            if data.remaining_count() == 0:
                if is_optional:
                    continue
                else:
                    raise Exception(f"Missing value for {attribute}")

            value = data.read(size)
            instruction.set_parsed_data(attribute, value)
        elif type == "string":
            if data.remaining_count() == 1:
                if is_optional:
                    continue
                else:
                    raise Exception(f"Missing value for {attribute}")

            value = read_string(data)
            instruction.set_parsed_data(attribute, value)
        else:
            raise Exception(f"Unknown type {attribute} {type}")


def parse_accounts_template(instruction: Instruction) -> None:
    template = instruction.accounts_template

    for i, template_item in enumerate(template):
        assert len(template_item) >= 2

        # TODO SOL - check the indexes
        attribute = template_item[0]
        type = template_item[2]

        is_optional = False
        if len(template_item) == 4:
            is_optional = template_item[3]

        if i >= len(instruction.accounts):
            if is_optional:
                instruction.set_parsed_account(attribute, None)
                continue
            else:
                raise Exception(f"Missing account for {attribute}")

        instruction_account = instruction.accounts[i]
        if len(instruction_account) == 2:
            account, account_type = instruction_account
            assert account_type == type
            instruction.set_parsed_account(attribute, account)
        else:
            lookup_table_account, index, account_type = instruction_account
            assert account_type == type
            instruction.set_parsed_account(attribute, (lookup_table_account, index))
