import io
from typing import TYPE_CHECKING, Any, Tuple, Union

from . import messages
from .protobuf import load_message

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session

    TronMessageType = Union[
        messages.TronTransferContract, messages.TronTriggerSmartContract
    ]

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
            messages.TronTransferContract,
        )
        contract = messages.TronTransferContract(
            to_address=raw_contract.to_address,
            owner_address=raw_contract.owner_address,
            amount=raw_contract.amount,
        )
    elif contract_type == messages.TronRawContractType.TriggerSmartContract:
        raw_contract = load_message(
            io.BytesIO(raw_tx.contract[0].parameter.value),
            messages.TronTriggerSmartContract,
        )
        contract = messages.TronTriggerSmartContract(
            owner_address=raw_contract.owner_address,
            contract_address=raw_contract.contract_address,
            data=raw_contract.data,
        )
    else:
        raise ValueError(f"Unsupported contract type: {contract_type}")

    return tx, contract


# ====== Client functions ====== #


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.TronAddress:
    return session.call(
        messages.TronGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TronAddress,
    )


def sign_tx(
    session: "Session",
    tx: messages.TronSignTx,
    contract: "TronMessageType",
    address_n: "Address",
) -> messages.TronSignature:
    tx.address_n = address_n
    resp = session.call(tx)
    messages.TronContractRequest.ensure_isinstance(resp)
    resp = session.call(contract)
    resp = messages.TronSignature.ensure_isinstance(resp)
    return resp
