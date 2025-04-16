# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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
import os
import typing as t
import warnings
from enum import IntEnum

from . import exceptions, mapping, messages, models
from .tools import parse_path
from .transport import Transport, get_transport
from .transport.thp.protocol_and_channel import Channel
from .transport.thp.protocol_v1 import ProtocolV1Channel
from .transport.thp.protocol_v2 import ProtocolV2Channel, TrezorState

if t.TYPE_CHECKING:
    from .transport.session import Session, SessionV1

LOG = logging.getLogger(__name__)

MAX_PASSPHRASE_LENGTH = 50
MAX_PIN_LENGTH = 50

PASSPHRASE_ON_DEVICE = object()
SEEDLESS = object()
PASSPHRASE_TEST_PATH = parse_path("44h/1h/0h/0/0")

OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware update
Or visit https://suite.trezor.io/
""".strip()


class ProtocolVersion(IntEnum):
    V1 = 0x01  # Codec
    V2 = 0x02  # THP


class TrezorClient:
    button_callback: t.Callable[[messages.ButtonRequest], None] | None = None
    pin_callback: t.Callable[[messages.PinMatrixRequest], str] | None = None

    _model: models.TrezorModel
    _features: messages.Features | None = None
    _protocol_version: int
    _setup_pin: str | None = None  # Should be used only by conftest
    _last_active_session: SessionV1 | None = None

    _session_id_counter: int = 0
    _default_pairing_method: int = messages.ThpPairingMethod.CodeEntry
    def __init__(
        self,
        transport: Transport,
        protocol: Channel | None = None,
        model: models.TrezorModel | None = None,
    ) -> None:
        """
        Transport needs to be opened before calling a method (or accessing
        an attribute) for the first time. It should be closed after you're
        done using the client.
        """

        LOG.info(f"creating client instance for device: {transport.get_path()}")
        # Here, self.model could be set to None. Unless _init_device is False, it will
        # get correctly reconfigured as part of the init_device flow.
        self._model = model  # type: ignore ["None" is incompatible with "TrezorModel"]
        if self._model:
            self.mapping = self.model.default_mapping
        else:
            self.mapping = mapping.DEFAULT_MAPPING

        self._is_invalidated: bool = False
        self.transport = transport

        if protocol is None:
            self.protocol = self._get_protocol()
        else:
            self.protocol = protocol
        self.protocol.mapping = self.mapping

        if isinstance(self.protocol, ProtocolV1Channel):
            self._protocol_version = ProtocolVersion.V1
        elif isinstance(self.protocol, ProtocolV2Channel):
            self._protocol_version = ProtocolVersion.V2
        else:
            raise Exception("Unknown protocol version")

    def do_pairing(self, pairing_method: int | None = None) -> None:
        from .transport.session import SessionV2

        assert self.protocol_version == ProtocolVersion.V2
        if pairing_method is None:
            pairing_method = self._default_pairing_method
        session = SessionV2(client=self, id=b"\x00")
        session.call(
            messages.ThpPairingRequest(host_name="Trezorlib"),
            expect=messages.ThpPairingRequestApproved,
            skip_firmware_version_check=True,
        )
        session.call(
            messages.ThpSelectMethod(selected_pairing_method=pairing_method),
            expect=messages.ThpEndResponse,
            skip_firmware_version_check=True,
        )
        assert isinstance(self.protocol, ProtocolV2Channel)
        self.protocol._has_valid_channel = True

    def get_session(
        self,
        passphrase: str | object = "",
        derive_cardano: bool = False,
    ) -> Session:
        """
        Returns a new session.

        In the case of seed derivation, the function will fail if the device is not initialized.
        """
        if self.features.initialized is False and passphrase is not SEEDLESS:
            raise exceptions.DerivationOnUninitaizedDeviceError(
                "Calling uninitialized device with a passphrase. Call get_seedless_session instead."
            )

        if isinstance(self.protocol, ProtocolV1Channel):
            from .transport.session import SessionV1, derive_seed

            if passphrase is SEEDLESS:
                return SessionV1.new(client=self, derive_cardano=False)
            session = SessionV1.new(
                self,
                derive_cardano=derive_cardano,
            )
            derive_seed(session, passphrase)
            return session
        if isinstance(self.protocol, ProtocolV2Channel):
            from .transport.session import SessionV2

            if self.protocol.trezor_state is TrezorState.UNPAIRED:
                self.do_pairing()

            if passphrase is SEEDLESS:
                return SessionV2(self, id=b"\x00")

            if self._session_id_counter >= 255:
                self._session_id_counter = 0
            assert isinstance(passphrase, str) or passphrase is None
            self._session_id_counter += 1

            return SessionV2.new(
                self, passphrase, derive_cardano, self._session_id_counter
            )

        raise NotImplementedError

    def get_seedless_session(self) -> Session:
        return self.get_session(passphrase=SEEDLESS)

    def invalidate(self) -> None:
        self._is_invalidated = True

    @property
    def features(self) -> messages.Features:
        if self._features is None:
            self._features = self._get_features()
            self.check_firmware_version(warn_only=True)
        assert self._features is not None
        return self._features

    def _get_features(self) -> messages.Features:
        if isinstance(self.protocol, ProtocolV2Channel):
            if (
                self.protocol.trezor_state is TrezorState.UNPAIRED
                or not self.protocol._has_valid_channel
            ):
                self.do_pairing()
        return self.protocol.get_features()

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    @property
    def model(self) -> models.TrezorModel:
        model = models.detect(self.features)
        if self.features.vendor not in model.vendors:
            raise exceptions.TrezorException(
                f"Unrecognized vendor: {self.features.vendor}"
            )
        return model

    @property
    def version(self) -> tuple[int, int, int]:
        f = self.features
        ver = (
            f.major_version,
            f.minor_version,
            f.patch_version,
        )
        return ver

    @property
    def is_invalidated(self) -> bool:
        return self._is_invalidated

    def refresh_features(self) -> messages.Features:
        self.protocol.update_features()
        self._features = self.protocol.get_features()
        self.check_firmware_version(warn_only=True)
        return self._features

    def _get_protocol(self) -> Channel:
        protocol = ProtocolV1Channel(self.transport, mapping.DEFAULT_MAPPING)
        protocol.write(messages.Initialize())
        response = protocol.read()

        if isinstance(response, messages.Failure):
            if response.code == messages.FailureType.InvalidProtocol:
                LOG.debug("Protocol V2 detected")
                protocol = ProtocolV2Channel(self.transport, self.mapping)
        return protocol

    def reset_protocol(self):
        if self._protocol_version == ProtocolVersion.V1:
            self.protocol = ProtocolV1Channel(self.transport, self.mapping)
        elif self._protocol_version == ProtocolVersion.V2:
            self.protocol = ProtocolV2Channel(self.transport, self.mapping)
        else:
            assert False
        self._features = None

    def is_outdated(self) -> bool:
        if self.features.bootloader_mode:
            return False
        return self.version < self.model.minimum_version

    def check_firmware_version(self, warn_only: bool = False) -> None:
        if self.is_outdated():
            if warn_only:
                warnings.warn("Firmware is out of date", stacklevel=2)
            else:
                raise exceptions.OutdatedFirmwareError(OUTDATED_FIRMWARE_ERROR)

    def _write(self, msg: t.Any, session_id: int | None = None) -> None:
        if isinstance(self.protocol, ProtocolV1Channel):
            self.protocol.write(msg)
        elif isinstance(self.protocol, ProtocolV2Channel):
            assert session_id is not None
            self.protocol.write(session_id=session_id, msg=msg)
        else:
            raise Exception("Unknown client protocol")

    def _read(self, session_id: int | None = None) -> t.Any:
        if isinstance(self.protocol, ProtocolV1Channel):
            return self.protocol.read()
        elif isinstance(self.protocol, ProtocolV2Channel):
            assert session_id is not None
            return self.protocol.read(session_id=session_id)
        else:
            raise Exception("Unknown client protocol")


def get_default_client(
    path: t.Optional[str] = None,
    **kwargs: t.Any,
) -> "TrezorClient":
    """Get a client for a connected Trezor device.

    Returns a TrezorClient instance with minimum fuss.

    Transport is opened and should be closed after you're done with the client.

    If path is specified, does a prefix-search for the specified device. Otherwise, uses
    the value of TREZOR_PATH env variable, or finds first connected Trezor.
    """

    if path is None:
        path = os.getenv("TREZOR_PATH")

    transport = get_transport(path, prefix_search=True)
    transport.open()

    return TrezorClient(transport, **kwargs)


def get_callback_passphrase_v1(
    passphrase: str = "",
) -> t.Callable[[Session, t.Any], t.Any] | None:

    def _callback_passphrase_v1(session: Session, msg: t.Any) -> t.Any:
        return session.call(messages.PassphraseAck(passphrase=passphrase))

    return _callback_passphrase_v1
