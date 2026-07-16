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
    from .nrf import *  # noqa: F401, F403
    from .sanity_struct import *  # noqa: F401, F403
    from .secmon import *  # noqa: F401, F403
    from .util import (  # noqa: F401
        FirmwareIntegrityError,
        InvalidSignatureError,
        Unsigned,
    )
    from .vendor import *  # noqa: F401, F403

if t.TYPE_CHECKING:
    from ..client import Session

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
) -> None:
    if session.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = session.call(messages.FirmwareErase(length=len(data)))

    # TREZORv1 method
    if isinstance(resp, messages.Success):
        resp = session.call(
            messages.FirmwareUpload(payload=data), expect=messages.Success
        )
        progress_update(len(data))

    # TREZORv2 method
    while isinstance(resp, messages.FirmwareRequest):
        length = resp.length
        payload = data[resp.offset : resp.offset + length]
        digest = blake2s(payload).digest()
        resp = session.call(messages.FirmwareUpload(payload=payload, hash=digest))
        progress_update(length)

    messages.Success.ensure_isinstance(resp)


def firmware_begin(
    session: Session,
    boot_header: bytes,
    module_headers: bytes,
    code: t.Optional[bytes] = None,
    custom: bool = False,
    progress_update: t.Callable[[int], t.Any] = lambda _: None,
) -> bool:
    """Phase 1 of a Merkle-tree firmware update.

    Sends the new signed boot header and the new firmware's module headers. The
    device authenticates them, confirms with the user, decides keep-seed, stages
    the boot header (with the resolved firmware_type) via the UCB and reboots.

    Provide `code` (the new bootloader code -- the image bytes *after* the boot
    header, i.e. bootloader.bin[header_size:]) so it is available if needed. The
    DEVICE decides whether it is used: if the device's current bootloader code
    already conforms to the new header it does a header-only update and requests
    nothing; otherwise it requests + streams the code (full bootloader update).
    Returns True iff the device streamed the code. If `code` is None the device
    can only do a header-only update and will fail if the code actually changed.

    After the device reboots and the boardloader installs the new boot header,
    reconnect and call `update()` with the firmware modules to run phase 2.

    If `custom` is set, the device is told this is an unofficial install: the
    kernel+coreapp may deviate from the founder manifest. The device requires an
    unlocked bootloader and marks the firmware custom (boot warning, unprivileged,
    storage-isolated). The secmon must still match the manifest.
    """
    if session.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = session.call(
        messages.FirmwareBegin(
            boot_header=boot_header,
            module_headers=module_headers,
            code_length=len(code) if code else None,
            custom_install=True if custom else None,
        )
    )

    # The device drives: it requests the code only if its current bootloader code
    # does not conform to the new header (otherwise it goes straight to Success).
    streamed = False
    while isinstance(resp, messages.FirmwareRequest):
        assert code is not None, "device requested bootloader code but none supplied"
        streamed = True
        length = resp.length
        payload = code[resp.offset : resp.offset + length]
        digest = blake2s(payload).digest()
        resp = session.call(messages.FirmwareUpload(payload=payload, hash=digest))
        progress_update(length)

    messages.Success.ensure_isinstance(resp)
    return streamed


def get_hash(session: Session, challenge: bytes | None) -> bytes:
    return session.call(
        messages.GetFirmwareHash(challenge=challenge), expect=messages.FirmwareHash
    ).hash
