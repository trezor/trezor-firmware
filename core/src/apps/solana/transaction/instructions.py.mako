# generated from instructions.py.mako
# (by running `make solana_templates` in root)
# do not edit manually!

<%
def getProgramId(program):
    return "_" + "_".join(program["name"].upper().split(" ") + ["ID"])

def getInstructionIdText(program, instruction):
    return "_".join([getProgramId(program)] + ["INS"] + instruction["name"].upper().split(" "))

def getClassName(program, instruction):
    return program["name"].replace(" ", "") + instruction["name"].replace(" ", "") + "Instruction"

INT_TYPES = ("u8", "u32", "u64", "i32", "i64", "timestamp", "lamports", "token_amount", "unix_timestamp")

def getPythonType(type):
    if type in INT_TYPES:
        return "int"
    elif type in ("pubkey", "authority"):
        return "Account"
    elif type in ("string", "memo"):
        return "str"
    elif type in programs["types"] and programs["types"][type].get("is_enum"):
        return "int"
    else:
        raise Exception(f"Unknown type: {type}")

def args_tuple(required_parameters, args_dict):
    args = []
    for required_parameter in required_parameters:
        if required_parameter.startswith("#"):
            args.append(required_parameter)
        else:
            args.append(args_dict[required_parameter])
    return repr(tuple(args))

%>\
from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.readers import read_uint32_le, read_uint64_le

from ..types import PropertyTemplate, UIProperty
from ..format import (
    format_int,
    format_lamports,
    format_pubkey,
    format_identity,
    format_token_amount,
    format_unix_timestamp,
)
from .instruction import Instruction
from .parse import (
    parse_byte,
    parse_memo,
    parse_pubkey,
    parse_string,
)

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard

    from ..types import Account, InstructionId, InstructionData

% for program in programs["programs"]:
${getProgramId(program)} = "${program["id"]}"
% endfor

% for program in programs["programs"]:
    % for instruction in program["instructions"]:
      % if isinstance(instruction["id"], int):
${getInstructionIdText(program, instruction)} = const(${instruction["id"]})
      % else:
${getInstructionIdText(program, instruction)} = ${instruction["id"]}
      % endif
    % endfor
% endfor

COMPUTE_BUDGET_PROGRAM_ID = _COMPUTE_BUDGET_PROGRAM_ID
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT = _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE = _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE


def is_system_program_account_creation(instruction: Instruction) -> bool:
    return (
        instruction.program_id == _SYSTEM_PROGRAM_ID
        and instruction.instruction_id in (
            _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT,
            _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
            _SYSTEM_PROGRAM_ID_INS_ALLOCATE,
            _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
        )
    )


def is_atap_account_creation(instruction: Instruction) -> bool:
    return (
        instruction.program_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        and instruction.instruction_id in (
            _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
            _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
        )
    )


def __getattr__(name: str) -> Type[Instruction]:
    def get_id(name: str) -> tuple[str, InstructionId]:
    %for program in programs["programs"]:
        %for instruction in program["instructions"]:
        if name == "${getClassName(program, instruction)}":
            return (${getProgramId(program)}, ${getInstructionIdText(program, instruction)})
        %endfor
    %endfor
        raise AttributeError # Unknown instruction

    id = get_id(name)

    class FakeClass(Instruction):
        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard[Instruction]:
            return ins.program_id == id[0] and ins.instruction_id == id[1]

    return FakeClass


if TYPE_CHECKING:

% for program in programs["programs"]:
    ## generates classes for instructions
    % for instruction in program["instructions"]:
    class ${getClassName(program, instruction)}(Instruction):
        ## generates properties for instruction parameters
        % for parameter in instruction["parameters"]:
        ${parameter["name"]}: ${getPythonType(parameter["type"])}
        % endfor

        ## generates properties for reference accounts
        % for reference in instruction["references"][:instruction["references_required"]]:
        ${reference}: Account
        % endfor
        % for reference in instruction["references"][instruction["references_required"]:]:
        ${reference}: Account | None
        % endfor
    % endfor
% endfor

def get_instruction_id_length(program_id: str) -> int:
% for program in programs["programs"]:
    if program_id == ${getProgramId(program)}:
        return ${program["instruction_id_length"]}
% endfor

    return 0


% for _, type in programs["types"].items():
    % if "is_enum" in type and type["is_enum"]:
def ${type["format"]}(value: int) -> str:
    % for variant in type["fields"]:
    if value == ${variant["value"]}:
        return "${variant["name"]}"
    % endfor
    raise DataError("Unknown value")
    % endif
% endfor

<%
    # Make sure that all required parameters are present in the instruction.
    for program in programs["programs"]:
        for instruction in program["instructions"]:
            param_names = [parameter["name"] for parameter in instruction["parameters"]]
            for parameter in instruction["parameters"]:
                required_parameters = programs["types"][parameter["type"]].get("required_parameters")
                if not required_parameters:
                    continue
                args = parameter.get("args", {})
                for required_parameter in required_parameters:
                    if required_parameter.startswith("#"):
                        continue
                    if required_parameter not in args:
                        raise Exception(f"Parameter \"{parameter['name']}\" is missing the required argument \"{required_parameter}\".")
                    target = args[required_parameter]
                    if target not in param_names and target not in instruction["references"]:
                        raise Exception(f"Instruction \"{instruction['name']}\" is missing the required parameter \"{required_parameter}\" from parameter \"{parameter['name']}\".")
%>

def get_instruction(
    program_id: str, instruction_id: InstructionId, instruction_accounts: list[Account], instruction_data: InstructionData
) -> Instruction:
% for program in programs["programs"]:
% if len(program["instructions"]) > 0:
    if program_id == ${getProgramId(program)}:
    % for instruction in program["instructions"]:
        if instruction_id == ${getInstructionIdText(program, instruction)}:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ${getInstructionIdText(program, instruction)},
                (
                % for parameter in instruction["parameters"]:
                    PropertyTemplate(
                        "${parameter["name"]}",
                        ${parameter["optional"]},
                        ${programs["types"][parameter["type"]]["parse"]},
                        ${programs["types"][parameter["type"]]["format"]},
                        ${args_tuple(programs["types"][parameter["type"]].get("required_parameters", []), parameter.get("args", {}))},
                    ),
                % endfor
                ),
                ${instruction["references_required"]},
                ${repr(tuple(instruction["references"]))},
                (
                % for ui_property in instruction["ui_properties"]:
                    UIProperty(
                        ${repr(ui_property.get("parameter"))},
                        ${repr(ui_property.get("account"))},
                        "${ui_property["display_name"]}",
                        ${repr(ui_property.get("default_value_to_hide"))},
                    ),
                % endfor
                ),
                "${program["name"]}: ${instruction["name"]}",
                True,
                True,
                ${instruction.get("is_ui_hidden", False)},
                ${instruction["is_multisig"]},
                ${repr(instruction.get("is_deprecated_warning"))},
            )
    % endfor
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "${program["name"]}",
            True,
            False,
            False,
            False
        )
% endif
% endfor
    return Instruction(
        instruction_data,
        program_id,
        instruction_accounts,
        0,
        (),
        0,
        (),
        (),
        "Unsupported program",
        False,
        False,
        False,
        False
    )

