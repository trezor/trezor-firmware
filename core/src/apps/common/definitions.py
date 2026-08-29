from typing import TYPE_CHECKING

from trezor.messages import (
    EthereumDisplayFormatInfo,
    EthereumNetworkInfo,
    EthereumTokenInfo,
    SolanaTokenInfo,
)
from trezor.wire import DataError

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import TypeVar

    # NOTE: it's important all DefType variants can't be cross-parsed
    DefType = TypeVar(
        "DefType",
        EthereumNetworkInfo,
        EthereumTokenInfo,
        SolanaTokenInfo,
        EthereumDisplayFormatInfo,
    )


def decode_definition(definition: AnyBytes, expected_type: type[DefType]) -> DefType:
    from trezor.enums import DefinitionType
    from trezordefinitions import decode

    # determine the type number from the expected type
    expected_type_number = DefinitionType.ETHEREUM_NETWORK
    # NOTE: can't check equality of MsgDefObjs now, so we check the name
    if expected_type.MESSAGE_NAME == EthereumTokenInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.ETHEREUM_TOKEN
    if expected_type.MESSAGE_NAME == SolanaTokenInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.SOLANA_TOKEN
    if expected_type.MESSAGE_NAME == EthereumDisplayFormatInfo.MESSAGE_NAME:
        expected_type_number = DefinitionType.ETHEREUM_DISPLAY_FORMAT

    try:
        return decode(definition, expected_type_number, expected_type)
    except ValueError as e:
        if __debug__:
            raise DataError(str(e))
        else:
            raise DataError("Invalid definitions")
