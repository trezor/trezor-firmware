# generated from __init__.py.mako
# do not edit manually!
## getProgramId(program) <<-- generates program id text
<%def name="getProgramId(program)">${"_".join(program["name"].upper().split(" ") + ["ID"])}</%def>\
## getInstructionIdText(instruction) <<-- generates instruction ID text
<%def name="getInstructionIdText(instruction)">${"_".join(["INS"] + instruction["name"].upper().split(" "))}</%def>\
## getInstructionUiIdentifier(instruction) <<-- generates UI identifier for show function
<%def name="getInstructionUiIdentifier(instruction)">${"_".join(instruction["name"].lower().split(" "))}</%def>\
## getClassName(instruction) <<-- generates class name from instruction name
<%def name="getClassName(instruction)">${instruction["name"].replace(" ", "")}Instruction</%def>\
## getReferenceName(reference) <<-- formatting reference account name
<%def name="getReferenceName(reference)">${"_".join(reference["name"].lower().split(" "))}</%def>\
<%def name="getReferenceOptionalType(reference)">\
% if reference["optional"]:
| None
% endif
</%def>\
## getReferenceTypeTemplate(reference) <<-- generates reference account type based on access and signer properties
<%def name="getReferenceTypeTemplate(reference)">\
% if reference["signer"]:
    % if reference["access"] == "w":
ADDRESS_SIG\
    % else:
ADDRESS_SIG_READ_ONLY\
    % endif
% else:
    % if reference["access"] == "w":
ADDRESS_RW\
    % else:
ADDRESS_READ_ONLY\
    % endif
% endif
</%def>\
## getReferenceOptionalTemplate(reference) <<-- if a reference account is optional shall return (, True)
<%def name="getReferenceOptionalTemplate(reference)">\
% if reference["optional"]:
, True\
% endif
</%def>\
from typing import TYPE_CHECKING
from trezor.wire import ProcessError

from . import Instruction
from ..constants import ADDRESS_SIG, ADDRESS_SIG_READ_ONLY, ADDRESS_READ_ONLY, ADDRESS_RW

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard
    from ..types import RawInstruction


def __getattr__(name: str) -> Type[Instruction]:
    ids = {
        %for program in programs["programs"]:
            %for instruction in program["instructions"]:
        "${getClassName(instruction)}": ("${program["id"]}", ${instruction["id"]}),
            %endfor
        %endfor
    }
    id = ids[name]

    class FakeClass(Instruction):
        @classmethod
        def is_type_of(cls, ins: Any):
            return ins.program_id == id[0] and ins.instruction_id == id[1]

    return FakeClass

## creates the program identifier with address from the template
% for program in programs["programs"]:
${getProgramId(program)} = "${program["id"]}"
% endfor

## generates instruction identifiers with values
% for program in programs["programs"]:
    % for instruction in program["instructions"]:
${getInstructionIdText(instruction)} = ${instruction["id"]}
    % endfor
% endfor

if TYPE_CHECKING:
% for program in programs["programs"]:
    ## generates classes for instructions
    % for instruction in program["instructions"]:
    class ${getClassName(instruction)}(Instruction):
        PROGRAM_ID = ${getProgramId(program)}
        INSTRUCTION_ID = ${getInstructionIdText(instruction)}

        ## generates properties for instruction parameters
        % for parameter in instruction["parameters"]:
        ${parameter["name"]}: ${parameter["ptype"]}
        % endfor

        ## generates properties for reference accounts
        % for reference in instruction["references"]:
        ${getReferenceName(reference)}: bytes ${getReferenceOptionalType(reference)}
        % endfor

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["${getClassName(instruction)}"]:
            return ins.program_id == cls.PROGRAM_ID and ins.instruction_id == cls.INSTRUCTION_ID

    % endfor
% endfor

def get_instruction(encoded_program_id: str, instruction_id: int, raw_instruction: RawInstruction) -> Instruction :
% for program in programs["programs"]:
    if encoded_program_id == ${getProgramId(program)}:
    % for instruction in program["instructions"]:
        % if instruction == program["instructions"][0]:
        if instruction_id == ${getInstructionIdText(instruction)}:
            return Instruction(
                raw_instruction,
                ${getInstructionIdText(instruction)},
                [
                % for parameter in instruction["parameters"]:
                    ("${parameter["name"]}", "${parameter["type"].lower()}"),
                % endfor
                ],
                [
                % for reference in instruction["references"]:
                    ("${getReferenceName(reference)}", "${reference["name"]}", ${getReferenceTypeTemplate(reference)}${getReferenceOptionalTemplate(reference)}),
                % endfor
                ],
                "${getInstructionUiIdentifier(instruction)}",
                "${instruction["name"]}",
            )
         % else:
        elif instruction_id == ${getInstructionIdText(instruction)}:
            return Instruction(
                raw_instruction,
                ${getInstructionIdText(instruction)},
                [
                % for parameter in instruction["parameters"]:
                    ("${parameter["name"]}", "${parameter["type"].lower()}"),
                % endfor
                ],
                [
                % for reference in instruction["references"]:
                    ("${getReferenceName(reference)}", "${reference["name"]}", ${getReferenceTypeTemplate(reference)}${getReferenceOptionalTemplate(reference)}),
                % endfor
                ],
                "${getInstructionUiIdentifier(instruction)}",
                "${instruction["name"]}",
            )
        % endif
    % endfor
        else:
            raise ProcessError(f"Unknown instruction type: {encoded_program_id} {instruction_id}")
% endfor
    else:
        raise ProcessError(f"Unknown instruction type: {encoded_program_id} {instruction_id}")
