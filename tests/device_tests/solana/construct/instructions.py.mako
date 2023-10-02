# generated from __init__.py.mako
# do not edit manually!

<%def name="getProgramId(program)">${"_".join(program["name"].upper().split(" ") + ["ID"])}</%def>\
<%def name="getInstructionIdText(instruction)">${"_".join(["INS"] + instruction["name"].upper().split(" "))}</%def>\
<%def name="getProgramInstructionsEnumName(program)">${program["name"].replace(" ", "")}Instruction</%def>\
<%def name="getProgramAccountsName(program)">_${program["name"].upper().replace(" ", "_")}_ACCOUNTS</%def>\
<%def name="getProgramParamsName(program)">_${program["name"].upper().replace(" ", "_")}_PARAMETERS</%def>\
<%def name="getConstructType(type)">\
% if type in ("u64", "i64"):
Int64ul\
% elif type in ("u32", "i32"):
Int32ul\
% elif type in ("pubKey", "authority"):
PublicKey()\
% elif type == "string":
_STRING\
% elif type == "memo":
Memo()\
% else:
Int64ul\
% endif
</%def>\
from enum import IntEnum
from construct import (
    Int32ul,
    Int64ul,
    Struct,
    Switch,
)
from .custom_constructs import (
    AccountReference,
    Accounts,
    InstructionData,
    InstructionId,
    InstructionProgramId,
    Memo,
    PublicKey,
    _STRING,
)

class Program:
% for program in programs["programs"]:
    ${getProgramId(program)} = "${program["id"]}"
% endfor

% for program in programs["programs"]:
class ${getProgramInstructionsEnumName(program)}(IntEnum):
    % for instruction in program["instructions"]:
    ${getInstructionIdText(instruction)} = ${instruction["id"]}
    % endfor
% endfor

% for program in programs["programs"]:
${getProgramAccountsName(program)} = Switch(
    lambda this: this.data["instruction_id"],
    {
    % for instruction in program["instructions"]:
        ${getProgramInstructionsEnumName(program)}.${getInstructionIdText(instruction)}: Accounts(
        % for reference in instruction["references"]:
            "${reference["name"]}" / AccountReference(),
        % endfor
        ),
    %endfor
    }
)
%endfor

% for program in programs["programs"]:
${getProgramParamsName(program)} = InstructionData(
    "instruction_id" / InstructionId(),
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
        % for instruction in program["instructions"]:
            ${getProgramInstructionsEnumName(program)}.${getInstructionIdText(instruction)}: Struct(
            % for parameter in instruction["parameters"]:
                "${parameter["name"]}" / ${getConstructType(parameter["type"])},
            % endfor
            ),
        %endfor
        }
    )
)
%endfor

INSTRUCTION_ID_FORMATS = {
% for program in programs["programs"]:
    Program.${getProgramId(program)}: ${program["instruction_id_format"]},
% endfor
}

_INSTRUCTION = Struct(
    "program_id" / InstructionProgramId(),
    "instruction_accounts"
    / Switch(
        lambda this: this.program_id,
        {
% for program in programs["programs"]:
            Program.${getProgramId(program)}: ${getProgramAccountsName(program)},
%endfor
        }
    ),
    "data"
    / Switch(
        lambda this: this.program_id,
        {
% for program in programs["programs"]:
            Program.${getProgramId(program)}: ${getProgramParamsName(program)},
%endfor
        }
    )
)


def replace_account_placeholders(construct):
    for ins in construct["instructions"]:
        program_id = Program.__dict__[ins["program_id"]]
% for program in programs["programs"]:
    % if program == programs["programs"][0]:
        if program_id == Program.${getProgramId(program)}:
    % else:
        elif program_id == Program.${getProgramId(program)}:
    %endif
            ins["data"]["instruction_id"] = ${getProgramInstructionsEnumName(program)}.__dict__[
                ins["data"]["instruction_id"]
            ].value
%endfor

        ins["program_id"] = program_id

    return construct
