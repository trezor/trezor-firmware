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

"""Merkle-tree (``pq_secure_boot``) release images: firmware manifest, boot header
prefix and the release bundle. Read and verify only; the signer in
``core/tools/trezor_core_tools`` imports the shared parts from here.
Design: docs/core/embed-arch/firmware-merkle-tree.md
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
from .core import BootableImage, BootHeader
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
    "boot_header_prefix",
    "consent_preamble",
    "module_chain_intermediates",
    "module_code_hash",
    "variant_leaf",
]

#: A bundle directory, a zip path, or an open stream of the zip.
BundleSource = t.Union[str, Path, t.IO[bytes]]
Reader = t.Callable[[str], bytes]
Exists = t.Callable[[str], bool]

MANIFEST_MAGIC = b"TRZD"

# Manifest region reserve (manifest + proof, padded); must match boot_header.h.
FW_MANIFEST_REGION = 0x400
FW_MANIFEST_PROOF_MAX_NODES = 4

# FW_CHUNK_SIZE; modules are not padded to it, so a last chunk may be partial.
DEFAULT_CHUNK_SIZE = 0x2000

# Chain domain tags: 0x01 for the length-bound seed, 0x02 for each fold step.
CHAIN_SEED_TAG = b"\x01"
CHAIN_STEP_TAG = b"\x02"

# Manifest header/entry sizes; SUBCON has no fixed size (length-prefixed array).
_MANIFEST_HEADER_SIZE = 4 + 4 + 4 + 32 + 4  # magic, variant, version, tr_root, count
_MANIFEST_ENTRY_SIZE = 4 * 5 + 32
_MANIFEST_COUNT_OFFSET = 4 + 4 + 4 + 32  # module_count, the last header field
_PROOF_COUNT_SIZE = 4


class FirmwareVariant(IntEnum):
    """``fw_variant_sec_t``: RM(1,5) codewords carried by the manifest and the boot
    header's ``firmware_type``; no single bit flip moves between variants."""

    INVALID = 0x00000000
    NONE = 0xCCCCCCCC
    CUSTOM = 0x33333333
    UNIVERSAL = 0x5A5A5A5A
    BITCOIN_ONLY = 0xA5A5A5A5
    PRODTEST = 0x66666666


class ModuleType(IntEnum):
    """``fw_module_type_t`` -- a module's role, bound into the leaf."""

    SECMON = 1
    APP = 2
    PRODTEST = 3


#: The entry the bootloader hands control to; exactly one per manifest.
ENTRY_FLAG_BOOT = 0x1


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def module_code_hash(code: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> bytes:
    """The manifest's ``code_hash``; must match ``firmware_module_code_hash()``.

    ``H = H(0x01 || size_le32)``, then ``H = H(0x02 || H || chunk_k)`` for
    k = n-1 .. 0, so chunk 0 is outermost and verifiable first.
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
    """Chain hashes for chunks 0 .. n-2 (``FirmwareUpload.prev_hash``), in
    consumption order; the innermost chunk's seed is derived on-device."""
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
    """The manifest bytes a variant leaf hashes; must match
    ``boot_header_variant_leaf()`` byte for byte.

    Custom variant only: firmware_version and the APP entry's size + code_hash
    are zeroed; a malformed custom manifest is hashed verbatim.
    """
    (variant,) = struct.unpack_from("<I", manifest, 4)
    if variant != FirmwareVariant.CUSTOM:
        return manifest
    (module_count,) = struct.unpack_from("<I", manifest, _MANIFEST_COUNT_OFFSET)
    app_off = None
    for i in range(module_count):
        off = _MANIFEST_HEADER_SIZE + i * _MANIFEST_ENTRY_SIZE
        (module_type,) = struct.unpack_from("<I", manifest, off)
        if module_type == ModuleType.APP:
            app_off = off
            break
    # size (+16, 4 B) and code_hash (+20, 32 B) form a contiguous tail
    a_off = len(manifest) if app_off is None else app_off + 16
    a_len = 0 if app_off is None else 36
    if app_off is None or a_off + a_len > len(manifest) or a_off < 12:
        return manifest
    buf = bytearray(manifest)
    buf[8:12] = b"\x00" * 4  # firmware_version
    buf[a_off : a_off + a_len] = b"\x00" * a_len
    return bytes(buf)


def variant_leaf(manifest: bytes) -> bytes:
    """A variant's Merkle leaf: ``H(0x00 || authenticity_bytes(manifest))``."""
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
    """The authenticated module directory at the start of a firmware image; it
    carries no signature and no ``hw_model``, both come from the boot header."""

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
    """One variant's ``<variant>.bin``: raw bytes (modules are addressed by offset
    into them) plus the parsed manifest. Verifiable only via PqSecureBundle."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        if data[:4] != MANIFEST_MAGIC:
            raise FirmwareIntegrityError("no firmware manifest at the image start")
        if len(data) < _MANIFEST_HEADER_SIZE:
            raise FirmwareIntegrityError("firmware image shorter than a manifest")
        # hand the struct exactly its own bytes so the round-trip check is meaningful
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
        #: Co-path from the variant leaf to ``firmware_root``; empty if single-variant.
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
        """The manifest alone, the span the variant leaf is computed over."""
        return self.data[: self._manifest_len]

    @property
    def manifest_region(self) -> bytes:
        """``[manifest || proof]``: what the device parses, and the second half of
        the consent preamble."""
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
        """Chunk END offset -> chain hash, for ``firmware.update(prev_hashes=...)``;
        a block is looked up by ``offset + length``. Absent keys are expected
        (innermost chunk of a module, manifest region)."""
        out: dict[int, bytes] = {}
        for entry in self.manifest.entries:
            code = self.module_code(entry)
            for k, h in enumerate(module_chain_intermediates(code, entry.chunk_size)):
                out[entry.addr + (k + 1) * entry.chunk_size] = h
        return out


class PqSecureNrf(t.NamedTuple):
    """The nRF co-processor payload of a release; ``co_path`` is unsigned metadata
    the device folds and checks against the signed boot header."""

    image: bytes
    co_path: bytes  # concatenated 32-byte nodes, nRF leaf -> modelRoot
    image_hash: bytes  # update-required hint; the device may skip on a match
    model_id: str

    @property
    def co_path_nodes(self) -> int:
        return len(self.co_path) // 32


# Must match BOOT_HEADER_MERKLE_PROOF_MAXLEN in sec/image/inc/sec/boot_header.h.
BOOT_HEADER_MERKLE_PROOF_MAXLEN = 256


def boot_header_prefix(header: bytes) -> bytes:
    """Authenticated part + Merkle proof of a raw boot header, cut before the
    unauth part (signatures, and the ``firmware_type`` the bootloader rewrites);
    must match the device's ``boot_header_prefix_extent()``."""
    # SUBCON, not BootHeader.parse: a bare header cannot round-trip the sanity rebuild
    hdr = BootHeader.SUBCON.parse(header)
    node_count = int.from_bytes(header[hdr.auth_len : hdr.auth_len + 4], "little")
    # same 256-node ceiling as boot_header_prefix_extent() on the device
    if node_count > BOOT_HEADER_MERKLE_PROOF_MAXLEN:
        raise FirmwareIntegrityError(
            f"boot header Merkle proof has {node_count} nodes, over the "
            f"{BOOT_HEADER_MERKLE_PROOF_MAXLEN}-node ceiling"
        )
    prefix_len = hdr.auth_len + 4 + 32 * node_count
    if prefix_len > len(header):
        raise FirmwareIntegrityError(
            f"boot header prefix ({prefix_len} B) runs past the header "
            f"({len(header)} B)"
        )
    return header[:prefix_len]


def consent_preamble(header: bytes, manifest_region: bytes) -> bytes:
    """Preimage of the interaction-less consent digest; the bootloader recomputes
    it over what is delivered and installs without asking again on a match."""
    return boot_header_prefix(header) + manifest_region


#: Release container (bundle.json) format this trezorlib speaks; must match
#: core/tools/trezor_core_tools/firmware_module.py. Flow: docs/core/build/xtask.md
CONTAINER_MAGIC = "TRZL"
#: Cross-model container: one self-contained per-model subtree each.
CONTAINER_SET_MAGIC = "TRZL-set"
CONTAINER_VERSION = 1


def _check_container(meta: dict, *, is_set: bool = False) -> dict:
    """Refuse a container of another format or version before reading any field.

    The container is unsigned by design: the boot header is the trust root, so a
    tampered container is a fail-closed DoS, never a forgery.
    """
    want = CONTAINER_SET_MAGIC if is_set else CONTAINER_MAGIC
    got = meta.get("format")
    if got is None:
        raise FirmwareIntegrityError(
            "bundle.json has no `format` -- it predates the versioned release "
            "container; rebuild the release"
        )
    if got != want:
        raise FirmwareIntegrityError(
            f"bundle.json is not a release container: format {got!r}, expected {want!r}"
        )
    version = meta.get("format_version")
    if version != CONTAINER_VERSION:
        raise FirmwareIntegrityError(
            f"bundle.json is release container v{version}, but this trezorlib "
            f"speaks v{CONTAINER_VERSION}"
        )
    return meta


def _check_set(root: dict) -> dict:
    """Check a cross-model container: every entry is a container and names the
    model it is filed under."""
    _check_container(root, is_set=True)
    for model, body in root.get("models", {}).items():
        _check_container(body)
        if body.get("model") != model:
            raise FirmwareIntegrityError(
                f"the entry filed under {model} names model {body.get('model')!r}"
            )
    return root


class PqSecureBundle:
    """A pq_secure release: bootloader image, one variant's firmware and an optional
    nRF payload. The only verifiable unit here: the boot header is signed and
    carries ``firmware_root``; the firmware folds to it."""

    def __init__(
        self,
        bootloader_bytes: bytes,
        firmware: PqSecureFirmware,
        nrf: PqSecureNrf | None = None,
        variant_name: str | None = None,
    ) -> None:
        #: Raw bytes kept: consent preamble and streamed code must be the signed bytes.
        self.bootloader_bytes = bootloader_bytes
        self.bootloader = BootableImage.parse(bootloader_bytes)
        self.firmware = firmware
        self.nrf = nrf
        self.variant_name = variant_name

    # --- loading -----------------------------------------------------------

    @staticmethod
    def _scoped(read: Reader, exists: Exists, prefix: str) -> tuple[Reader, Exists]:
        """The same reader, rooted at one model's subtree."""
        if not prefix:
            return read, exists
        return (lambda name: read(prefix + name), lambda name: exists(prefix + name))

    @classmethod
    def _enter(cls, src: BundleSource, model: str | None) -> tuple[Reader, Exists]:
        """Open a bundle, descending into ``<MODEL>/`` when it is a cross-model set."""
        read, exists = cls._opener(src)
        if not exists("bundle.json"):
            raise FirmwareIntegrityError(
                "not a pq_secure release: no bundle.json in the bundle"
            )
        root = json.loads(read("bundle.json"))
        if root.get("format") != CONTAINER_SET_MAGIC:
            if model is not None and root.get("model") != model:
                raise ValueError(f"this bundle is for {root.get('model')}, not {model}")
            return read, exists
        _check_set(root)
        available = sorted(root.get("models", {}))
        if model is None:
            if len(available) != 1:
                raise ValueError(
                    f"bundle covers several models; pick one of: {', '.join(available)}"
                )
            model = available[0]
        elif model not in available:
            raise ValueError(
                f"no model {model!r} in the bundle; have: {', '.join(available)}"
            )
        scoped_read, scoped_exists = cls._scoped(read, exists, f"{model}/")
        if not scoped_exists("bundle.json"):
            raise FirmwareIntegrityError(
                f"the bundle lists {model} but holds no {model}/bundle.json"
            )
        # the subtree must name the model it is filed under
        subtree = _check_container(json.loads(scoped_read("bundle.json")))
        if subtree.get("model") != model:
            raise FirmwareIntegrityError(
                f"the {model}/ subtree names model {subtree.get('model')!r}"
            )
        return scoped_read, scoped_exists

    @classmethod
    def models(cls, src: BundleSource) -> list[str]:
        """The models a bundle covers; one entry for a per-model bundle."""
        read, exists = cls._opener(src)
        if not exists("bundle.json"):
            return []
        root = json.loads(read("bundle.json"))
        if root.get("format") == CONTAINER_SET_MAGIC:
            return sorted(_check_set(root).get("models", {}))
        return [m] if (m := _check_container(root).get("model")) else []

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
    def variants(cls, src: BundleSource, model: str | None = None) -> list[str]:
        """The variant names a bundle offers, without loading any of them."""
        read, _ = cls._enter(src, model)
        meta = _check_container(json.loads(read("bundle.json")))
        return [v["variant"] for v in meta.get("variants", []) if "variant" in v]

    @classmethod
    def load(
        cls,
        src: BundleSource,
        variant: str | None = None,
        model: str | None = None,
    ) -> PqSecureBundle:
        """Load from an ``xtask release`` bundle (directory, zip path or open zip).

        ``model`` is required only for a cross-model set covering several models.
        Neither ``variant`` nor ``model`` is guessed here; the CLI picks both.
        """
        read, exists = cls._enter(src, model)
        meta = _check_container(json.loads(read("bundle.json")))
        variant = cls._pick_variant(meta, variant, exists)

        entry = next(v for v in meta["variants"] if v.get("variant") == variant)
        firmware = PqSecureFirmware.parse(read(entry["file"]))

        # (kind, index) is routing only; the device derives its own from build config
        nrf = None
        nrf_meta = next(
            (
                c
                for c in meta.get("coprocessors", [])
                if c.get("kind") == "nrf" and c.get("index", 0) == 0
            ),
            None,
        )
        if nrf_meta:
            image = read(nrf_meta["file"])
            if len(image) != nrf_meta["length"]:
                raise FirmwareIntegrityError(
                    f"nRF image is {len(image)} B, bundle.json says "
                    f"{nrf_meta['length']} B"
                )
            nrf = PqSecureNrf(
                image=image,
                co_path=b"".join(bytes.fromhex(n) for n in nrf_meta["co_path"]),
                image_hash=bytes.fromhex(nrf_meta["image_hash"]),
                model_id=nrf_meta.get("image_model_id", ""),
            )
        return cls(read(meta["bootloader"]["file"]), firmware, nrf, variant)

    @staticmethod
    def _with_file(meta: dict, variant: str, exists: t.Callable[[str], bool]) -> str:
        """Return `variant` once its image is known to be in the container."""
        entry = next(v for v in meta["variants"] if v.get("variant") == variant)
        name = entry.get("file")
        if name is None:
            raise ValueError(f"bundle.json names variant {variant!r} with no file")
        if not exists(name):
            raise ValueError(f"bundle has no {name}")
        return variant

    @classmethod
    def _pick_variant(
        cls, meta: dict, requested: str | None, exists: t.Callable[[str], bool]
    ) -> str:
        available = [v["variant"] for v in meta.get("variants", []) if "variant" in v]
        if requested is not None:
            if requested not in available:
                raise ValueError(
                    f"no variant {requested!r} in the bundle; have: "
                    f"{', '.join(sorted(available))}"
                )
            return cls._with_file(meta, requested, exists)
        if len(available) == 1:
            # a lone variant is picked unasked, so check its file is present here too
            return cls._with_file(meta, available[0], exists)
        if not available:
            raise ValueError("bundle.json lists no variants; pass one explicitly")
        raise ValueError(
            "bundle holds several variants; pick one of: "
            f"{', '.join(sorted(available))}"
        )

    # --- the FirmwareType protocol -----------------------------------------

    def verify(self, dev_keys: bool = False) -> None:
        """Verify offline: boot-header signature, this variant folds to the header's
        ``firmware_root``, every module's ``code_hash``. The nRF fold is only
        verifiable on-device."""
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
        """``firmware_root``: the fingerprint the device shows (same as
        ``check_firmware_header``)."""
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
        """Exactly ``code_length`` bytes of bootloader code, the extent the header
        signs; offered in phase 1, the device decides whether it needs it."""
        return bytes(self.bootloader.code)

    def boot_header_prefix(self) -> bytes:
        """See :func:`boot_header_prefix`."""
        return boot_header_prefix(self.bootloader_bytes)

    def consent_preamble(self) -> bytes:
        """``RebootToBootloader.firmware_preamble`` for this release; see
        :func:`consent_preamble`."""
        return consent_preamble(self.bootloader_bytes, self.firmware.manifest_region)

    def chunk_prev_hashes(self) -> dict[int, bytes]:
        return self.firmware.chunk_prev_hashes()

    @property
    def version(self) -> tuple[int, int, int, int]:
        return self.firmware.manifest.firmware_version
