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

"""Merkle-tree (``pq_secure_boot``) firmware images.

A pq_secure release is not one file. The signed boot header lives at the start
of ``bootloader.bin`` and carries ``firmware_root``; the firmware image
(``<variant>.bin``) opens with a manifest that commits each module's code, plus
the Merkle co-path folding that manifest up to ``firmware_root``. Neither half
is meaningful alone, which is why:

* :class:`PqSecureFirmware` deliberately has no ``verify()`` and no ``model()``
  -- the manifest carries neither a signature nor a ``hw_model``.
* :class:`PqSecureBundle` pairs it with the bootloader image and is the only
  thing here that satisfies the ``FirmwareType`` protocol.

Everything in this module reads and checks; nothing builds or signs. The signer
lives in ``core/tools/trezor_core_tools`` and imports the shared parts from
here, so device, signer and host cannot drift.
"""

from __future__ import annotations

import hashlib
import json
import struct
import typing as t
import zipfile
from enum import IntEnum
from pathlib import Path

import construct as c
from construct_classes import subcon

from .. import merkle_tree
from ..construct_helpers import EnumAdapter, TupleAdapter
from .core import BootableImage
from .models import Model
from .sanity_struct import SanityCheckedStruct
from .util import FirmwareIntegrityError

__all__ = [
    "BundleSource",
    "CHAIN_SEED_TAG",
    "CHAIN_STEP_TAG",
    "DEFAULT_CHUNK_SIZE",
    "ENTRY_FLAG_BOOT",
    "FW_MANIFEST_PROOF_MAX_NODES",
    "FW_MANIFEST_REGION",
    "FirmwareVariant",
    "ManifestEntry",
    "ModuleType",
    "PqSecureBundle",
    "PqSecureFirmware",
    "PqSecureManifest",
    "PqSecureNrf",
    "authenticity_bytes",
    "module_chain_intermediates",
    "module_code_hash",
    "variant_leaf",
]

#: Where a bundle can be read from: its directory, its zip, or an open stream
#: of that zip.
BundleSource = t.Union[str, Path, t.IO[bytes]]
Reader = t.Callable[[str], bytes]
Exists = t.Callable[[str], bool]

MANIFEST_MAGIC = b"TRZD"

# Fixed layout constants, mirrored from sec/image/inc/sec/boot_header.h. The
# manifest region is a reserve, not a struct: manifest + proof, then padding out
# to FW_MANIFEST_REGION, and the first module's code starts after it.
FW_MANIFEST_REGION = 0x400
FW_MANIFEST_PROOF_MAX_NODES = 4

# Smart-hashing chunk size (FW_CHUNK_SIZE). Per-module in the manifest, though
# every module currently uses this value. Modules are NOT padded to a multiple
# of it, so a module's last chunk may be partial.
DEFAULT_CHUNK_SIZE = 0x2000

# Chain domain tags: distinct tags separate the two constructions -- 0x01 for the
# length-bound seed, 0x02 for each fold step.
CHAIN_SEED_TAG = b"\x01"
CHAIN_STEP_TAG = b"\x02"

# Byte sizes of the manifest header and one entry. Computed rather than derived
# from SUBCON because the entry array is length-prefixed, so the struct has no
# fixed size; checked against the parsed form in _manifest_span().
_MANIFEST_HEADER_SIZE = 4 + 4 + 4 + 32 + 4  # magic, variant, version, tr_root, count
_MANIFEST_ENTRY_SIZE = 4 * 5 + 32
_MANIFEST_COUNT_OFFSET = 4 + 4 + 4 + 32  # module_count, the last header field
_PROOF_COUNT_SIZE = 4


class FirmwareVariant(IntEnum):
    """``fw_variant_t`` -- the authenticated storage-separation axis.

    Values match ``vendor_fw_type_t``, so a variant maps to the same
    ``firmware_type`` byte under either scheme.
    """

    NONE = 0
    CUSTOM = 1
    UNIVERSAL = 2
    BITCOIN_ONLY = 3
    PRODTEST = 4


class ModuleType(IntEnum):
    """``fw_module_type_t`` -- a module's role, bound into the leaf."""

    SECMON = 1
    APP = 2
    PRODTEST = 3


#: The entry the bootloader hands control to. Exactly one per manifest.
ENTRY_FLAG_BOOT = 0x1


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def module_code_hash(code: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> bytes:
    """The manifest's ``code_hash`` for a module's code.

    Domain-tagged, length-bound, folded LAST chunk -> FIRST so that chunk 0 ends
    up outermost and the device can verify chunks in the order it receives them.
    Mirrors ``firmware_module_code_hash()`` byte for byte::

        seed = H(0x01 || size_le32)
        for k = n-1 .. 0:  H = H(0x02 || H || chunk_k)
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    h = _sha256(CHAIN_SEED_TAG + struct.pack("<I", len(code)))
    n = (len(code) + chunk_size - 1) // chunk_size
    for k in reversed(range(n)):
        h = _sha256(CHAIN_STEP_TAG + h + code[k * chunk_size : (k + 1) * chunk_size])
    return h


def module_chain_intermediates(
    code: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> list[bytes]:
    """The intermediate chain hashes for chunks 0 .. n-2, in consumption order.

    Each rides inline on its chunk's ``FirmwareUpload.prev_hash``; the device
    folds it with the chunk and compares against the running expected value,
    starting from the authenticated ``code_hash``. The innermost chunk (n-1) is
    absent because the device derives the seed itself, and a single-chunk module
    needs nothing at all.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    n = (len(code) + chunk_size - 1) // chunk_size
    h = _sha256(CHAIN_SEED_TAG + struct.pack("<I", len(code)))
    out: list[bytes] = []
    for idx, k in enumerate(reversed(range(n))):
        h = _sha256(CHAIN_STEP_TAG + h + code[k * chunk_size : (k + 1) * chunk_size])
        if idx < n - 1:
            out.append(h)
    out.reverse()
    return out


def authenticity_bytes(manifest: bytes) -> bytes:
    """The manifest bytes a variant leaf is computed over.

    Identical to `manifest`, EXCEPT for the custom variant, where everything the
    creator controls is zeroed so that any creator's app folds to the single
    founder-signed custom slot: the firmware version, and the app entry's
    ``size`` + ``code_hash``. The app's type, flags, addr and chunk_size stay
    authenticated, as does the whole secmon entry -- chunk_size sits before the
    zeroed tail precisely so it keeps being covered. Mirrors
    ``boot_header_variant_leaf()`` byte for byte.
    """
    (variant,) = struct.unpack_from("<I", manifest, 4)
    if variant != FirmwareVariant.CUSTOM:
        return manifest
    (module_count,) = struct.unpack_from("<I", manifest, _MANIFEST_COUNT_OFFSET)
    buf = bytearray(manifest)
    buf[8:12] = b"\x00" * 4  # firmware_version
    for i in range(module_count):
        off = _MANIFEST_HEADER_SIZE + i * _MANIFEST_ENTRY_SIZE
        (module_type,) = struct.unpack_from("<I", manifest, off)
        if module_type == ModuleType.APP:
            # size (+16, 4 B) and code_hash (+20, 32 B) -- a contiguous tail.
            buf[off + 16 : off + 52] = b"\x00" * 36
            break
    return bytes(buf)


def variant_leaf(manifest: bytes) -> bytes:
    """A variant's Merkle leaf: ``H(0x00 || authenticity_bytes(manifest))``.

    The node the founder tree combines and the device folds up to
    ``firmware_root``.
    """
    return merkle_tree.leaf_hash(authenticity_bytes(manifest))


class ManifestEntry(SanityCheckedStruct):
    """One module in the manifest directory (``firmware_manifest_entry_t``)."""

    module_type: ModuleType | int
    flags: int
    addr: int
    chunk_size: int
    size: int
    code_hash: bytes

    # fmt: off
    SUBCON = c.Struct(
        "module_type" / EnumAdapter(c.Int32ul, ModuleType),
        "flags" / c.Int32ul,
        "addr" / c.Int32ul,      # offset from the firmware region start
        "chunk_size" / c.Int32ul,
        "size" / c.Int32ul,
        "code_hash" / c.Bytes(32),
    )
    # fmt: on

    @property
    def is_boot(self) -> bool:
        return bool(self.flags & ENTRY_FLAG_BOOT)


class PqSecureManifest(SanityCheckedStruct):
    """The authenticated directory at the start of a firmware image.

    Note what is NOT here: no signature, and no ``hw_model``. Authenticity comes
    from folding this to the boot header's ``firmware_root``; the model comes
    from the boot header.
    """

    firmware_variant: FirmwareVariant | int
    firmware_version: tuple[int, int, int, int]
    translations_root: bytes
    entries: list[ManifestEntry] = subcon(ManifestEntry)

    # fmt: off
    SUBCON = c.Struct(
        "_magic" / c.Const(MANIFEST_MAGIC),
        "firmware_variant" / EnumAdapter(c.Int32ul, FirmwareVariant),
        "firmware_version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "translations_root" / c.Bytes(32),
        "entries" / c.PrefixedArray(c.Int32ul, ManifestEntry.SUBCON),
    )
    # fmt: on

    @property
    def is_custom(self) -> bool:
        return self.firmware_variant == FirmwareVariant.CUSTOM

    def boot_entry(self) -> ManifestEntry:
        boot = [e for e in self.entries if e.is_boot]
        if len(boot) != 1:
            raise FirmwareIntegrityError(
                f"manifest has {len(boot)} boot entries, expected exactly 1"
            )
        return boot[0]

    def entry(self, module_type: ModuleType) -> ManifestEntry | None:
        return next((e for e in self.entries if e.module_type == module_type), None)


class PqSecureFirmware:
    """A pq_secure firmware image -- one variant's ``<variant>.bin``.

    Held as raw bytes plus a parsed view, rather than as a single struct,
    because the manifest addresses modules by offset INTO this image: the
    device reads code at ``entry.addr``, so the bytes are the authority and a
    rebuilt struct would not be.

    Not verifiable on its own -- see the module docstring.
    """

    def __init__(self, data: bytes) -> None:
        self.data = data
        if data[:4] != MANIFEST_MAGIC:
            raise FirmwareIntegrityError("no firmware manifest at the image start")
        if len(data) < _MANIFEST_HEADER_SIZE:
            raise FirmwareIntegrityError("firmware image shorter than a manifest")
        # Locate the manifest's end BEFORE parsing it, so the struct is handed
        # exactly its own bytes. That makes SanityCheckedStruct's round-trip
        # check meaningful: it then asserts the sizes above against the real
        # layout, instead of failing trivially on the trailing image.
        (module_count,) = struct.unpack_from("<I", data, _MANIFEST_COUNT_OFFSET)
        self._manifest_len = _MANIFEST_HEADER_SIZE + module_count * _MANIFEST_ENTRY_SIZE
        if self._manifest_len > len(data):
            raise FirmwareIntegrityError(
                f"manifest claims {module_count} modules, which runs past the image"
            )
        self.manifest = PqSecureManifest.parse(data[: self._manifest_len])
        proof_off = self._manifest_len
        if proof_off + _PROOF_COUNT_SIZE > len(data):
            raise FirmwareIntegrityError("firmware image truncated before the proof")
        (count,) = struct.unpack_from("<I", data, proof_off)
        if count > FW_MANIFEST_PROOF_MAX_NODES:
            raise FirmwareIntegrityError(
                f"manifest proof has {count} nodes, max {FW_MANIFEST_PROOF_MAX_NODES}"
            )
        nodes_off = proof_off + _PROOF_COUNT_SIZE
        self._region_len = nodes_off + count * 32
        if self._region_len > FW_MANIFEST_REGION:
            raise FirmwareIntegrityError(
                f"manifest region {self._region_len} B exceeds the "
                f"{FW_MANIFEST_REGION} B reserve"
            )
        #: The variant's Merkle co-path from its leaf up to ``firmware_root``.
        #: Empty for a single-variant release.
        self.proof = [
            data[nodes_off + i * 32 : nodes_off + (i + 1) * 32] for i in range(count)
        ]

    @classmethod
    def parse(cls, data: bytes) -> PqSecureFirmware:
        try:
            return cls(data)
        except FirmwareIntegrityError:
            raise
        except Exception as e:
            raise FirmwareIntegrityError("Invalid pq_secure firmware image") from e

    @classmethod
    def looks_like(cls, data: bytes) -> bool:
        return data[:4] == MANIFEST_MAGIC

    @property
    def manifest_bytes(self) -> bytes:
        """The manifest alone -- the span the variant leaf is computed over."""
        return self.data[: self._manifest_len]

    @property
    def manifest_region(self) -> bytes:
        """``[manifest || proof]`` -- what the device parses at the image start,
        and the second half of the interaction-less consent preamble."""
        return self.data[: self._region_len]

    def authenticity_bytes(self) -> bytes:
        """The manifest bytes this variant's leaf is computed over."""
        return authenticity_bytes(self.manifest_bytes)

    def variant_leaf(self) -> bytes:
        """This variant's Merkle leaf: ``H(0x00 || authenticity_bytes)``."""
        return variant_leaf(self.manifest_bytes)

    def firmware_root(self) -> bytes:
        """Fold this variant's leaf through its embedded co-path."""
        return merkle_tree.evaluate_proof(self.authenticity_bytes(), self.proof)

    def module_code(self, entry: ManifestEntry) -> bytes:
        code = self.data[entry.addr : entry.addr + entry.size]
        if len(code) != entry.size:
            raise FirmwareIntegrityError(
                f"module at 0x{entry.addr:x} runs past the image "
                f"({len(code)} of {entry.size} B present)"
            )
        return code

    def validate_code_hashes(self) -> None:
        """Check every module's code against its authenticated ``code_hash``."""
        for entry in self.manifest.entries:
            actual = module_code_hash(self.module_code(entry), entry.chunk_size)
            if actual != entry.code_hash:
                name = getattr(entry.module_type, "name", entry.module_type)
                raise FirmwareIntegrityError(f"code_hash mismatch for module {name}")

    def chunk_prev_hashes(self) -> dict[int, bytes]:
        """Map each chunk's END image offset to its chain hash, for
        ``firmware.update(prev_hashes=...)``.

        Keying by the END offset means a transport block spanning several chunks
        is looked up directly by ``request.offset + request.length``, with no
        host-side knowledge of the block size. An absent key is correct, not an
        error: the innermost chunk of a module derives the seed on-device, and
        the manifest region carries no chunk at all.
        """
        out: dict[int, bytes] = {}
        for entry in self.manifest.entries:
            code = self.module_code(entry)
            for k, h in enumerate(module_chain_intermediates(code, entry.chunk_size)):
                out[entry.addr + (k + 1) * entry.chunk_size] = h
        return out


class PqSecureNrf(t.NamedTuple):
    """The nRF co-processor payload a release may carry.

    The image is a model-level leaf of the founder tree, covered by the same
    boot-header signature, so ``co_path`` is unsigned metadata that the DEVICE
    folds and checks -- carrying it in the clear is safe.
    """

    image: bytes
    co_path: bytes  # concatenated 32-byte nodes, nRF leaf -> modelRoot
    image_hash: bytes  # update-required hint; the device may skip on a match
    model_id: str

    @property
    def co_path_nodes(self) -> int:
        return len(self.co_path) // 32


class PqSecureBundle:
    """A pq_secure release: a bootloader image, one variant's firmware, and an
    optional nRF payload.

    This is the unit the host installs and the only thing here that can be
    verified, because authenticity crosses the two halves: the boot header is
    signed and carries ``firmware_root``; the firmware folds to it.
    """

    def __init__(
        self,
        bootloader_bytes: bytes,
        firmware: PqSecureFirmware,
        nrf: PqSecureNrf | None = None,
        variant_name: str | None = None,
    ) -> None:
        #: Kept alongside the parsed form: the consent preamble and the
        #: streamed code must be the bytes that were signed, not a rebuild.
        self.bootloader_bytes = bootloader_bytes
        self.bootloader = BootableImage.parse(bootloader_bytes)
        self.firmware = firmware
        self.nrf = nrf
        self.variant_name = variant_name

    # --- loading -----------------------------------------------------------

    @staticmethod
    def _opener(src: BundleSource) -> tuple[Reader, Exists]:
        """Uniform access to a bundle directory, a zip path, or an open zip."""
        if not isinstance(src, (str, Path)):  # an already-open binary stream
            zf = zipfile.ZipFile(src)
            names = set(zf.namelist())
            return zf.read, names.__contains__
        path = Path(src)
        if path.is_dir():
            return (
                lambda name: (path / name).read_bytes(),
                lambda name: (path / name).exists(),
            )
        if zipfile.is_zipfile(path):
            zf = zipfile.ZipFile(path)
            names = set(zf.namelist())
            return zf.read, names.__contains__
        raise ValueError(f"{path} is neither a directory nor a zip bundle")

    @classmethod
    def variants(cls, src: BundleSource) -> list[str]:
        """The variant names a bundle offers, without loading any of them."""
        read, exists = cls._opener(src)
        if not exists("bundle.json"):
            return []
        meta = json.loads(read("bundle.json"))
        return [
            Path(v["firmware"]).stem
            for v in meta.get("variants", [])
            if "firmware" in v
        ]

    @classmethod
    def load(cls, src: BundleSource, variant: str | None = None) -> PqSecureBundle:
        """Load from a ``build_firmware_pq`` bundle.

        Accepts the bundle directory, the path to its zip, or an already-open
        binary stream of that zip -- the CLI has the bytes in hand and should not
        have to spill them to a file to read them.
        """
        read, exists = cls._opener(src)
        meta = json.loads(read("bundle.json")) if exists("bundle.json") else {}
        variant = cls._pick_variant(meta, variant, exists)

        firmware = PqSecureFirmware.parse(read(f"{variant}.bin"))
        nrf = None
        nrf_meta = meta.get("nrf")
        if nrf_meta:
            image = read(nrf_meta["image"])
            if len(image) != nrf_meta["length"]:
                raise FirmwareIntegrityError(
                    f"nRF image is {len(image)} B, bundle.json says "
                    f"{nrf_meta['length']} B"
                )
            nrf = PqSecureNrf(
                image=image,
                co_path=b"".join(bytes.fromhex(n) for n in nrf_meta["co_path"]),
                image_hash=bytes.fromhex(nrf_meta["image_hash"]),
                model_id=nrf_meta.get("model_id", ""),
            )
        return cls(read("bootloader.bin"), firmware, nrf, variant)

    @staticmethod
    def _pick_variant(
        meta: dict, requested: str | None, exists: t.Callable[[str], bool]
    ) -> str:
        available = [
            Path(v["firmware"]).stem
            for v in meta.get("variants", [])
            if "firmware" in v
        ]
        if requested is not None:
            if available and requested not in available:
                raise ValueError(
                    f"no variant {requested!r} in the bundle; have: "
                    f"{', '.join(sorted(available))}"
                )
            if not exists(f"{requested}.bin"):
                raise ValueError(f"bundle has no {requested}.bin")
            return requested
        if len(available) == 1:
            return available[0]
        if not available:
            raise ValueError("bundle.json lists no variants; pass one explicitly")
        raise ValueError(
            "bundle holds several variants; pick one of: "
            f"{', '.join(sorted(available))}"
        )

    # --- the FirmwareType protocol -----------------------------------------

    def verify(self, dev_keys: bool = False) -> None:
        """Verify the release offline, end to end.

        Checks the boot-header signature, that this variant folds to the
        ``firmware_root`` THAT header commits to, and that every module's code
        matches its authenticated ``code_hash``.

        The nRF payload is only sanity-checked here: its fold to ``modelRoot``
        is verified on-device against the signed header, and the host has no
        independent root to check it against.
        """
        self.bootloader.verify(dev_keys=dev_keys)
        signed_root = bytes(self.bootloader.header.firmware_root)
        folded = self.firmware.firmware_root()
        if folded != signed_root:
            raise FirmwareIntegrityError(
                f"firmware does not belong to this bootloader: folds to "
                f"{folded.hex()[:16]}, header commits to {signed_root.hex()[:16]}"
            )
        self.firmware.validate_code_hashes()
        if self.nrf is not None and not self.nrf.co_path:
            raise FirmwareIntegrityError("nRF payload has no co-path to fold")

    def digest(self) -> bytes:
        """``firmware_root`` -- what the device shows as the fingerprint.

        Deliberately the same value ``check_firmware_header`` reports, so a
        ``--fingerprint`` given on the host means what the screen says.
        """
        return bytes(self.bootloader.header.firmware_root)

    def model(self) -> Model | None:
        """From the boot header; the manifest carries no ``hw_model``."""
        return self.bootloader.model()

    # --- what the upload path needs ----------------------------------------

    @property
    def boot_header(self) -> bytes:
        """The signed boot header at the start of the bootloader image."""
        return self.bootloader_bytes[: self.bootloader.header.header_len]

    @property
    def bootloader_code(self) -> bytes:
        """Everything after the boot header.

        Always offered to the device in phase 1; the DEVICE decides whether it
        needs it (a header-only update requests nothing).
        """
        return self.bootloader_bytes[self.bootloader.header.header_len :]

    def boot_header_prefix(self) -> bytes:
        """The digest-relevant part of the boot header: authenticated part plus
        the Merkle proof, stopping before the unauthenticated part.

        The cut is derived from parsed fields rather than fixed offsets, but
        applied to the ORIGINAL bytes -- the device recomputes the same boundary
        from the same content, so the two must agree exactly.

        It stops there because the unauth part holds the signatures and the
        ``firmware_type`` byte that the bootloader itself rewrites while
        staging; including either would make the digest unreproducible from an
        installed header.
        """
        prefix_len = (
            self.bootloader.header.auth_len
            + 4  # the proof's node_count
            + 32 * len(self.bootloader.unauth.merkle_proof)
        )
        if prefix_len > self.bootloader.header.header_len:
            raise FirmwareIntegrityError(
                f"boot header prefix ({prefix_len} B) runs past the header "
                f"({self.bootloader.header.header_len} B)"
            )
        return self.bootloader_bytes[:prefix_len]

    def consent_preamble(self) -> bytes:
        """``RebootToBootloader.firmware_preamble`` for this release.

        The preimage of the interaction-less consent digest: firmware hashes it
        to identify what the user is confirming, and the bootloader recomputes
        the same digest over what is actually delivered, installing without
        asking again only if they match.
        """
        return self.boot_header_prefix() + self.firmware.manifest_region

    def chunk_prev_hashes(self) -> dict[int, bytes]:
        return self.firmware.chunk_prev_hashes()

    @property
    def version(self) -> tuple[int, int, int, int]:
        return self.firmware.manifest.firmware_version
