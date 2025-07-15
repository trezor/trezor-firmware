import io
from typing import TYPE_CHECKING, Any, Tuple

from . import messages, tools
from .protobuf import load_message

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address

    TronMessageType = messages.TronTransferContract

DEFAULT_BIP32_PATH = "m/44h/195h/0h/0/0"


def from_raw_data(
    raw_data: bytes,
) -> Tuple[messages.TronSignTx, "TronMessageType"]:
    raw_tx = load_message(io.BytesIO(raw_data), messages.TronRawTransaction)

    tx = messages.TronSignTx(
        ref_block_bytes=raw_tx.ref_block_bytes,
        ref_block_hash=raw_tx.ref_block_hash,
        expiration=raw_tx.expiration,
        timestamp=raw_tx.timestamp,
        fee_limit=raw_tx.fee_limit,
        data=raw_tx.data,
    )

    if len(raw_tx.contract) != 1:
        raise ValueError("Only single contract transactions are supported.")

    contract_type = raw_tx.contract[0].type
    if contract_type == messages.TronRawContractType.TransferContract:
        raw_contract = load_message(
            io.BytesIO(raw_tx.contract[0].parameter.value),
            messages.TronRawTransferContract,
        )
        contract = messages.TronTransferContract(
            to_address=_encode_address(raw_contract.to_address),
            owner_address=_encode_address(raw_contract.owner_address),
            amount=raw_contract.amount,
        )
    else:
        raise ValueError(f"Unsupported contract type: {contract_type}")

    return tx, contract


def _encode_address(address: bytes) -> str:
    return tools.b58check_encode(address)


# ====== Client functions ====== #


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.TronAddress:
    return client.call(
        messages.TronGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TronAddress,
    )


def sign_tx(
    client: "TrezorClient",
    tx: messages.TronSignTx,
    contract: "TronMessageType",
    address_n: "Address",
) -> messages.TronSignature:
    tx.address_n = address_n
    resp = client.call(tx)
    messages.TronContractRequest.ensure_isinstance(resp)
    resp = client.call(contract)
    resp = messages.TronSignature.ensure_isinstance(resp)
    return resp
