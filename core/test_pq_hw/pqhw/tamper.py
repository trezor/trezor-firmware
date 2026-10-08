"""Single-fault releases: a genuine upload with one thing broken, and the
rejection the device must answer it with.

The same cases as the manual wire harness (core/tools/trezor_core_tools/
firmware_pq_update.py, `--tamper`), whose expected messages they share; that
tool is one script, so the mutations are restated here as functions over
flows.Upload. Kept apart from the flows so a case reads as data.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass

from trezorlib.firmware import pq_secure
from trezorlib.firmware.pq_secure import PqSecureBundle

from .flows import Upload

#: byte of the upload flipped by corrupt-chunk: inside the app module
CORRUPT_OFFSET = 0x80000


@dataclass(frozen=True)
class Tamper:
    name: str
    #: substring of the device's Failure message
    expect: str
    #: where it is refused: 1 = FirmwareBegin, 2 = the firmware stream
    phase: int
    #: what it breaks, for the report
    what: str
    alter: t.Callable[[Upload, PqSecureBundle], Upload]
    #: the variant the case needs (the custom layout cases)
    variant: str = "universal"
    #: refused before the confirm screen; False for the nRF co-path, which is
    #: checked when the nRF stage runs, after the confirm and after the
    #: bootloader staging has already overwritten part of the firmware area
    before_confirm: bool = True


def _flip(data: bytes, offset: int) -> bytes:
    b = bytearray(data)
    b[offset] ^= 0xFF
    return bytes(b)


def _app_size_offset(bundle: PqSecureBundle) -> int:
    """Offset of the APP entry's size field in the manifest region."""
    entries = bundle.firmware.manifest.entries
    app = next(
        i for i, e in enumerate(entries) if e.module_type == pq_secure.ModuleType.APP
    )
    # size follows type + flags + addr + chunk_size in each entry
    return pq_secure._MANIFEST_HEADER_SIZE + app * pq_secure._MANIFEST_ENTRY_SIZE + 16


def _with_app_size(up: Upload, bundle: PqSecureBundle, delta: int) -> Upload:
    off = _app_size_offset(bundle)
    m = bytearray(up.module_headers)
    size = int.from_bytes(m[off : off + 4], "little") + delta
    m[off : off + 4] = size.to_bytes(4, "little")
    return up.but(module_headers=bytes(m))


def _flip_all_hashes(up: Upload, _b: PqSecureBundle) -> Upload:
    # the device picks the block size, so every inline hash is flipped
    return up.but(prev_hashes={o: _flip(h, 0) for o, h in up.prev_hashes.items()})


def _no_nrf(up: Upload, _b: PqSecureBundle) -> Upload:
    assert up.nrf_image, "no-nrf needs a release that carries an nRF image"
    return up.but(nrf_image=None, nrf_co_path=None, nrf_image_hash=None)


def _nrf_copath(up: Upload, _b: PqSecureBundle) -> Upload:
    assert up.nrf_co_path, "nrf-copath needs a release that carries an nRF image"
    return up.but(nrf_co_path=_flip(up.nrf_co_path, 0))


PHASE1 = [
    Tamper(
        "bl-sig",
        "Invalid boot header signature",
        1,
        "a boot-header signature byte flipped: refused before the confirm and "
        "before anything is erased",
        lambda up, _b: up.but(
            boot_header=_flip(up.boot_header, len(up.boot_header) // 2)
        ),
    ),
    Tamper(
        "wrong-model",
        "Invalid boot header",
        1,
        "hw_model in the boot header changed",
        lambda up, _b: up.but(boot_header=_flip(up.boot_header, 4)),
    ),
    Tamper(
        "fw-sig",
        "Firmware manifest not authentic",
        1,
        "a manifest byte flipped: the variant leaf no longer folds to firmware_root",
        lambda up, _b: up.but(module_headers=_flip(up.module_headers, 64)),
    ),
    Tamper(
        "nrf-copath",
        "nRF image not in founder tree",
        1,
        "nRF co-path byte flipped: the whole upload is refused, even with the "
        "nRF already current (after the confirm, when the nRF stage runs)",
        _nrf_copath,
        before_confirm=False,
    ),
    Tamper(
        "no-nrf",
        "Release carries no co-processor image",
        1,
        "nRF fields withheld from a device that has an nRF",
        _no_nrf,
    ),
    Tamper(
        "custom-app-size",
        "Invalid firmware manifest",
        1,
        "custom app size +4 MiB (folds: the size is not authenticated for custom)",
        lambda up, b: _with_app_size(up, b, 0x0040_0000),
        variant="custom",
    ),
    Tamper(
        "custom-app-unaligned",
        "Invalid firmware manifest",
        1,
        "custom app size +1 byte: only the block-alignment check catches it",
        lambda up, b: _with_app_size(up, b, 1),
        variant="custom",
    ),
]

PHASE2 = [
    Tamper(
        "corrupt-chunk",
        "Invalid chunk hash",
        2,
        f"firmware byte {CORRUPT_OFFSET:#x} flipped, hashes genuine",
        lambda up, _b: up.but(firmware=_flip(up.firmware, CORRUPT_OFFSET)),
    ),
    Tamper(
        "chunk-hash",
        "Invalid chunk hash",
        2,
        "every inline prev_hash flipped",
        _flip_all_hashes,
    ),
    Tamper(
        "missing-chunk-hash",
        "missing chunk hash",
        2,
        "inline prev_hashes dropped",
        lambda up, _b: up.but(prev_hashes={}),
    ),
]

#: phase 2 streams a sibling variant of what phase 1 approved
VARIANT_SWAP = "Firmware variant mismatch"
#: firmware-side refusals of the interaction-less preamble
BAD_PREAMBLE = "Invalid firmware header"
VENDOR_CHANGE = "Different firmware vendor"
#: phase 2 with no phase 1 on a fresh bootloader boot
BARE_PHASE2 = "must begin with FirmwareBegin"


def variant_swap(up: Upload, other: PqSecureBundle) -> Upload:
    return up.but(firmware=other.firmware.data, prev_hashes=other.chunk_prev_hashes())


def truncated_preamble(bundle: PqSecureBundle) -> bytes:
    p = bundle.consent_preamble()
    return p[: len(p) // 3]


def other_vendor_preamble(bundle: PqSecureBundle, other: PqSecureBundle) -> bytes:
    """This release's boot header with a sibling variant's manifest: the
    variant maps to a different vendor string."""
    return bundle.boot_header_prefix() + other.firmware.manifest_region
