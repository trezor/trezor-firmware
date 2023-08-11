from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader

from .template import templates

def find_template(
    value:          any,
    template_list:  list,
    template_prop:  str
) -> dict:
    # using generator object to optimize algo as we are looking for the first and only match
    gen = (
        x for x in template_list
        if x[template_prop] == value
    )
    return next(gen)

def parse_compact(
    serialized_tx: BufferReader
) -> int:
    value = 0
    shift = 0
    while(serialized_tx.remaining_count()):
        B = serialized_tx.get()
        value += (B & 0x7f) << shift
        shift += 7
        if B & 0x80 == 0:
            return value
        
    raise BufferError

def parse_b256(
    serialized_tx: BufferReader
) -> str:
    return "".join("{:02x}".format(x) for x in serialized_tx.read(32))

def parse_header(
    serialized_tx: BufferReader
) -> dict:
    header = dict()

    header["required"]      = serialized_tx.get()
    header["readonly"]      = serialized_tx.get()
    header["notrequired"]   = serialized_tx.get()

    return header

def parse_accounts(
    serialized_tx: BufferReader
) -> list:
    accounts = list()
    count = parse_compact(serialized_tx)
    
    for x in range(count):
        accounts.append(parse_b256(serialized_tx))

    return accounts

def parse_i32(
    serialized_tx: BufferReader
) -> int:
    value = 0
    for x in range(4):
        value += serialized_tx.get() << (8 * x)
    return value

def parse_sized_string(
    serialized_tx: BufferReader
) -> str:
    # read str len
    strlen = parse_i32(serialized_tx)
    # read padding
    serialized_tx.read(4)
    return "".join("{:c}".format(x) for x in serialized_tx.read(strlen))

def parse_basic_family(
    serialized_tx:      BufferReader,
    parameter_template: dict
) -> (int | str):
    if "u32" == parameter_template["name"]:
        return "".join("{:02x}".format(x) for x in reversed(serialized_tx.read(4)))
    elif "i32" == parameter_template["name"]:
        return "".join("{:02x}".format(x) for x in reversed(serialized_tx.read(4)))
    elif "u64" == parameter_template["name"]:
        return "".join("{:02x}".format(x) for x in reversed(serialized_tx.read(8)))
    elif "i64" == parameter_template["name"]:
        return "".join("{:02x}".format(x) for x in reversed(serialized_tx.read(8)))
    elif "String" == parameter_template["name"]:
        return parse_sized_string(serialized_tx)
    elif "Pubkey" == parameter_template["name"]:
        return parse_b256(serialized_tx)
    else:
        raise NotImplementedError

def parse_struct_family(
    serialized_tx:      BufferReader,
    parameter_template: dict
) -> list:
    fields = list()

    for field in parameter_template["fields"]:
        fields.append(parse_parameter(serialized_tx, field))
    
    return fields

def parse_enum_family(
    serialized_tx:      BufferReader,
    parameter_template: dict
) -> dict:
    # return {"int": 0, "text": "Staker"}
    raise NotImplementedError

def parse_parameter(
    serialized_tx:  BufferReader,
    parameter:      dict
) -> (int | str | list | dict):
    # get type template
    parameter_template = find_template(parameter["type"], templates["parameters"], "name")

    if "basic" == parameter_template["family"]:
        return {"name": parameter["name"], "type": parameter["type"], "value": parse_basic_family(serialized_tx, parameter_template)}
    elif "struct" == parameter_template["family"]:
        return {"name": parameter["name"], "type": parameter["type"], "value": parse_struct_family(serialized_tx, parameter_template)}
    elif "enum" == parameter_template["family"]:
        return {"name": parameter["name"], "type": parameter["type"], "value": parse_enum_family(serialized_tx, parameter_template)}
    else:
        raise TypeError

def parse_parameters(
    serialized_tx:          BufferReader,
    instruction_template:   dict
) -> list:
    parameters = list()

    for param in instruction_template["parameters"]:
        parameters.append(parse_parameter(serialized_tx, param))

    return parameters

def parse_program(
    serialized_tx:  BufferReader,
    accounts:       list
) -> dict:
    account_index = serialized_tx.get()

    # create return value
    instruction = dict()

    # get program template
    program_template = find_template(accounts[account_index], templates["programs"], "id")

    # add program name and id to return dict
    instruction["program_name"] = program_template["name"]
    instruction["program_id"] = program_template["id"]


    # get account references
    account_num = parse_compact(serialized_tx)
    instruction["accounts"] = list()
    for x in range(account_num):
        instruction["accounts"].append(accounts[serialized_tx.get()])
    
    # get instruction data length (not used)
    instruction["data_length"] = parse_compact(serialized_tx)

    # get instruction id
    instruction_id = parse_i32(serialized_tx)

    # get instruction template
    instruction_template = find_template(instruction_id, program_template["instructions"], "id")

    # add instruction name
    instruction["name"] = instruction_template["name"]

    # parse instruction parameters
    instruction["parameters"] = parse_parameters(serialized_tx, instruction_template)

    return instruction

def parse_instructions(
    serialized_tx:  BufferReader,
    accounts:       list
) -> dict:
    instructions = list()
    instruction_count = parse_compact(serialized_tx)

    for x in range(instruction_count):
        instructions.append(parse_program(serialized_tx, accounts))

    return instructions

def parse_message(
    serialized_tx: BufferReader
) -> dict:
    
    message = dict()

    message["header"]       = parse_header(serialized_tx)
    message["accounts"]     = parse_accounts(serialized_tx)
    message["blockhash"]    = parse_b256(serialized_tx)
    message["instructions"] = parse_instructions(serialized_tx, message["accounts"])

    if serialized_tx.remaining_count():
        raise BufferError

    return message
