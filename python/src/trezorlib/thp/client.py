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

from __future__ import annotations

import logging
import struct
import typing as t
from collections import defaultdict

from .. import client, exceptions, messages, models, protobuf
from ..log import DUMP_BYTES
from .channel import Channel
from .pairing import PairingController

if t.TYPE_CHECKING:
    from ..mapping import ProtobufMapping
    from ..transport import Transport

LOG = logging.getLogger(__name__)

HEADER_FMT = ">BH"
HEADER_LEN = struct.calcsize(HEADER_FMT)


class ThpSession(client.Session["TrezorClientThp", int]):
    def derive(
        self,
        passphrase: str | client.PassphraseSetting,
        derive_cardano: bool,
    ) -> None:
        msg = messages.ThpCreateNewSession(derive_cardano=derive_cardano)
        if passphrase is client.PassphraseSetting.ON_DEVICE:
            msg.on_device = True
        else:
            assert isinstance(passphrase, str)
            msg.passphrase = passphrase
        self.call(msg, expect=messages.Success)

    @property
    def channel(self) -> Channel:
        return self.client.channel


class TrezorClientThp(client.TrezorClient[ThpSession]):
    _channel: Channel | None = None
    _device_properties: messages.ThpDeviceProperties | None = None

    def __init__(
        self,
        app: client.AppManifest,
        transport: Transport,
        *,
        mapping: ProtobufMapping | None,
        model: models.TrezorModel | None,
    ) -> None:
        channel = Channel.allocate(transport)
        try:
            # try to open the channel
            channel.open(app.get_credentials())
        except exceptions.DeviceLockedError:
            # If opening failed, the channel is now invalid.
            # Allocate a new channel for someone else to open.
            channel = Channel.allocate(transport)
        self.channel = channel

        if model is None:
            model = self.detect_model(self.device_properties)
        if mapping is None:
            mapping = model.default_mapping

        super().__init__(
            app=app,
            transport=transport,
            mapping=mapping,
            model=model,
            pairing=PairingController(self),
        )
        self._session_id_counter = 0
        self._session_message_queue: dict[int, list[protobuf.MessageType]] = (
            defaultdict(list)
        )

    def connect(self) -> None:
        if self.channel.is_open():
            return
        self.channel.open(self.app.get_credentials(), force_unlock=True)

    def is_connected(self) -> bool:
        return self.channel.is_open()

    def _get_any_session(self) -> ThpSession:
        if not self.channel.is_open():
            raise exceptions.DeviceLockedError
        if not self.pairing.is_paired():
            raise exceptions.NotPairedError
        else:
            self.pairing.finish()
        return ThpSession(self, self._session_id_counter)

    def _get_pairing_session(self) -> ThpSession:
        return ThpSession(self, 0)

    def _get_session(
        self,
        *,
        passphrase: str | client.PassphraseSetting | None,
        derive_cardano: bool,
    ) -> ThpSession:
        if not self.pairing.is_paired():
            raise exceptions.NotPairedError
        else:
            self.pairing.finish()

        if passphrase is None:
            return ThpSession(self, 0)

        self._session_id_counter += 1
        if self._session_id_counter >= 0xFF:
            self._session_id_counter = 1
        session = ThpSession(self, self._session_id_counter)
        session.derive(passphrase, derive_cardano)
        return session

    def _invalidate(self) -> None:
        super()._invalidate()
        # Close the channel. The client cannot be used until a channel is
        # re-established.
        self.channel.close()
        self._session_id_counter = 0
        self._session_message_queue.clear()

    def _write(self, session: ThpSession, msg: protobuf.MessageType) -> None:
        if not self.channel.is_open():
            raise exceptions.DeviceLockedError

        LOG.debug(
            f"sending message: {msg.__class__.__name__}",
            extra={"protobuf": msg, "session": session},
        )
        msg_type, msg_bytes = self.mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            f"encoded as type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        header = struct.pack(HEADER_FMT, session.id, msg_type)
        self.channel.write_chunk(header + msg_bytes)

    def _read(
        self, session: ThpSession, timeout: float | None = None
    ) -> protobuf.MessageType:
        if not self.channel.is_open():
            raise exceptions.DeviceLockedError

        if self._session_message_queue[session.id]:
            return self._session_message_queue[session.id].pop(0)
        if session.is_invalid:
            raise exceptions.InvalidSessionError(session.id)
        while True:
            msg = self.channel.read_chunk(timeout=timeout)
            session_id, msg_type = struct.unpack(HEADER_FMT, msg[:HEADER_LEN])
            msg_bytes = msg[HEADER_LEN:]
            LOG.log(
                DUMP_BYTES,
                f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
                extra={"session": session_id},
            )
            msg = self.mapping.decode(msg_type, msg_bytes)
            LOG.debug(
                f"received message: {msg.__class__.__name__}",
                extra={"protobuf": msg, "session": session_id},
            )
            if session_id == session.id:
                return msg
            else:
                self._session_message_queue[session_id].append(msg)

    @staticmethod
    def detect_model(props: messages.ThpDeviceProperties) -> models.TrezorModel:
        internal_model = props.internal_model
        model = models.by_internal_name(internal_model)
        if model is None:
            model = models.unknown_model(None, internal_model)
        return model

    @property
    def device_properties(self) -> messages.ThpDeviceProperties:
        return self.channel.device_properties
