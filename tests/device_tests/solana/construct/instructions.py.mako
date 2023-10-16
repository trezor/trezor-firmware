# generated from __init__.py.mako
# do not edit manually!

<%def name="getProgramId(program)">${"_".join(program["name"].upper().split(" ") + ["ID"])}</%def>\
<%def name="getInstructionIdText(instruction)">${"_".join(["INS"] + instruction["name"].upper().split(" "))}</%def>\
<%def name="getProgramInstructionsEnumName(program)">${program["name"].replace(" ", "")}Instruction</%def>\
<%def name="getProgramInstructionsConstructName(program)">${program["name"].replace(" ","")}_Instruction</%def>\
<%def name="getInstructionConstructName(program, instruction)">${program["name"].replace(" ","")}_${instruction["name"].replace(" ", "")}_Instruction</%def>\
<%def name="getConstructType(type)">\
% if type in ("u64", "i64"):
Int64ul\
% elif type in ("u32", "i32"):
Int32ul\
% elif type == "u8":
Byte\
% elif type in ("pubKey", "authority"):
PublicKey\
% elif type == "string":
String\
% elif type == "memo":
Memo\
% else:
Int64ul\
% endif
</%def>\
from enum import IntEnum
from construct import (
    Byte,
    GreedyBytes,
    GreedyRange,
    Int32ul,
    Int64ul,
    Optional,
    Struct,
    Switch,
)
from .custom_constructs import (
    CompactStruct,
    InstructionIdAdapter,
    Memo,
    PublicKey,
    String,
)

class Program:
% for program in programs["programs"]:
    ${getProgramId(program)} = "${program["id"]}"
% endfor

INSTRUCTION_ID_FORMATS = {
% for program in programs["programs"]:
    Program.${getProgramId(program)}: ${program["instruction_id_format"]},
% endfor
}

% for program in programs["programs"]:

${"#"} ${program["name"]} begin

class ${getProgramInstructionsEnumName(program)}(IntEnum):
    % for instruction in program["instructions"]:
    ${getInstructionIdText(instruction)} = ${instruction["id"]}
    % endfor

    % for instruction in program["instructions"]:
${getInstructionConstructName(program, instruction)} = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(
        % for reference in instruction["references"]:
        "${reference["name"]}" / Byte,
        % endfor
        % if instruction["is_multisig"]:
        "multisig_signers" / Optional(GreedyRange(Byte))
        % endif
    ),
    "data" / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        % for parameter in instruction["parameters"]:
        "${parameter["name"]}" / ${getConstructType(parameter["type"])},
        % endfor
    ),
)

    % endfor

${getProgramInstructionsConstructName(program)} = Switch(
    lambda this: this.instruction_id,
    {
    %for instruction in program["instructions"]:
        ${getProgramInstructionsEnumName(program)}.${getInstructionIdText(instruction)}: ${getInstructionConstructName(program, instruction)},
    %endfor
    },
)

${"#"} ${program["name"]} end
% endfor

Instruction = Switch(
    lambda this: this.program_id,
    {
% for program in programs["programs"]:
        Program.${getProgramId(program)}: ${getProgramInstructionsConstructName(program)},
%endfor
    }
)
