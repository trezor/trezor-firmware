# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import io
from typing import TYPE_CHECKING, Any

from trezorlib.messages import ExtAppMessage, ExtAppResponse, Failure
from trezorlib import exceptions, protobuf

from .generated import messages as funnycoin_messages

if TYPE_CHECKING:
    from trezorlib.client import Session
    from trezorlib.tools import Address


def message_id(msg: type[protobuf.MessageType] | funnycoin_messages.MessageType) -> int:
    """Return app-specific numeric message ID for a message class or instance."""
    if isinstance(msg, type):
        name = msg.__name__
    else:
        name = msg.__class__.__name__

    try:
        return int(funnycoin_messages.MessageType[name])
    except KeyError as e:
        raise ValueError(f"Unknown message type: {name}") from e


def message_type(msg_id: int) -> type[protobuf.MessageType]:
    """Convert message ID (int) to message class type."""
    try:
        enum_name = funnycoin_messages.MessageType(msg_id).name
        return getattr(funnycoin_messages, enum_name)
    except ValueError as e:
        raise ValueError(f"Unknown message ID: {msg_id}") from e


def call_ext(
    session: "Session",
    instance_id: int,
    *,
    msg_data: funnycoin_messages.MessageType,
    expect: list[type[funnycoin_messages.MessageType]],
    timeout: float | None = None,
) -> Any:
    """Call a method on this session, process and return the response."""

    # Serialize to bytes
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
            # Find the index of the matching message ID
            idx = expect_ids.index(resp.message_id)

            return protobuf.load_message(buf, expect[idx])
        except Exception as _e:
            raise exceptions.TrezorFailure(
                failure=Failure(message="Unexpected response type")
            )


# ====== Client functions ====== #


def get_public_node(
    session: "Session", instance_id: int, n: "Address", show_display: bool = False
) -> funnycoin_messages.PublicKey:
    """Request FunnyCoin public node/public key for a derivation path."""
    return call_ext(
        session,
        instance_id,
        msg_data=funnycoin_messages.GetPublicKey(
            address_n=n, show_display=show_display
        ),
        expect=[funnycoin_messages.PublicKey],
    )
