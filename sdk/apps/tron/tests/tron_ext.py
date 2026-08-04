import io
from typing import TYPE_CHECKING, Any, Tuple, Union

from trezorlib import exceptions
from trezorlib import protobuf
from trezorlib.messages import Failure, TrezorAppMessage, TrezorAppResponse
from trezorlib.protobuf import load_message

from .generated import messages as tron_messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session

    TronMessageType = Union[
        tron_messages.TransferContract,
        tron_messages.TriggerSmartContract,
        tron_messages.FreezeBalanceV2Contract,
        tron_messages.UnfreezeBalanceV2Contract,
        tron_messages.WithdrawUnfreeze,
        tron_messages.WithdrawBalance,
        tron_messages.VoteWitnessContract,
    ]


def message_id(msg: type[protobuf.MessageType] | tron_messages.MessageType) -> int:
    """Return app-specific numeric message ID for a message class or instance."""
    if isinstance(msg, type):
        name = msg.__name__
    else:
        name = msg.__class__.__name__

    try:
        return int(tron_messages.MessageType[name])
    except KeyError as e:
        raise ValueError(f"Unknown message type: {name}") from e


def message_type(msg_id: int) -> type[protobuf.MessageType]:
    """Convert message ID (int) to message class type."""
    try:
        enum_name = tron_messages.MessageType(msg_id).name
        return getattr(tron_messages, enum_name)
    except ValueError as e:
        raise ValueError(f"Unknown message ID: {msg_id}") from e


def call_ext(
    session: "Session",
    instance_id: int,
    *,
    msg_data: tron_messages.MessageType,
    expect: list[type[tron_messages.MessageType]],
    timeout: float | None = None,
) -> Any:
    """Call a method on this session, process and return the response."""

    # Serialize to bytes
    buf = io.BytesIO()
    protobuf.dump_message(buf, msg_data)

    msg = TrezorAppMessage(
        instance_id=instance_id,
        message_id=message_id(msg_data),
        data=buf.getvalue(),
    )
    if session.is_invalid:
        raise exceptions.InvalidSessionError(session.id)
    with session:
        resp = session.client._call(
            session, msg, expect=TrezorAppResponse, timeout=timeout
        )
        buf = io.BytesIO(resp.data)

        assert isinstance(expect, list)
        assert len(expect) > 0

        expect_ids = [message_id(cls) for cls in expect]
        try:
            # Find the index of the matching message ID
            idx = expect_ids.index(resp.message_id)

            return protobuf.load_message(buf, expect[idx])
        except Exception:
            raise exceptions.TrezorFailure(
                failure=Failure(message="Unexpected response type")
            )


DEFAULT_BIP32_PATH = "m/44h/195h/0h/0/0"


def from_raw_data(
    raw_data: bytes,
) -> Tuple[tron_messages.SignTx, "TronMessageType"]:
    raw_tx = load_message(io.BytesIO(raw_data), tron_messages.RawTransaction)
    tx = tron_messages.SignTx(
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
    parameter_value = raw_tx.contract[0].parameter.value

    if contract_type == tron_messages.RawContractType.TransferContract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.TransferContract,
        )
        contract = tron_messages.TransferContract(
            to_address=raw_contract.to_address,
            owner_address=raw_contract.owner_address,
            amount=raw_contract.amount,
        )
    elif contract_type == tron_messages.RawContractType.TriggerSmartContract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.TriggerSmartContract,
        )
        contract = tron_messages.TriggerSmartContract(
            owner_address=raw_contract.owner_address,
            contract_address=raw_contract.contract_address,
            data=raw_contract.data,
        )
    elif contract_type == tron_messages.RawContractType.FreezeBalanceV2Contract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.FreezeBalanceV2Contract,
        )
        contract = tron_messages.FreezeBalanceV2Contract(
            owner_address=raw_contract.owner_address,
            balance=raw_contract.balance,
            resource=raw_contract.resource,
        )
    elif contract_type == tron_messages.RawContractType.UnfreezeBalanceV2Contract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.UnfreezeBalanceV2Contract,
        )
        contract = tron_messages.UnfreezeBalanceV2Contract(
            owner_address=raw_contract.owner_address,
            balance=raw_contract.balance,
            resource=raw_contract.resource,
        )
    elif contract_type == tron_messages.RawContractType.WithdrawExpireUnfreezeContract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.WithdrawUnfreeze,
        )
        contract = tron_messages.WithdrawUnfreeze(
            owner_address=raw_contract.owner_address,
        )
    elif contract_type == tron_messages.RawContractType.WithdrawBalanceContract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.WithdrawBalance,
        )
        contract = tron_messages.WithdrawBalance(
            owner_address=raw_contract.owner_address,
        )
    elif contract_type == tron_messages.RawContractType.VoteWitnessContract:
        raw_contract = load_message(
            io.BytesIO(parameter_value),
            tron_messages.VoteWitnessContract,
        )
        contract = tron_messages.VoteWitnessContract(
            owner_address=raw_contract.owner_address, votes=raw_contract.votes
        )
    else:
        raise ValueError(f"Unsupported contract type: {contract_type}")

    return tx, contract


# ====== Client functions ====== #


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> tron_messages.Address:
    return call_ext(
        session,
        instance_id,
        msg_data=tron_messages.GetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=[tron_messages.Address],
    )


def sign_tx(
    session: "Session",
    instance_id: int,
    tx: tron_messages.SignTx,
    contract: "TronMessageType",
    address_n: "Address",
    chunkify: bool = False,
) -> tron_messages.Signature:
    tx.address_n = address_n
    tx.chunkify = chunkify

    print("Tron: calling sign_tx with tx:", tx)

    resp = call_ext(
        session, instance_id, msg_data=tx, expect=[tron_messages.ContractRequest]
    )

    print("Tron: got contract request:", resp)
    print("Tron: sending contract:", contract, "with type:", type(contract))

    resp = call_ext(
        session,
        instance_id,
        msg_data=contract,
        expect=[tron_messages.Signature],
    )
    print("Tron: got signature:", resp)
    return resp
