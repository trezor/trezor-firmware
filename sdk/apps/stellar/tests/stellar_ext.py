"""Wire client of the modular Stellar app, the counterpart of `trezorlib.stellar`."""

import io
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from trezorlib import exceptions, protobuf
from trezorlib.messages import ExtAppMessage, ExtAppResponse, Failure

from .generated import messages as stellar_messages

if TYPE_CHECKING:
    from trezorlib.client import Session
    from trezorlib.tools import Address


def message_id(msg: type[protobuf.MessageType] | protobuf.MessageType) -> int:
    """Return app-specific numeric message ID for a message class or instance."""
    if isinstance(msg, type):
        name = msg.__name__
    else:
        name = msg.__class__.__name__

    try:
        return int(stellar_messages.MessageType[name])
    except KeyError as e:
        raise ValueError(f"Unknown message type: {name}") from e


def call_ext(
    session: "Session",
    instance_id: int,
    *,
    msg_data: protobuf.MessageType,
    expect: list[type[protobuf.MessageType]],
    timeout: float | None = None,
) -> Any:
    """Send `msg_data` to the app and return the response, which must be one of `expect`."""

    buf = io.BytesIO()
    protobuf.dump_message(buf, msg_data)

    msg = ExtAppMessage(
        instance_id=instance_id,
        message_id=message_id(msg_data),
        data=buf.getvalue(),
    )
    if session.is_invalid:
        raise exceptions.InvalidSessionError(session.id)
    with session:
        resp = session.client._call(
            session, msg, expect=ExtAppResponse, timeout=timeout
        )
        buf = io.BytesIO(resp.data)

        assert isinstance(expect, list)
        assert len(expect) > 0

        expect_ids = [message_id(cls) for cls in expect]
        try:
            idx = expect_ids.index(resp.message_id)
            return protobuf.load_message(buf, expect[idx])
        except Exception:
            raise exceptions.TrezorFailure(
                failure=Failure(message="Unexpected response type")
            )


DEFAULT_BIP32_PATH = "m/44h/148h/0h"


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> stellar_messages.Address:
    return call_ext(
        session,
        instance_id,
        msg_data=stellar_messages.GetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=[stellar_messages.Address],
    )


def sign_tx(
    session: "Session",
    instance_id: int,
    tx: stellar_messages.SignTx,
    operations: Sequence[protobuf.MessageType],
    ext: stellar_messages.TxExt,
    address_n: "Address",
    network_passphrase: str,
) -> stellar_messages.SignedTx:
    tx.address_n = address_n
    tx.network_passphrase = network_passphrase
    tx.num_operations = len(operations)

    resp = call_ext(
        session, instance_id, msg_data=tx, expect=[stellar_messages.TxOpRequest]
    )
    assert isinstance(resp, stellar_messages.TxOpRequest)

    for operation in operations:
        resp = call_ext(
            session,
            instance_id,
            msg_data=operation,
            expect=[
                stellar_messages.TxOpRequest,
                stellar_messages.TxExtRequest,
                stellar_messages.SignedTx,
            ],
        )

    if isinstance(resp, stellar_messages.TxExtRequest):
        resp = call_ext(
            session,
            instance_id,
            msg_data=ext,
            expect=[stellar_messages.SignedTx],
        )

    if not isinstance(resp, stellar_messages.SignedTx):
        raise exceptions.TrezorFailure(
            failure=Failure(message="Unexpected response type")
        )
    return resp


def sign_soroban_authorization(
    session: "Session",
    instance_id: int,
    address_n: "Address",
    network_passphrase: str,
    authorization: stellar_messages.SorobanAuthorizationWithAddress,
) -> stellar_messages.SorobanAuthorizationSignature:
    return call_ext(
        session,
        instance_id,
        msg_data=stellar_messages.SignSorobanAuthorization(
            address_n=address_n,
            network_passphrase=network_passphrase,
            envelope_type=stellar_messages.SorobanAuthorizationEnvelopeType.ENVELOPE_TYPE_SOROBAN_AUTHORIZATION_WITH_ADDRESS,
            soroban_authorization_with_address=authorization,
        ),
        expect=[stellar_messages.SorobanAuthorizationSignature],
    )
