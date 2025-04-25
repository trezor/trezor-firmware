# generated from __init__.py.mako
# do not edit manually!

<%
CONSTRUCT_TYPES = {
    "u64": "Int64ul",
    "i64": "Int64ul",
    "unix_timestamp": "Int64ul",
    "u32": "Int32ul",
    "i32": "Int32ul",
    "StakeAuthorize": "Int32ul",
    "u8": "Byte",
    "AuthorityType": "Byte",
    "pubkey": "PublicKey",
    "authority": "PublicKey",
    "string": "String",
    "memo": "Memo",
}

INSTRUCTION_TYPES = {
    0: "Pass",
    1: "Byte",
    4: "Int32ul",
}

def upper_snake_case(name):
    return "_".join(name.split(" ")).upper()

def camelcase(name):
    return "".join([word.capitalize() for word in name.split(" ")])

def instruction_id(instruction):
    return "INS_" + upper_snake_case(instruction.name)

def instruction_struct_name(program, instruction):
    return camelcase(program.name) + "_" + camelcase(instruction.name) + "_Instruction"

def instruction_subcon(program, instruction):
    if instruction.id is None:
        return "Pass"
    instruction_id_type = INSTRUCTION_TYPES[program.instruction_id_length]
    return f"Const({instruction.id}, {instruction_id_type})"

%>\
from enum import Enum
from construct import (
    Byte,
    Const,
    GreedyBytes,
    GreedyRange,
    Int32ul,
    Int64ul,
    Optional,
    Pass,
    Select,
    Struct,
)
from .custom_constructs import (
    CompactArray,
    CompactStruct,
    HexStringAdapter,
    Memo,
    OptionalParameter,
    PublicKey,
    String,
)

class Program(Enum):
% for program in programs.programs:
    ${upper_snake_case(program.name)} = "${program.id}"
% endfor

% for program in programs.programs:

${"#"} ${program.name} begin

class ${camelcase(program.name)}Instruction(Enum):
    % for instruction in program.instructions:
    ${upper_snake_case(instruction.name)} = ${instruction.id}
    % endfor

    % for instruction in program.instructions:
${camelcase(program.name)}_${camelcase(instruction.name)} = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(
        % for reference in instruction.references[:instruction.references_required]:
        "${reference}" / Byte,
        % endfor
        % for reference in instruction.references[instruction.references_required:]:
        "${reference}" / Optional(Byte),
        % endfor
        % if instruction.is_multisig:
        "multisig_signers" / Optional(GreedyRange(Byte))
        % endif
    ),
    "data" / CompactStruct(
        "instruction_id" / ${instruction_subcon(program, instruction)},
        % for parameter in instruction.parameters:
            % if parameter["optional"]:
        "${parameter["name"]}" / OptionalParameter(${CONSTRUCT_TYPES.get(parameter.type)}),
            % else:
        "${parameter["name"]}" / ${CONSTRUCT_TYPES.get(parameter.type, "Int64ul")},
            % endif
        % endfor
    ),
)

    % endfor

${camelcase(program.name)}_Instruction = Select(
    %for instruction in program.instructions:
    ${camelcase(program.name)}_${camelcase(instruction.name)},
    %endfor
)

${"#"} ${program.name} end
% endfor

PROGRAMS = {
% for program in programs.programs:
    "${program.id}": ${camelcase(program.name)}_Instruction,
%endfor
}

UnknownInstruction = Struct(
    "program_index" / Byte,
    "accounts" / CompactArray(Byte),
    "data" / HexStringAdapter(GreedyBytes),
)
