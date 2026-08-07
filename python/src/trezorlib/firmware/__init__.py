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

from .. import messages, protobuf
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

    class FirmwareType(Protocol):
        @classmethod
        def parse(cls, data: bytes) -> FirmwareType: ...

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
    prev_hashes: t.Optional[t.Dict[int, bytes]] = None,
) -> None:
    if session.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    # pq_secure_boot phase 2: `prev_hashes` maps a requested chunk's image offset
    # to its smart-hashing chain H_prev, sent inline on that chunk's
    # FirmwareUpload so the device verifies each chunk against the signed
    # code_hash AS IT STREAMS. None for a non-tree (legacy) update, and any chunk
    # not in the map (the innermost chunk of a module, and the manifest/header
    # block) carries no prev_hash.
    resp = session.call(messages.FirmwareErase(length=len(data)))
    _stream_firmware_upload(session, data, resp, progress_update, prev_hashes)


def _stream_firmware_upload(
    session: Session,
    data: bytes,
    resp: protobuf.MessageType,
    progress_update: t.Callable[[int], t.Any],
    prev_hashes: t.Optional[t.Dict[int, bytes]] = None,
) -> protobuf.MessageType:
    """Drive the FirmwareRequest/FirmwareUpload loop from the first response
    (`resp`) to FirmwareErase; returns the final Success (raises otherwise).
    `prev_hashes` (offset -> chain H_prev) is attached inline per chunk for a
    pq_secure_boot tree update; None/absent for the rest."""
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
        # pq smart-hashing: a requested block spans one or more hash chunks; the
        # device needs only the block's TRAILING chunk H_prev, keyed by the
        # block's END offset (offset+length). None => the block reaches a module's
        # innermost chunk and the device derives the seed (or it's the header).
        prev_hash = prev_hashes.get(resp.offset + length) if prev_hashes else None
        resp = session.call(
            messages.FirmwareUpload(payload=payload, hash=digest, prev_hash=prev_hash)
        )
        progress_update(length)

    messages.Success.ensure_isinstance(resp)
    return resp


def firmware_begin(
    session: Session,
    boot_header: bytes,
    module_headers: bytes,
    code: t.Optional[bytes] = None,
    nrf_image: t.Optional[bytes] = None,
    nrf_co_path: t.Optional[bytes] = None,
    nrf_image_hash: t.Optional[bytes] = None,
    progress_update: t.Callable[[int], t.Any] = lambda _: None,
) -> t.Dict[str, int]:
    """Phase 1 of a Merkle-tree firmware update.

    Sends the new signed boot header and the new firmware's module headers. The
    device authenticates them, confirms with the user, decides keep-seed, stages
    the boot header (with the resolved firmware_type) via the UCB and reboots.

    Provide `code` (the new bootloader code -- the image bytes *after* the boot
    header, i.e. bootloader.bin[header_size:]) so it is available if needed. The
    DEVICE decides whether it is used: if the device's current bootloader code
    already conforms to the new header it does a header-only update and requests
    nothing; otherwise it requests + streams the code (full bootloader update).
    If `code` is None the device can only do a header-only update and will fail
    if the code actually changed.

    Returns a dict of bytes actually streamed per image, keyed "code" and "nrf"
    -- so the caller can tell a full-bootloader update (code > 0) from
    header-only (code == 0), and whether the nRF was actually pushed (nrf > 0)
    versus skipped by the device as already-current/absent (nrf == 0).

    After the device reboots and the boardloader installs the new boot header,
    reconnect and call `update()` with the firmware modules to run phase 2.

    Custom (unofficial) firmware is a first-class authenticated variant
    (FW_VARIANT_CUSTOM) in the manifest, so the device derives custom-ness from
    the authenticated variant itself -- it requires an unlocked bootloader and
    runs the firmware unprivileged with a boot warning, storage-isolated. No host
    flag is needed.

    Provide `nrf_image` + `nrf_co_path` (+ `nrf_image_hash`, an update-required
    hint) to also OTA the nRF (BLE co-processor) firmware in the same session:
    the nRF MCUboot image is a model-tree leaf under the same boot-header
    signature, delivered while the current bootloader still provides the (BLE)
    link. A phase-1 FirmwareRequest carries `coprocessor_index`: 0 = the
    bootloader code, 1 = the nRF image -- so serve the matching source (the
    device rejects nothing here; the two never overlap on offset). If the running
    nRF is already current the device requests nothing for it.
    """
    if session.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = session.call(
        messages.FirmwareBegin(
            boot_header=boot_header,
            module_headers=module_headers,
            code_length=len(code) if code else None,
            nrf_length=len(nrf_image) if nrf_image else None,
            nrf_co_path=nrf_co_path,
            nrf_image_hash=nrf_image_hash,
        )
    )

    # The device drives the request loop, tagging each FirmwareRequest with the
    # image it wants: coprocessor_index 0 = the bootloader code (requested only if
    # the current code does not conform to the new header), 1 = the nRF image.
    # Track bytes served per image so the caller knows what the device actually
    # pulled (an already-current nRF is simply never requested).
    served = {"code": 0, "nrf": 0}
    while isinstance(resp, messages.FirmwareRequest):
        is_nrf = (resp.coprocessor_index or 0) != 0
        src = nrf_image if is_nrf else code
        assert src is not None, "device requested image bytes but none supplied"
        length = resp.length
        payload = src[resp.offset : resp.offset + length]
        digest = blake2s(payload).digest()
        resp = session.call(messages.FirmwareUpload(payload=payload, hash=digest))
        served["nrf" if is_nrf else "code"] += length
        progress_update(length)

    messages.Success.ensure_isinstance(resp)
    return served


def get_hash(session: Session, challenge: bytes | None) -> bytes:
    return session.call(
        messages.GetFirmwareHash(challenge=challenge), expect=messages.FirmwareHash
    ).hash
