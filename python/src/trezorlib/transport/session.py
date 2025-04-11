from __future__ import annotations

import logging
import typing as t

from .. import exceptions, messages, models
from ..client import MAX_PIN_LENGTH
from ..protobuf import MessageType
from .thp.protocol_v1 import ProtocolV1Channel
from .thp.protocol_v2 import ProtocolV2Channel

if t.TYPE_CHECKING:
    from ..client import TrezorClient

LOG = logging.getLogger(__name__)

MT = t.TypeVar("MT", bound=MessageType)


class Session:
    def __init__(self, client: TrezorClient, id: bytes) -> None:
        self.client = client
        self._id = id

    def call(
        self,
        msg: MessageType,
        expect: type[MT] = MessageType,
        skip_firmware_version_check: bool = False,
        _passphrase_ack: messages.PassphraseAck | None = None,
    ) -> MT:
        if not skip_firmware_version_check:
            self.client.check_firmware_version()
        resp = self.call_raw(msg)

        while True:
            if isinstance(resp, messages.PinMatrixRequest):
                if self.client.pin_callback is None:
                    raise RuntimeError("Missing pin_callback")
                resp = self._callback_pin(resp)
            elif isinstance(resp, messages.PassphraseRequest):
                if _passphrase_ack is None:
                    # we got a PassphraseRequest when not explicitly trying to unlock
                    # the session, this means that the session has expired
                    raise exceptions.InvalidSessionError
                resp = self.call_raw(_passphrase_ack)
            elif isinstance(resp, messages.ButtonRequest):
                resp = self._callback_button(resp)
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

    def _callback_pin(self, msg: messages.PinMatrixRequest) -> MessageType:
        if self.client.pin_callback is None:
            raise RuntimeError("No PIN provided")
        try:
            pin = self.client.pin_callback(msg)
        except exceptions.Cancelled:
            self.call_raw(messages.Cancel())
            raise

        if any(d not in "123456789" for d in pin) or not (
            1 <= len(pin) <= MAX_PIN_LENGTH
        ):
            self.call_raw(messages.Cancel())
            raise ValueError("Invalid PIN provided")

        resp = self.call_raw(messages.PinMatrixAck(pin=pin))
        if isinstance(resp, messages.Failure) and resp.code in (
            messages.FailureType.PinInvalid,
            messages.FailureType.PinCancelled,
            messages.FailureType.PinExpected,
        ):
            raise exceptions.PinException(resp.code, resp.message)
        else:
            return resp

    def _callback_button(self, msg: messages.ButtonRequest) -> MessageType:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        # do this raw - send ButtonAck first, notify UI later
        self._write(messages.ButtonAck())
        if self.client.button_callback:
            self.client.button_callback(msg)
        return self._read()

    def _write(self, msg: t.Any) -> None:
        raise NotImplementedError

    def _read(self) -> t.Any:
        raise NotImplementedError

    def refresh_features(self) -> messages.Features:
        return self.client.refresh_features()

    def resume(self) -> None:
        pass

    def end(self) -> t.Any:
        return self.call(messages.EndSession())

    def cancel(self) -> None:
        self._write(messages.Cancel())

    def ping(self, message: str, button_protection: bool | None = None) -> str:
        # We would like ping to work on any valid TrezorClient instance, but
        # due to the protection modes, we need to go through self.call, and that will
        # raise an exception if the firmware is too old.
        # So we short-circuit the simplest variant of ping with call_raw.
        if not button_protection:
            resp = self.call_raw(messages.Ping(message=message))
            if isinstance(resp, messages.ButtonRequest):
                # device is PIN-locked.
                # respond and hope for the best
                resp = self._callback_button(resp)
            resp = messages.Success.ensure_isinstance(resp)
            assert resp.message is not None
            return resp.message

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
    _was_initialized_at_least_once = False

    @classmethod
    def new(
        cls,
        client: TrezorClient,
        derive_cardano: bool = False,
        session_id: bytes | None = None,
    ) -> SessionV1:
        assert isinstance(client.protocol, ProtocolV1Channel)
        session = SessionV1(client, id=session_id or b"")
        session.derive_cardano = derive_cardano
        session.init_session(derive_cardano=session.derive_cardano)
        return session

    @classmethod
    def resume_from_id(cls, client: TrezorClient, session_id: bytes) -> SessionV1:
        assert isinstance(client.protocol, ProtocolV1Channel)
        session = SessionV1(client, session_id)
        session.init_session()
        return session

    def resume(self) -> None:
        self.init_session(derive_cardano=self.derive_cardano)

    def _write(self, msg: t.Any) -> None:
        self._activate_self()
        if t.TYPE_CHECKING:
            assert isinstance(self.client.protocol, ProtocolV1Channel)
        self.client._write(msg)

    def _activate_self(self) -> None:
        if self.client._last_active_session is not self:
            self.client._last_active_session = self
            self.resume()

    def _read(self) -> t.Any:
        assert self.client._last_active_session is self
        if t.TYPE_CHECKING:
            assert isinstance(self.client.protocol, ProtocolV1Channel)
        return self.client._read()

    def init_session(self, derive_cardano: bool | None = None) -> None:
        if self.id == b"":
            new_session = True
            session_id = None
        else:
            new_session = False
            session_id = self.id
        self.client._last_active_session = self
        resp: messages.Features = self.call_raw(
            messages.Initialize(session_id=session_id, derive_cardano=derive_cardano)
        )
        assert isinstance(resp, messages.Features)
        msg_id = resp.session_id or b""
        if new_session:
            self.id = msg_id
        elif self.id != msg_id:
            raise exceptions.FailedSessionResumption(resp.session_id)
        self.was_initialized_at_least_once = True


def derive_seed(session: Session, passphrase: str | object) -> None:

    from ..client import PASSPHRASE_ON_DEVICE, PASSPHRASE_TEST_PATH

    if passphrase is PASSPHRASE_ON_DEVICE:
        ack = messages.PassphraseAck(on_device=True)
    elif isinstance(passphrase, str):
        ack = messages.PassphraseAck(passphrase=passphrase)
    else:
        raise ValueError("Invalid passphrase")
    session.call(
        messages.GetAddress(address_n=PASSPHRASE_TEST_PATH, coin_name="Testnet"),
        expect=messages.Address,
        _passphrase_ack=ack,
    )
    session.refresh_features()


class SessionV2(Session):

    @classmethod
    def new(
        cls,
        client: TrezorClient,
        passphrase: str | None,
        derive_cardano: bool,
        session_id: int = 0,
    ) -> SessionV2:
        assert isinstance(client.protocol, ProtocolV2Channel)
        session = cls(client, session_id.to_bytes(1, "big"))
        session.call(
            messages.ThpCreateNewSession(
                passphrase=passphrase, derive_cardano=derive_cardano
            ),
            expect=messages.Success,
        )
        session.update_id_and_sid(session_id.to_bytes(1, "big"))
        return session

    def __init__(self, client: TrezorClient, id: bytes) -> None:

        super().__init__(client, id)
        assert isinstance(client.protocol, ProtocolV2Channel)

        self.channel: ProtocolV2Channel = client.protocol
        self.update_id_and_sid(id)

    def _write(self, msg: t.Any) -> None:
        LOG.debug("writing message %s", type(msg))
        self.channel.write(self.sid, msg)

    def _read(self) -> t.Any:
        msg = self.channel.read(self.sid)
        LOG.debug("reading message %s", type(msg))
        return msg

    def update_id_and_sid(self, id: bytes) -> None:
        self._id = id
        self.sid = int.from_bytes(id, "big")  # TODO update to extract only sid
