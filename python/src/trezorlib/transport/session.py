from __future__ import annotations

import logging
import typing as t

from .. import exceptions, messages, models
from ..protobuf import MessageType
from .thp.protocol_v1 import ProtocolV1Channel

if t.TYPE_CHECKING:
    from ..client import TrezorClient

LOG = logging.getLogger(__name__)

MT = t.TypeVar("MT", bound=MessageType)


class Session:
    def __init__(
        self, client: TrezorClient, id: bytes, passphrase: str | object | None = None
    ) -> None:
        self.client = client
        self._id = id
        self.passphrase = passphrase

    @classmethod
    def new(
        cls, client: TrezorClient, passphrase: str | object | None, derive_cardano: bool
    ) -> Session:
        raise NotImplementedError

    def call(self, msg: MessageType, expect: type[MT] = MessageType) -> MT:
        self.client.check_firmware_version()
        resp = self.call_raw(msg)

        while True:
            if isinstance(resp, messages.PinMatrixRequest):
                if self.client.pin_callback is None:
                    raise NotImplementedError("Missing pin_callback")
                resp = self.client.pin_callback(self, resp)
            elif isinstance(resp, messages.PassphraseRequest):
                if self.client.passphrase_callback is None:
                    raise NotImplementedError("Missing passphrase_callback")
                resp = self.client.passphrase_callback(self, resp)
            elif isinstance(resp, messages.ButtonRequest):
                resp = (self.client.button_callback or default_button_callback)(
                    self, resp
                )
            elif isinstance(resp, messages.Failure):
                if resp.code == messages.FailureType.ActionCancelled:
                    raise exceptions.Cancelled
                raise exceptions.TrezorFailure(resp)
            elif not isinstance(resp, expect):
                raise exceptions.UnexpectedMessageError(expect, resp)
            else:
                return resp

    def call_raw(self, msg: t.Any) -> t.Any:
        self._write(msg)
        return self._read()

    def _write(self, msg: t.Any) -> None:
        raise NotImplementedError

    def _read(self) -> t.Any:
        raise NotImplementedError

    def refresh_features(self) -> None:
        self.client.refresh_features()

    def end(self) -> t.Any:
        return self.call(messages.EndSession())

    def ping(self, message: str, button_protection: bool | None = None) -> str:
        resp = self.call(
            messages.Ping(message=message, button_protection=button_protection),
            expect=messages.Success,
        )
        assert resp.message is not None
        return resp.message

    def invalidate(self) -> None:
        self.client.invalidate()

    @property
    def features(self) -> messages.Features:
        return self.client.features

    @property
    def model(self) -> models.TrezorModel:
        return self.client.model

    @property
    def version(self) -> t.Tuple[int, int, int]:
        return self.client.version

    @property
    def id(self) -> bytes:
        return self._id

    @id.setter
    def id(self, value: bytes) -> None:
        if not isinstance(value, bytes):
            raise ValueError("id must be of type bytes")
        self._id = value


class SessionV1(Session):
    derive_cardano: bool | None = False

    @classmethod
    def new(
        cls,
        client: TrezorClient,
        passphrase: str | object = "",
        derive_cardano: bool = False,
        session_id: bytes | None = None,
    ) -> SessionV1:
        assert isinstance(client.protocol, ProtocolV1Channel)
        session = SessionV1(client, id=session_id or b"")

        session.passphrase = passphrase
        session.derive_cardano = derive_cardano
        session.init_session(session.derive_cardano)
        return session

    @classmethod
    def resume_from_id(cls, client: TrezorClient, session_id: bytes) -> SessionV1:
        assert isinstance(client.protocol, ProtocolV1Channel)
        session = SessionV1(client, session_id)
        session.init_session()
        return session

    def _write(self, msg: t.Any) -> None:
        if t.TYPE_CHECKING:
            assert isinstance(self.client.protocol, ProtocolV1Channel)
        self.client.protocol.write(msg)

    def _read(self) -> t.Any:
        if t.TYPE_CHECKING:
            assert isinstance(self.client.protocol, ProtocolV1Channel)
        return self.client.protocol.read()

    def init_session(self, derive_cardano: bool | None = None):
        if self.id == b"":
            session_id = None
        else:
            session_id = self.id
        resp: messages.Features = self.call_raw(
            messages.Initialize(session_id=session_id, derive_cardano=derive_cardano)
        )
        assert isinstance(resp, messages.Features)
        if resp.session_id is not None:
            self.id = resp.session_id


def default_button_callback(session: Session, msg: t.Any) -> t.Any:
    return session.call(messages.ButtonAck())
