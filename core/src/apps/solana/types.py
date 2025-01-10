from typing import TYPE_CHECKING

from .definitions import Definitions

if TYPE_CHECKING:
    from enum import IntEnum
    from typing import Any, Callable, Generic, TypeVar

    from trezor.messages import SolanaTxAdditionalInfo, SolanaTxTokenAccountInfo
    from trezor.utils import BufferReader
    from typing_extensions import Self

    from .transaction import Instruction

    Address = tuple[bytes, "AddressType"]
    AddressReference = tuple[bytes, int, "AddressType"]
    Account = Address | AddressReference

    ProgramIndex = int
    InstructionId = int | None
    AccountIndex = int
    InstructionData = memoryview
    RawInstruction = tuple[
        ProgramIndex, InstructionId, list[AccountIndex], InstructionData
    ]

    T = TypeVar("T")
else:
    IntEnum = object
    T = 0
    Generic = {T: object}


class AddressType(IntEnum):
    AddressSig = 0
    AddressSigReadOnly = 1
    AddressReadOnly = 2
    AddressRw = 3


class PropertyTemplate(Generic[T]):
    def __init__(
        self,
        name: str,
        is_authority: bool,
        is_optional: bool,
        parse: Callable[[BufferReader], T],
        format: Callable[[Instruction, T], str],
    ) -> None:
        self.name = name
        self.is_authority = is_authority
        self.is_optional = is_optional
        self.parse = parse
        self.format = format


class AccountTemplate:
    def __init__(
        self, name: str, is_authority: bool, optional: bool, is_token_mint: bool
    ) -> None:
        self.name = name
        self.is_authority = is_authority
        self.optional = optional
        self.is_token_mint = is_token_mint


class UIProperty:
    def __init__(
        self,
        parameter: str | None,
        account: str | None,
        display_name: str,
        is_authority: bool,
        default_value_to_hide: Any | None,
    ) -> None:
        self.parameter = parameter
        self.account = account
        self.display_name = display_name
        self.is_authority = is_authority
        self.default_value_to_hide = default_value_to_hide


class AdditionalTxInfo:
    def __init__(
        self,
        token_accounts_infos: list[SolanaTxTokenAccountInfo],
        definitions: Definitions,
    ) -> None:
        self.token_accounts_infos = token_accounts_infos
        self.definitions = definitions

    @classmethod
    def from_solana_tx_additional_info(
        cls,
        additional_info: SolanaTxAdditionalInfo | None,
    ) -> Self:
        if not additional_info:
            return cls(token_accounts_infos=[], definitions=Definitions())

        return cls(
            token_accounts_infos=additional_info.token_accounts_infos,
            definitions=Definitions.from_encoded(additional_info.encoded_token),
        )
