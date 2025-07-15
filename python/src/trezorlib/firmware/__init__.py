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

import typing as t
from hashlib import blake2s

from typing_extensions import Protocol, TypeGuard

from .. import messages
from .core import VendorFirmware
from .legacy import LegacyFirmware, LegacyV2Firmware
from .models import Model

# re-exports:
if True:
    # indented block prevents isort from messing with these until we upgrade to 5.x
    from .consts import *  # noqa: F401, F403
    from .core import *  # noqa: F401, F403
    from .legacy import *  # noqa: F401, F403
    from .util import (  # noqa: F401
        FirmwareIntegrityError,
        InvalidSignatureError,
        Unsigned,
    )
    from .vendor import *  # noqa: F401, F403

if t.TYPE_CHECKING:
    from ..transport.session import Session

    T = t.TypeVar("T", bound="FirmwareType")

    class FirmwareType(Protocol):
        @classmethod
        def parse(cls: type[T], data: bytes) -> T: ...

        def verify(self, dev_keys: bool = False) -> None: ...

        def digest(self) -> bytes: ...

        def model(self) -> Model | None: ...


def parse(data: bytes) -> FirmwareType:
    try:
        if data[:4] == b"TRZR":
            return LegacyFirmware.parse(data)
        elif data[:4] == b"TRZV":
            return VendorFirmware.parse(data)
        elif data[:4] == b"TRZF":
            return LegacyV2Firmware.parse(data)
        else:
            raise ValueError("Unrecognized firmware image type")
    except Exception as e:
        raise FirmwareIntegrityError("Invalid firmware image") from e


def is_onev2(fw: FirmwareType) -> TypeGuard[LegacyFirmware]:
    return isinstance(fw, LegacyFirmware) and fw.embedded_v2 is not None


# ====== Client functions ====== #


def update(
    session: Session,
    data: bytes,
    progress_update: t.Callable[[int], t.Any] = lambda _: None,
):
    if session.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = session.call(messages.FirmwareErase(length=len(data)))

    # TREZORv1 method
    if isinstance(resp, messages.Success):
        resp = session.call(messages.FirmwareUpload(payload=data))
        progress_update(len(data))
        if isinstance(resp, messages.Success):
            return
        else:
            raise RuntimeError(f"Unexpected result {resp}")

    # TREZORv2 method
    while isinstance(resp, messages.FirmwareRequest):
        length = resp.length
        payload = data[resp.offset : resp.offset + length]
        digest = blake2s(payload).digest()
        resp = session.call(messages.FirmwareUpload(payload=payload, hash=digest))
        progress_update(length)

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")


def get_hash(session: Session, challenge: bytes | None) -> bytes:
    return session.call(
        messages.GetFirmwareHash(challenge=challenge), expect=messages.FirmwareHash
    ).hash
