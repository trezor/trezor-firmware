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

import enum
import logging
import os
import platform
import typing as t
import unicodedata
import warnings
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

import typing_extensions as tx

from . import exceptions, messages, models
from .mapping import DEFAULT_MAPPING
from .protobuf import MessageType
from .tools import enter_context, parse_path
from .transport import Transport, get_transport

if t.TYPE_CHECKING:
    from .mapping import ProtobufMapping
    from .thp import pairing
    from .thp.credentials import Credential

MT = t.TypeVar("MT", bound=MessageType)
ClientType = t.TypeVar("ClientType", bound="TrezorClient")
SessionType = t.TypeVar("SessionType", bound="Session")
SessionIdType = t.TypeVar("SessionIdType", contravariant=True)

LOG = logging.getLogger(__name__)

MAX_PASSPHRASE_LENGTH = 50
MAX_PIN_LENGTH = 50

_DEFAULT_READ_TIMEOUT: int | None = None


class PassphraseSetting(enum.Enum):
    """Passphrase setting for a session."""

    STANDARD_WALLET = ""
    """Open the default wallet with no passphrase."""
    ON_DEVICE = object()
    """Request passphrase entry on the device."""
    AUTO = object()
    """If passphrase is enabled and the device supports it, request passphrase
    entry on the device. Otherwise, open the default wallet with no
    passphrase."""
    NONE = None
    """Create a management session where wallet operations are disabled."""


GET_ROOT_FINGERPRINT_MESSAGE = messages.GetPublicKey(
    address_n=parse_path("m/0h"),
    show_display=False,
    ignore_xpub_magic=True,
    ecdsa_curve_name="secp256k1",
)


class Session(t.Generic[ClientType, SessionIdType]):
    def __init__(
        self,
        client: ClientType,
        id: SessionIdType,
        *,
        root_fingerprint: bytes | None = None,
    ) -> None:
        self.client = client
        self.id = id
        self.is_invalid = False
        self._root_fingerprint = root_fingerprint

    def _log_short_id(self) -> str:
        if self.id is None:
            return f"(none:{id(self)})"
        return repr(self.id)[:8]

    @enter_context
    def get_root_fingerprint(self) -> bytes:
        if self._root_fingerprint is None:
            self.ensure_unlocked()
            assert self._root_fingerprint is not None
        return self._root_fingerprint

    def call(
        self,
        msg: MessageType,
        *,
        expect: type[MT] = MessageType,
        timeout: float | None = None,
    ) -> MT:
        """Call a method on this session, process and return the response."""
        if self.is_invalid:
            raise exceptions.InvalidSessionError(self.id)
        with self:
            return self.client._call(self, msg, expect=expect, timeout=timeout)

    def call_raw(self, msg: MessageType, timeout: float | None = None) -> MessageType:
        """Invoke a single call-response round-trip to the device.

        No processing is done on the response: errors are not converted to exceptions,
        internal workflow callbacks are not triggered.
        """
        return self.client._call_raw(self, msg, timeout)

    def read(self, timeout: float | None = None) -> MessageType:
        """Read a single message from the device."""
        return self.client._read(self, timeout)

    def write(self, msg: MessageType) -> None:
        """Write a single message to the device."""
        return self.client._write(self, msg)

    def close(self) -> None:
        """End and invalidate this session."""
        LOG.info("Closing session %s", self)
        try:
            self.call(messages.EndSession())
            self.is_invalid = True
        except Exception as e:
            LOG.warning("Failed to end session: %s", e)

    def cancel(self) -> None:
        """Send a Cancel signal to the device, interrupting the current workflow."""
        self.write(messages.Cancel())

    @property
    def features(self) -> messages.Features:
        return self.client.features

    def refresh_features(self) -> messages.Features:
        return self.client.refresh_features()

    @property
    def model(self) -> models.TrezorModel:
        return self.client.model

    @property
    def version(self) -> tuple[int, int, int]:
        return self.client.version

    def __enter__(self) -> tx.Self:
        self.client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: t.Any,
    ) -> None:
        self.client.__exit__(exc_type, exc_value, traceback)

    @enter_context
    def ensure_unlocked(self) -> None:
        resp = self.call(GET_ROOT_FINGERPRINT_MESSAGE, expect=messages.PublicKey)
        assert resp.root_fingerprint is not None
        root_fingerprint = resp.root_fingerprint.to_bytes(4, "big")
        if self._root_fingerprint is None:
            self._root_fingerprint = root_fingerprint
        assert self._root_fingerprint == root_fingerprint
        self.refresh_features()

    @enter_context
    def lock(self) -> None:
        self.client.lock(_use_session=self)


@dataclass
class AppManifest:
    app_name: str
    host_name: str = platform.node()

    button_callback: t.Callable[[messages.ButtonRequest], None] | None = None
    pin_callback: t.Callable[[messages.PinMatrixRequest], str] | None = None

    credentials: (
        t.Collection[Credential] | t.Callable[[], t.Collection[Credential]]
    ) = ()

    def _callback_pin(self, msg: messages.PinMatrixRequest) -> str:
        if self.pin_callback is None:
            raise RuntimeError("PIN callback was not specified")
        return self.pin_callback(msg)

    def _callback_button(self, msg: messages.ButtonRequest) -> None:
        if self.button_callback is not None:
            self.button_callback(msg)

    def get_credentials(self) -> t.Collection[Credential]:
        if callable(self.credentials):
            return self.credentials()
        return self.credentials


class TrezorClient(t.Generic[SessionType], metaclass=ABCMeta):
    _features: messages.Features | None = None

    def __init__(
        self,
        app: AppManifest,
        transport: Transport,
        *,
        model: models.TrezorModel | None,
        mapping: ProtobufMapping | None,
        pairing: pairing.PairingController,
    ) -> None:
        """
        TODO
        """
        LOG.info(
            f"creating client instance {type(self).__name__} for device: {transport}"
        )
        self.app = app
        self.transport = transport
        self._model = model
        self._mapping = mapping
        self._features = None
        self.pairing = pairing

    # ===== Internal methods for overriding in subclasses =====

    @abstractmethod
    def _write(self, session: SessionType, msg: MessageType) -> None:
        """Convert a message to the appropriate bytes representation for the given session
        and write it to the transport.
        """
        raise NotImplementedError

    @abstractmethod
    def _read(self, session: SessionType, timeout: float | None = None) -> MessageType:
        """Read the next message from the transport that is intended for the given session."""
        raise NotImplementedError

    @abstractmethod
    def _get_any_session(self) -> SessionType:
        """Get an arbitrary but valid session.

        Used for internal calls that do not want to activate a specific session.
        Users of the library SHOULD NOT use this method; use `get_session()`
        with the appropriate parameters instead.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_session(
        self,
        *,
        passphrase: str | t.Literal[PassphraseSetting.ON_DEVICE] | None,
        derive_cardano: bool,
    ) -> SessionType:
        """Get a new session with the given passphrase and `derive_cardano` flag.

        This internal method is used by `get_session()`, so that TrezorClient
        subclasses do not have to check for Cardano in capabilities.
        """
        raise NotImplementedError

    # ===== Common implementations =====

    def __enter__(self) -> tx.Self:
        """(Re)Open a connection to the device."""
        self.transport.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: t.Any,
    ) -> None:
        self.transport.__exit__(exc_type, exc_value, traceback)

    def connect(self) -> None:
        """Establish a connection to the device.

        When connecting to a THP device with active screen lock, the channel
        will fail to establish. The user must unlock their device first, even if
        a valid credential is available.

        Normally, calling `get_session()` will trigger the PIN prompt if
        required to open the channel. However, other operations that are
        normally "silent" from the user's perspective can fail with a
        `DeviceLockedError`. (One notable example is reading `client.features`.)

        `connect()` ensures an open channel, triggering a PIN unlock if
        required. Subsequent silent operations will be able to proceed.

        `connect()` does nothing if a connection is already established.
        Notably, if the device was locked _after_ the channel was established,
        `connect()` will not cause it to unlock. If that is your requirement,
        use `client.ensure_unlocked()` instead.
        """

    def is_connected(self) -> bool:
        return True

    def get_session(
        self,
        passphrase: str | PassphraseSetting | None = PassphraseSetting.STANDARD_WALLET,
        *,
        derive_cardano: bool = False,
    ) -> SessionType:
        """Get a new session with the given passphrase.

        Passphrase can be provided as a string or a [`PassphraseSetting`] enum
        value. Set `passphrase=PassphraseSetting.ON_DEVICE` to request the
        passphrase on the device. Set `passphrase=PassphraseSetting.AUTO` to
        automatically determine whether to request the passphrase on the device
        based on the device's capabilities.

        If passphrase is None or `PassphraseSetting.NONE`, the returned session
        will be "seedless", that is, it will not be possible to call any methods
        that require the user's seed (such as wallet addresses or signature
        operations).

        Use `derive_cardano=True` to request activation of Cardano-specific
        operations in this session. If Cardano is not available, an exception
        will be raised. (Note that Cardano operations may still be available
        even if `derive_cardano` is set to False.)

        The value of `derive_cardano` is ignored if `passphrase` is set to None.
        """
        self.connect()
        self.check_firmware_version()

        if (
            derive_cardano
            and messages.Capability.Cardano not in self.features.capabilities
        ):
            raise exceptions.TrezorException("Cardano is not available on this device.")
        if (
            passphrase is PassphraseSetting.ON_DEVICE
            and messages.Capability.PassphraseEntry not in self.features.capabilities
        ):
            raise exceptions.PassphraseError(
                "Passphrase entry is not available on this device."
            )

        if isinstance(passphrase, str):
            passphrase = unicodedata.normalize("NFKD", passphrase)

        passphrase_is_nonempty = isinstance(passphrase, str) and passphrase != ""
        must_request_passphrase = (
            passphrase_is_nonempty or passphrase is PassphraseSetting.ON_DEVICE
        )
        if must_request_passphrase and not self.features.passphrase_protection:
            raise exceptions.PassphraseError(
                "Passphrase protection is disabled on this device."
            )
        if passphrase_is_nonempty and self.features.passphrase_always_on_device is True:
            raise exceptions.PassphraseError(
                "Only on-device entry allowed for passphrase."
            )

        # coerce PassphraseSetting to str, None, or ON_DEVICE
        if passphrase is PassphraseSetting.STANDARD_WALLET:
            passphrase = ""
        elif passphrase is PassphraseSetting.AUTO:
            if (
                self.features.passphrase_protection
                and messages.Capability.PassphraseEntry in self.features.capabilities
            ):
                passphrase = PassphraseSetting.ON_DEVICE
            else:
                passphrase = ""
        elif passphrase is PassphraseSetting.NONE:
            passphrase = None

        return self._get_session(passphrase=passphrase, derive_cardano=derive_cardano)

    @property
    def features(self) -> messages.Features:
        if self._features is not None:
            return self._features
        self._features = self._get_features()
        self.check_firmware_version(warn_only=True)
        return self._features

    def _get_features(self) -> messages.Features:
        with self._get_any_session() as session:
            resp = session.call_raw(messages.GetFeatures())
        return messages.Features.ensure_isinstance(resp)

    @property
    def model(self) -> models.TrezorModel:
        if self._model is None:
            self._model = models.detect(self.features)
            if self.features.vendor not in self._model.vendors:
                raise exceptions.TrezorException(
                    f"Unrecognized vendor: {self.features.vendor}"
                )
        return self._model

    @property
    def mapping(self) -> ProtobufMapping:
        if self._mapping is None:
            if self._model is None:
                # short-circuit the case where we need some mapping in order
                # to run model detection via GetFeatures
                return DEFAULT_MAPPING
            self._mapping = self.model.default_mapping
        return self._mapping

    @property
    def version(self) -> tuple[int, int, int]:
        f = self.features
        ver = (
            f.major_version,
            f.minor_version,
            f.patch_version,
        )
        return ver

    def refresh_features(self) -> messages.Features:
        # clear cached features
        self._features = None
        # trigger a refresh
        return self.features

    def is_outdated(self) -> bool:
        if self.features.bootloader_mode:
            return False
        return self.version < self.model.minimum_version

    def check_firmware_version(self, warn_only: bool = False) -> None:
        if self.is_outdated():
            if warn_only:
                warnings.warn("Firmware is out of date", stacklevel=2)
            else:
                raise exceptions.OutdatedFirmwareError

    def _call_raw(
        self,
        session: SessionType,
        msg: MessageType,
        timeout: float | None = None,
    ) -> MessageType:
        """Send a message to the transport and return the raw response.

        Does not perform any sort of handling on the response: errors are not
        converted to exceptions, internal workflow callbacks are not triggered.
        """
        self._write(session, msg)
        return self._read(session, timeout)

    def ping(
        self,
        message: str,
        button_protection: bool | None = None,
        timeout: float | None = None,
    ) -> str:
        with self._get_any_session() as session:
            resp = session.call(
                messages.Ping(message=message, button_protection=button_protection),
                expect=messages.Success,
                timeout=timeout,
            )
            assert resp.message is not None
            return resp.message

    def _call(
        self,
        session: SessionType,
        msg: MessageType,
        *,
        expect: type[MT] = MessageType,
        timeout: float | None = None,
    ) -> MT:
        resp = session.call_raw(msg, timeout=timeout)
        while True:
            if isinstance(resp, messages.PinMatrixRequest):
                resp = self._callback_pin(session, resp)
            elif isinstance(resp, messages.ButtonRequest):
                resp = self._callback_button(session, resp)
            elif isinstance(resp, messages.Failure):
                if resp.code in (
                    messages.FailureType.ActionCancelled,
                    messages.FailureType.PinCancelled,
                ):
                    raise exceptions.Cancelled
                elif resp.code == messages.FailureType.InvalidSession:
                    raise exceptions.InvalidSessionError(session.id)
                raise exceptions.TrezorFailure(resp)
            elif isinstance(resp, messages.PassphraseRequest):
                raise exceptions.InvalidSessionError(session.id, from_message=resp)
            elif not isinstance(resp, expect):
                raise exceptions.UnexpectedMessageError(expect, resp)
            else:
                return resp

    def _callback_pin(
        self, session: SessionType, msg: messages.PinMatrixRequest
    ) -> MessageType:
        try:
            pin = self.app._callback_pin(msg)
        except exceptions.Cancelled:
            session.call_raw(messages.Cancel())
            raise

        if any(d not in "123456789" for d in pin) or not (
            1 <= len(pin) <= MAX_PIN_LENGTH
        ):
            session.call_raw(messages.Cancel())
            raise ValueError("Invalid PIN provided")

        resp = session.call_raw(messages.PinMatrixAck(pin=pin))
        if isinstance(resp, messages.Failure) and resp.code in (
            messages.FailureType.PinInvalid,
            messages.FailureType.PinCancelled,
            messages.FailureType.PinExpected,
        ):
            raise exceptions.PinException(resp.code, resp.message)
        else:
            return resp

    def _callback_button(
        self, session: SessionType, msg: messages.ButtonRequest
    ) -> MessageType:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        # do this raw - send ButtonAck first, notify UI later
        session.write(messages.ButtonAck())
        self.app._callback_button(msg)
        return session.read()

    def cancel(self) -> None:
        """Send a Cancel signal to the device, interrupting the current workflow."""
        try:
            with self._get_any_session() as session:
                session.call_raw(messages.Cancel())
        except exceptions.Cancelled:
            pass

    def lock(self, *, _use_session: SessionType | None = None) -> None:
        """Lock the device with a PIN prompt, if enabled."""
        session = _use_session or self._get_any_session()
        with session:
            session.call_raw(messages.LockDevice())
            self.refresh_features()

    def ensure_unlocked(self) -> None:
        """Ensure the device is unlocked."""
        session = self.get_session(passphrase=PassphraseSetting.STANDARD_WALLET)
        with session:
            session.ensure_unlocked()

    def _invalidate(self) -> None:
        """Invalidate the client after a device wipe.

        All state that is no longer valid after a wipe should be cleared here.
        """
        self._features = None


def get_default_client(
    app_name: str,
    path_or_transport: str | Transport | None = None,
    *,
    credentials: t.Collection[Credential] = (),
    button_callback: t.Callable[[messages.ButtonRequest], None] | None = None,
    pin_callback: t.Callable[[messages.PinMatrixRequest], str] | None = None,
    code_entry_callback: t.Callable[[], str] | None = None,
    **kwargs: t.Any,
) -> "TrezorClient":
    """Get a client for a connected Trezor device.

    Returns a TrezorClient instance with minimum fuss.

    If path is specified, does a prefix-search for the specified device. Otherwise, uses
    the value of TREZOR_PATH env variable, or finds first connected Trezor.
    """
    if path_or_transport is None:
        path_or_transport = os.getenv("TREZOR_PATH")
    if isinstance(path_or_transport, Transport):
        transport = path_or_transport
    else:
        transport = get_transport(path_or_transport, prefix_search=True)

    app = AppManifest(
        app_name=app_name,
        credentials=credentials,
        button_callback=button_callback,
        pin_callback=pin_callback,
    )
    client = get_client(app, transport, **kwargs)

    if not client.pairing.is_paired():
        from .thp.pairing import default_pairing_flow

        default_pairing_flow(client.pairing, code_entry_callback=code_entry_callback)
    return client


def get_default_session(
    client: TrezorClient,
    passphrase_callback: t.Callable[[], str] | None = None,
    *,
    derive_cardano: bool = False,
) -> Session:
    """Get a default session for a connected Trezor device.

    The first argument must be a previously created and paired client instance,
    e.g., via `get_client` or `get_default_client`.

    The logic for determining what passphrase to use is as follows:

    1. If the device has passphrase disabled, the default wallet is used
    2. If the device allows on-device entry, passphrase is requested on the
       device
    3. If `passphrase_callback` is provided, it is used to get the passphrase
    4. Otherwise, the default wallet is used
    """
    passphrase = PassphraseSetting.STANDARD_WALLET
    client.ensure_unlocked()
    if client.features.passphrase_protection:
        if messages.Capability.PassphraseEntry in client.features.capabilities:
            passphrase = PassphraseSetting.ON_DEVICE
        elif passphrase_callback is not None:
            passphrase = passphrase_callback()
    return client.get_session(passphrase=passphrase, derive_cardano=derive_cardano)


def get_client(
    app: AppManifest,
    transport: Transport,
    *,
    mapping: ProtobufMapping | None = None,
    model: models.TrezorModel | None = None,
) -> TrezorClient:
    from .protocol_v1 import TrezorClientV1, probe
    from .thp.client import TrezorClientThp

    if probe(transport):
        cls = TrezorClientV1
    else:
        cls = TrezorClientThp
    return cls(app=app, transport=transport, mapping=mapping, model=model)
