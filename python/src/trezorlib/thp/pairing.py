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

import secrets
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from hashlib import sha256

import typing_extensions as tx

from .. import messages
from ..exceptions import ProtocolError, StateMismatchError, TrezorException
from ..protobuf import MessageType
from .channel import Channel, ChannelState, PairingState
from .cpace import cpace
from .credentials import Credential, StaticCredential

if t.TYPE_CHECKING:
    from ..client import MT
    from .client import TrezorClientThp


class ControllerLifecycle(Enum):
    INITIAL = auto()
    PAIRING_REQUESTED = auto()
    PAIRING_COMPLETED = auto()
    FINISHED = auto()
    FAILED = auto()

    def abort_if_failed(self) -> None:
        if self is ControllerLifecycle.FAILED:
            raise ValueError("Pairing failed")


@dataclass
class CodeEntryState:
    challenge: bytes
    commitment: bytes
    cpace_trezor_public_key: bytes


class PairingController:
    def __init__(self, client: TrezorClientThp) -> None:
        self.opened = False
        self.client = client
        self.session = client._get_pairing_session()
        self._pairing_requested = False
        self._failed = False

    @property
    def state(self) -> ControllerLifecycle:
        if self._failed:
            return ControllerLifecycle.FAILED
        if self.channel.state is ChannelState.CREDENTIAL_PHASE:
            return ControllerLifecycle.PAIRING_COMPLETED
        elif self.channel.state is ChannelState.ENCRYPTED_TRANSPORT:
            return ControllerLifecycle.FINISHED
        elif (
            self.channel.state is ChannelState.PAIRING_PHASE and self._pairing_requested
        ):
            return ControllerLifecycle.PAIRING_REQUESTED
        else:
            return ControllerLifecycle.INITIAL

    @state.setter
    def state(self, state: ControllerLifecycle) -> None:
        self._failed = state is ControllerLifecycle.FAILED
        if state is ControllerLifecycle.INITIAL:
            self._pairing_requested = False
        elif state is ControllerLifecycle.PAIRING_REQUESTED:
            if self.channel.state > ChannelState.PAIRING_PHASE:
                raise StateMismatchError(
                    "Tried to revert to pairing phase from a later state"
                )
            self.channel.state = ChannelState.PAIRING_PHASE
            self._pairing_requested = True
        elif state is ControllerLifecycle.PAIRING_COMPLETED:
            self.channel.state = ChannelState.CREDENTIAL_PHASE
            self._pairing_requested = False
        elif state is ControllerLifecycle.FINISHED:
            self.channel.state = ChannelState.ENCRYPTED_TRANSPORT
            self._pairing_requested = False
        else:
            raise ValueError(f"Invalid state: {state}")

    def _maybe_open(self) -> None:
        if self.opened:
            return
        self.opened = True
        self.client.connect()
        self.session.__enter__()

    def _maybe_close(self) -> None:
        if not self.opened:
            return
        self.opened = False
        self.session.__exit__(None, None, None)

    def start(self) -> None:
        self.state.abort_if_failed()
        self._maybe_open()
        if self.state is not ControllerLifecycle.INITIAL:
            return
        self.session.call(
            messages.ThpPairingRequest(
                host_name=self.client.app.host_name,
                app_name=self.client.app.app_name,
            ),
            expect=messages.ThpPairingRequestApproved,
        )
        self.state = ControllerLifecycle.PAIRING_REQUESTED

    def _call(self, message: MessageType, *, expect: type[MT]) -> MT:
        self.start()
        return self.session.call(message, expect=expect)

    @property
    def channel(self) -> Channel:
        return self.client.channel

    @property
    def methods(self) -> t.Collection[type["PairingMethod"]]:
        return {
            m
            for m in PairingMethod.METHODS_AVAILABLE
            if m.PAIRING_METHOD in self.channel.device_properties.pairing_methods
        }

    def is_paired(self) -> bool:
        return self.channel.pairing_state.is_paired()

    def set_paired(self) -> None:
        self.state.abort_if_failed()
        if not self.channel.pairing_state.is_paired():
            self.channel.pairing_state = PairingState.PAIRED
        self.state = ControllerLifecycle.PAIRING_COMPLETED

    def finish(self, _no_call: bool = False) -> None:
        if self.state is ControllerLifecycle.FINISHED:
            return
        self.state.abort_if_failed()
        if not _no_call:
            self._call(messages.ThpEndRequest(), expect=messages.ThpEndResponse)
        self.state = ControllerLifecycle.FINISHED
        self._maybe_close()

    def abort(self) -> None:
        self.state = ControllerLifecycle.FAILED
        self.channel.close()
        self._maybe_close()

    def _check_state(self, required_state: ControllerLifecycle) -> None:
        if self.state != required_state:
            raise StateMismatchError(
                f"Tried to execute a {required_state.name} operation in the {self.state.name} state"
            )

    def request_credential(self, autoconnect: bool = False) -> Credential:
        self._check_state(ControllerLifecycle.PAIRING_COMPLETED)
        pubkey = self.channel.get_host_static_pubkey()
        credential_response = self._call(
            messages.ThpCredentialRequest(
                host_static_public_key=pubkey,
                autoconnect=autoconnect,
            ),
            expect=messages.ThpCredentialResponse,
        )
        return StaticCredential(
            host_privkey=self.channel.host_static_privkey,
            credential=credential_response.credential,
            trezor_pubkey=credential_response.trezor_static_public_key,
        )

    # ==== Available pairing flows ====
    def skip(self) -> None:
        if not self.is_paired():
            SkipPairing(self)


class PairingMethod(metaclass=ABCMeta):
    METHODS_AVAILABLE: t.ClassVar[set[type[tx.Self]]] = set()

    PAIRING_METHOD: t.ClassVar[messages.ThpPairingMethod]

    def __init__(self, controller: PairingController) -> None:
        controller.start()
        controller._check_state(ControllerLifecycle.PAIRING_REQUESTED)
        self.controller = controller
        self.setup()

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.METHODS_AVAILABLE.add(cls)

    @abstractmethod
    def setup(self) -> None:
        raise NotImplementedError

    @property
    def handshake_hash(self) -> bytes:
        return self.controller.channel.handshake_hash

    def _abort_if_not_equal(self, expected: t.Any, actual: t.Any) -> None:
        if actual != expected:
            self.controller.abort()
            raise ProtocolError("Code or commitment mismatch")

    def _select_method(
        self,
        *,
        expect: type[MT] = messages.ThpPairingPreparationsFinished,
    ) -> MT:
        if not any(
            self.PAIRING_METHOD == m.PAIRING_METHOD for m in self.controller.methods
        ):
            raise ValueError(
                f"Pairing method {self.PAIRING_METHOD.name} not supported by the device."
            )

        return self.controller._call(
            messages.ThpSelectMethod(selected_pairing_method=self.PAIRING_METHOD),
            expect=expect,
        )


class SkipPairing(PairingMethod):
    PAIRING_METHOD = messages.ThpPairingMethod.SkipPairing

    def setup(self) -> None:
        self._select_method(expect=messages.ThpEndResponse)
        self.controller.set_paired()
        self.controller.finish(_no_call=True)


class CodeEntry(PairingMethod):
    PAIRING_METHOD = messages.ThpPairingMethod.CodeEntry

    code_entry_state: CodeEntryState | None = None

    def setup(self) -> None:
        commitment_msg = self._select_method(expect=messages.ThpCodeEntryCommitment)
        # create a challenge
        challenge = secrets.token_bytes(16)
        cpace_trezor_msg = self.controller._call(
            messages.ThpCodeEntryChallenge(challenge=challenge),
            expect=messages.ThpCodeEntryCpaceTrezor,
        )
        self.code_entry_state = CodeEntryState(
            challenge=challenge,
            commitment=commitment_msg.commitment,
            cpace_trezor_public_key=cpace_trezor_msg.cpace_trezor_public_key,
        )

    def send_code(self, code: str) -> None:
        assert self.code_entry_state is not None

        if len(code) != 6 or not code.isdigit():
            raise ValueError("Code must be a 6-digit number")

        # perform the CPace protocol
        cpace_result = cpace(
            prs=code.encode("ascii"),
            ci=self.handshake_hash,
            b_pubkey=self.code_entry_state.cpace_trezor_public_key,
        )
        tag = sha256(cpace_result.shared_secret).digest()
        secret_msg = self.controller._call(
            messages.ThpCodeEntryCpaceHostTag(
                cpace_host_public_key=cpace_result.a_pubkey,
                tag=tag,
            ),
            expect=messages.ThpCodeEntrySecret,
        )

        # check the commitment
        computed_commitment = sha256(secret_msg.secret).digest()
        self._abort_if_not_equal(self.code_entry_state.commitment, computed_commitment)

        # check the code
        sha_ctx = sha256(messages.ThpPairingMethod.CodeEntry.to_bytes(1, "big"))
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(secret_msg.secret)
        sha_ctx.update(self.code_entry_state.challenge)
        code_hash = sha_ctx.digest()
        computed_code = int.from_bytes(code_hash, "big") % 1_000_000
        self._abort_if_not_equal(code, f"{computed_code:06}")

        self.controller.set_paired()


class QrCode(PairingMethod):
    PAIRING_METHOD = messages.ThpPairingMethod.QrCode

    def setup(self) -> None:
        self._select_method()

    def send_qr_code(self, code: bytes) -> None:
        tag = sha256(self.handshake_hash + code).digest()
        secret_msg = self.controller._call(
            messages.ThpQrCodeTag(tag=tag),
            expect=messages.ThpQrCodeSecret,
        )

        sha_ctx = sha256()
        sha_ctx.update(messages.ThpPairingMethod.QrCode.to_bytes(1, "big"))
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(secret_msg.secret)
        computed_code = sha_ctx.digest()[:16]
        self._abort_if_not_equal(code, computed_code)

        self.controller.set_paired()


class Nfc(PairingMethod):
    PAIRING_METHOD = messages.ThpPairingMethod.NFC

    nfc_host_secret: bytes

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.nfc_host_secret = secrets.token_bytes(16)

    def setup(self) -> None:
        self._select_method()

    def send_nfc_tag(self, tag_trezor: bytes) -> None:
        sha_ctx = sha256(messages.ThpPairingMethod.NFC.to_bytes(1, "big"))
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(tag_trezor)
        tag_host = sha_ctx.digest()

        tag_trezor_msg = self.controller._call(
            messages.ThpNfcTagHost(tag=tag_host),
            expect=messages.ThpNfcTagTrezor,
        )

        sha_ctx = sha256(messages.ThpPairingMethod.NFC.to_bytes(1, "big"))
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(self.nfc_host_secret)
        computed_tag = sha_ctx.digest()
        self._abort_if_not_equal(tag_trezor_msg.tag, computed_tag)

        self.controller.set_paired()


def default_pairing_flow(
    pairing: PairingController,
    *,
    code_entry_callback: t.Callable[[], str] | None = None,
    request_credential: bool = True,
) -> Credential | None:
    if pairing.is_paired():
        return

    if SkipPairing in pairing.methods:
        pairing.skip()
        return

    if CodeEntry not in pairing.methods:
        raise NotImplementedError(
            "CodeEntry pairing method not supported by the device."
        )

    if code_entry_callback is None:
        raise TrezorException(
            "code_entry_callback is required when the device is not paired"
        )

    method = CodeEntry(pairing)
    code = code_entry_callback()
    method.send_code(code)

    assert pairing.state is ControllerLifecycle.PAIRING_COMPLETED

    if request_credential:
        credential = pairing.request_credential()
    else:
        credential = None

    pairing.finish()
    return credential
