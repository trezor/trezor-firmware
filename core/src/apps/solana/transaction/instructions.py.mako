# generated from __init__.py.mako
# do not edit manually!
## getProgramId(program) <<-- generates program id text
<%def name="getProgramId(program)">${"_".join(program["name"].upper().split(" ") + ["ID"])}</%def>\
## getInstructionIdText(instruction) <<-- generates instruction ID text
<%def name="getInstructionIdText(instruction)">${"_".join(["INS"] + instruction["name"].upper().split(" "))}</%def>\
## TODO SOL: getInstructionUiIdentifier hs been replaced wwith UI template
## getInstructionUiIdentifier(instruction) <<-- generates UI identifier for show function
## <%def name="getInstructionUiIdentifier(instruction)">${"_".join(instruction["name"].lower().split(" "))}</%def>\
## getClassName(instruction) <<-- generates class name from instruction name
<%def name="getClassName(instruction)">${instruction["name"].replace(" ", "")}Instruction</%def>\
## getReferenceName(reference) <<-- formatting reference account name
<%def name="getReferenceName(reference)">${"_".join(reference["name"].lower().split(" "))}</%def>\
<%def name="getReferenceOptionalType(reference)">\
% if reference["optional"]:
 | None\
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
% else:
, False\
% endif
</%def>\
<%def name="getPythonType(type)">\
% if type == "u32":
int\
% elif type == "u64":
int\
% elif type == "i32":
int\
% elif type == "i64":
int\
% elif type == "pubkey":
bytes\
% elif type == "string":
str\
% else:
int\
% endif
</%def>\
from typing import TYPE_CHECKING
from trezor.wire import ProcessError
from .parse import parseProperty
from trezor.utils import BufferReader
## from ..constants import ADDRESS_SIG, ADDRESS_SIG_READ_ONLY, ADDRESS_READ_ONLY, ADDRESS_RW

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard
    from ..types import RawInstruction

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


class Instruction:
    PROGRAM_ID: str
    INSTRUCTION_ID: int

    program_id: str
    instruction_id: int

    # name of the UI template to be used derived from the template
    ui_identifier: str
    # Name to be displayed on the UI
    ui_name: str

    # There is no separate field for UI display name, so the property name is used
    # for that purpose. The values within this list shall be used to display on the
    # UI and to retrieve the value by calling the __getattr__ function.
    ui_parameter_list: list[str] | None = None
    # Here, a tuple is used where the first item is the UI Display name and the
    # second item is the account name that can be used to retrieve the value
    # by using the __getattr__ function or access directly from the parsed_accounts
    # list.
    ui_account_list: list[tuple[str, str]] | None = None


    parsed_data: dict[str, Any] | None = None
    parsed_accounts: dict[str, bytes | tuple[bytes, int] | None] | None = None


    def __init__(
        self,
        instruction_data: bytes,
        program_id: str,
        instruction_id: int,
        property_templates: list[dict[str, str | bool]],
        accounts_template: list[dict[str, str | bool]],
        ui_parameter_list: list[int],
        ui_account_list: list[int],
        ui_identifier: str,
        ui_name: str
    ) -> None:
        self.program_id = program_id
        self.instruction_id = instruction_id
        self.ui_identifier = ui_identifier
        self.ui_name = ui_name

        self.ui_parameter_list = []
        self.ui_account_list = []

        self.parsed_data = {}
        self.parsed_accounts = {}

        reader = BufferReader(instruction_data)

        for property_template in property_templates:
            self.set_property(property_template["name"], parseProperty(reader, property_template))
        
        # TODO SOL: parsed account shall be appended here
        
        for index in ui_parameter_list:
            self.ui_parameter_list.append(
                property_templates[index]["name"]
            )
            # ui_parameter_list: list[tuple[str, str]] | None = None
        
        # TODO SOL: ui_account_list shall be appended here
    
    def __getattr__(self, attr: str) -> Any:
        assert self.parsed_data is not None
        # assert self.parsed_accounts is not None

        if attr in self.parsed_data:
            return self.parsed_data[attr]
        elif attr in self.parsed_accounts:
            return self.parsed_accounts[attr]
        else:
            raise AttributeError(f"Attribute {attr} not found")
    
    def set_property(self, attr: str, value: Any) -> None:
        assert self.parsed_data is not None
        self.parsed_data[attr] = value
    
    def set_account(
        self, account: str, value: bytes | tuple[bytes, int] | None
    ) -> None:
        assert self.parsed_accounts is not None
        self.parsed_accounts[account] = value

    @classmethod
    def is_type_of(cls, ins: Any) -> TypeGuard["Instruction"]:
        return ins.program_id == cls.PROGRAM_ID and ins.instruction_id == cls.INSTRUCTION_ID



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


if TYPE_CHECKING:

% for program in programs["programs"]:
    ## generates classes for instructions
    % for instruction in program["instructions"]:
    class ${getClassName(instruction)}(Instruction):
        PROGRAM_ID = ${getProgramId(program)}
        INSTRUCTION_ID = ${getInstructionIdText(instruction)}

        ## generates properties for instruction parameters
        % for parameter in instruction["parameters"]:
        ${parameter["name"]}: ${getPythonType(parameter["type"])}
        % endfor

        ## generates properties for reference accounts
        % for reference in instruction["references"]:
        ${getReferenceName(reference)}: bytes${getReferenceOptionalType(reference)}
        % endfor

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["${getClassName(instruction)}"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    % endfor
% endfor

def get_instruction(
    program_id: str, instruction_id: int, accounts: list[int], instruction_data: bytes
) -> Instruction:
% for program in programs["programs"]:
% if len(program["instructions"]) > 0:
    if program_id == ${getProgramId(program)}:
    % for instruction in program["instructions"]:
        % if instruction == program["instructions"][0]:
        if instruction_id == ${getInstructionIdText(instruction)}:
        % else:
        elif instruction_id == ${getInstructionIdText(instruction)}:
        % endif
            return Instruction(
                instruction_data,
                program_id,
                ${getInstructionIdText(instruction)},
                ${instruction["parameters"]},
                ${instruction["references"]},
                ${instruction["ui"]["elements"]["parameter_indexes"]},
                ${instruction["ui"]["elements"]["account_indexes"]},
                ## "${getInstructionUiIdentifier(instruction)}",
                "${instruction["ui"]["template"]}",
                "${instruction["name"]}"
            )
    % endfor
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} {instruction_id}"
            )
% endif
% endfor
    else:
        raise ProcessError(
            f"Unknown instruction type: {program_id} {instruction_id}"
        )
