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

import typing as t
from copy import copy
from dataclasses import asdict
from enum import Enum

import click
import construct as c
from construct_classes import Struct
from typing_extensions import Protocol, Self, runtime_checkable

from .. import cosi, firmware
from ..firmware import models as fw_models

SYM_OK = click.style("\u2714", fg="green")
SYM_FAIL = click.style("\u274c", fg="red")


class Status(Enum):
    VALID = click.style("VALID", fg="green", bold=True)
    INVALID = click.style("INVALID", fg="red", bold=True)
    MISSING = click.style("MISSING", fg="blue", bold=True)
    DEVEL = click.style("DEVEL", fg="red", bold=True)

    def is_ok(self) -> bool:
        return self is Status.VALID or self is Status.DEVEL


VHASH_DEVEL = bytes.fromhex(
    "c5b4d40cb76911392122c8d1c277937e49c69b2aaf818001ec5c7663fcce258f"
)


def _make_dev_keys(*key_bytes: bytes) -> t.Sequence[bytes]:
    return [k * 32 for k in key_bytes]


def all_zero(data: bytes) -> bool:
    return all(b == 0 for b in data)


def _check_signature_any(fw: "SignableImageProto", is_devel: bool = False) -> Status:
    if not fw.signature_present():
        return Status.MISSING
    try:
        fw.verify()
        return Status.VALID if not is_devel else Status.DEVEL
    except Exception:
        pass

    try:
        fw.verify(dev_keys=True)
        return Status.DEVEL
    except Exception:
        return Status.INVALID


# ====================== formatting functions ====================


class LiteralStr(str):
    pass


def _format_container(
    pb: t.Union[c.Container, Struct, dict],
    indent: int = 0,
    sep: str = " " * 4,
    truncate_after: t.Optional[int] = 64,
    truncate_to: t.Optional[int] = 32,
) -> str:
    def mostly_printable(bytes: bytes) -> bool:
        if not bytes:
            return True
        printable = sum(1 for byte in bytes if 0x20 <= byte <= 0x7E)
        return printable / len(bytes) > 0.8

    def pformat(value: t.Any, indent: int) -> str:
        level = sep * indent
        leadin = sep * (indent + 1)

        if isinstance(value, LiteralStr):
            return value

        if isinstance(value, list):
            # short list of simple values
            if not value or isinstance(value[0], (int, bool, Enum)):
                return repr(value)

            # long list, one line per entry
            lines = ["[", level + "]"]
            lines[1:1] = [leadin + pformat(x, indent + 1) for x in value]
            return "\n".join(lines)

        if isinstance(value, Struct):
            value = asdict(value)

        if isinstance(value, dict):
            lines = ["{"]
            for key, val in value.items():
                if key.startswith("_"):
                    continue
                if val is None or val == []:
                    continue
                lines.append(leadin + key + ": " + pformat(val, indent + 1))
            lines.append(level + "}")
            return "\n".join(lines)

        if isinstance(value, (bytes, bytearray)):
            length = len(value)
            suffix = ""
            if truncate_after and length > truncate_after:
                suffix = "..."
                value = value[: truncate_to or 0]
            if mostly_printable(value):
                output = repr(value)
            else:
                output = value.hex()
            return f"{length} bytes {output}{suffix}"

        if isinstance(value, Enum):
            return str(value)

        return repr(value)

    return pformat(pb, indent)


def _format_version(version: t.Tuple[int, ...]) -> str:
    return ".".join(str(i) for i in version)


def format_header(
    header: firmware.core.FirmwareHeader,
    code_hashes: t.Sequence[bytes],
    digest: bytes,
    sig_status: Status,
) -> str:
    header_dict = asdict(header)
    header_out = header_dict.copy()

    for key, val in header_out.items():
        if "version" in key:
            header_out[key] = LiteralStr(_format_version(val))

    hashes_out = []
    for expected, actual in zip(header.hashes, code_hashes):
        status = SYM_OK if expected == actual else SYM_FAIL
        hashes_out.append(LiteralStr(f"{status} {expected.hex()}"))

    if all(all_zero(h) for h in header.hashes):
        hash_status = Status.MISSING
    elif header.hashes != code_hashes:
        hash_status = Status.INVALID
    else:
        hash_status = Status.VALID

    header_out["hashes"] = hashes_out

    all_ok = SYM_OK if hash_status.is_ok() and sig_status.is_ok() else SYM_FAIL

    output = [
        "Firmware Header " + _format_container(header_out),
        f"Fingerprint: {click.style(digest.hex(), bold=True)}",
        f"{all_ok} Signature is {sig_status.value}, hashes are {hash_status.value}",
    ]

    return "\n".join(output)


# =========================== functionality implementations ===============


class SignableImageProto(Protocol):
    NAME: t.ClassVar[str]

    @classmethod
    def parse(cls, data: bytes) -> Self:
        """Parse binary data into an image of this type."""
        ...

    def digest(self) -> bytes:
        """Calculate digest that will be signed / verified."""
        ...

    def verify(self, dev_keys: bool = False) -> None:
        """Verify signature of the image.

        If dev_keys is True, verify using development keys. If selected, a production
        image will fail verification.
        """
        ...

    def build(self) -> bytes:
        """Reconstruct binary representation of the image."""
        ...

    def format(self, verbose: bool = False) -> str:
        """Generate printable information about the image."""
        ...

    def signature_present(self) -> bool:
        """Check if the image has a signature."""
        ...

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        """Return public keys that should be used to sign the image.

        This does _not_ return the keys with which the image is actually signed.
        In particular, `image.public_keys()` will return the production
        keys even if the image is signed with development keys.

        If dev_keys is True, return development keys.
        """
        ...


@runtime_checkable
class CosiSignedImage(SignableImageProto, Protocol):
    DEV_KEYS: t.ClassVar[t.Sequence[bytes]] = []

    def insert_signature(self, signature: bytes, sigmask: int) -> None:
        ...


@runtime_checkable
class LegacySignedImage(SignableImageProto, Protocol):
    def slots(self) -> t.Iterable[int]:
        ...

    def insert_signature(self, slot: int, key_index: int, signature: bytes) -> None:
        ...

    def public_keys(
        self, dev_keys: bool = False, signature_version: int = 3
    ) -> t.Sequence[bytes]:
        """Return public keys that should be used to sign the image.

        This does _not_ return the keys with which the image is actually signed.
        In particular, `image.public_keys()` will return the production
        keys even if the image is signed with development keys.

        If dev_keys is True, return development keys.

        Specifying signature_version allows to return keys for a different signature
        scheme version. The default is the newest version 3.
        """
        ...


class CosiSignatureHeaderProto(Protocol):
    hw_model: t.Union[fw_models.Model, bytes]
    signature: bytes
    sigmask: int


class CosiSignedMixin:
    def signature_present(self) -> bool:
        header = self.get_header()
        return not all_zero(header.signature) or header.sigmask != 0

    def insert_signature(self, signature: bytes, sigmask: int) -> None:
        self.get_header().signature = signature
        self.get_header().sigmask = sigmask

    def get_header(self) -> CosiSignatureHeaderProto:
        raise NotImplementedError

    def get_model_keys(self, dev_keys: bool) -> fw_models.ModelKeys:
        hw_model = self.get_header().hw_model
        model = fw_models.Model.from_hw_model(hw_model)
        return model.model_keys(dev_keys)


class VendorHeader(firmware.VendorHeader, CosiSignedMixin):
    NAME: t.ClassVar[str] = "vendorheader"
    DEV_KEYS = _make_dev_keys(b"\x44", b"\x45")

    SUBCON = c.Struct(*firmware.VendorHeader.SUBCON.subcons, c.Terminated)

    def get_header(self) -> CosiSignatureHeaderProto:
        return self

    def _format(self, terse: bool) -> str:
        if not terse:
            output = [
                "Vendor Header " + _format_container(self),
                f"Pubkey bundle hash: {self.vhash().hex()}",
            ]
        else:
            output = [
                "Vendor Header for {vendor} version {version} ({size} bytes)".format(
                    vendor=click.style(self.text, bold=True),
                    version=_format_version(self.version),
                    size=self.header_len,
                ),
            ]

        if not terse:
            output.append(f"Fingerprint: {click.style(self.digest().hex(), bold=True)}")

        sig_status = _check_signature_any(self)
        sym = SYM_OK if sig_status.is_ok() else SYM_FAIL
        output.append(f"{sym} Signature is {sig_status.value}")

        return "\n".join(output)

    def format(self, verbose: bool = False) -> str:
        return self._format(terse=False)

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        return self.get_model_keys(dev_keys).bootloader_keys


class VendorFirmware(firmware.VendorFirmware, CosiSignedMixin):
    NAME: t.ClassVar[str] = "firmware"
    DEV_KEYS = _make_dev_keys(b"\x47", b"\x48")

    def get_header(self) -> CosiSignatureHeaderProto:
        return self.firmware.header

    def format(self, verbose: bool = False) -> str:
        vh = copy(self.vendor_header)
        vh.__class__ = VendorHeader
        assert isinstance(vh, VendorHeader)

        is_devel = self.vendor_header.vhash() == VHASH_DEVEL
        return (
            vh._format(terse=not verbose)
            + "\n"
            + format_header(
                self.firmware.header,
                self.firmware.code_hashes(),
                self.digest(),
                _check_signature_any(self, is_devel),
            )
        )

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        """Return public keys that should be used to sign the image.

        In vendor firmware, the public keys are stored in the vendor header.
        There is no choice of development keys. If that is required, you need to create
        an image with a development vendor header.
        """
        return self.vendor_header.pubkeys


class BootloaderImage(firmware.FirmwareImage, CosiSignedMixin):
    NAME: t.ClassVar[str] = "bootloader"
    DEV_KEYS = _make_dev_keys(b"\x41", b"\x42")

    def get_header(self) -> CosiSignatureHeaderProto:
        return self.header

    def format(self, verbose: bool = False) -> str:
        return format_header(
            self.header,
            self.code_hashes(),
            self.digest(),
            _check_signature_any(self),
        )

    def verify(self, dev_keys: bool = False) -> None:
        self.validate_code_hashes()
        public_keys = self.public_keys(dev_keys)
        try:
            cosi.verify(
                self.header.signature,
                self.digest(),
                self.get_model_keys(dev_keys).boardloader_sigs_needed,
                public_keys,
                self.header.sigmask,
            )
        except Exception:
            raise firmware.InvalidSignatureError("Invalid bootloader signature")

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        return self.get_model_keys(dev_keys).boardloader_keys


class LegacyFirmware(firmware.LegacyFirmware):
    NAME: t.ClassVar[str] = "legacy_firmware_v1"

    def signature_present(self) -> bool:
        return any(i != 0 for i in self.key_indexes) or any(
            not all_zero(sig) for sig in self.signatures
        )

    def insert_signature(self, slot: int, key_index: int, signature: bytes) -> None:
        if not 0 <= slot < firmware.V1_SIGNATURE_SLOTS:
            raise ValueError("Invalid slot number")
        if not 0 < key_index <= len(fw_models.LEGACY_V1V2.firmware_keys):
            raise ValueError("Invalid key index")
        self.key_indexes[slot] = key_index
        self.signatures[slot] = signature

    def format(self, verbose: bool = False) -> str:
        contents = asdict(self).copy()
        del contents["embedded_v2"]
        if self.embedded_v2:
            em = copy(self.embedded_v2)
            em.__class__ = LegacyV2Firmware
            assert isinstance(em, LegacyV2Firmware)
            embedded_content = "\nEmbedded V2 header: " + em.format(verbose=verbose)
        else:
            embedded_content = ""

        return _format_container(contents) + embedded_content

    def public_keys(
        self, dev_keys: bool = False, signature_version: int = 2
    ) -> t.Sequence[bytes]:
        if dev_keys:
            return fw_models.LEGACY_V1V2_DEV.firmware_keys
        else:
            return fw_models.LEGACY_V1V2.firmware_keys

    def slots(self) -> t.Iterable[int]:
        return self.key_indexes


class LegacyV2Firmware(firmware.LegacyV2Firmware):
    NAME: t.ClassVar[str] = "legacy_firmware_v2"

    def signature_present(self) -> bool:
        return any(i != 0 for i in self.header.v1_key_indexes) or any(
            not all_zero(sig) for sig in self.header.v1_signatures
        )

    def insert_signature(self, slot: int, key_index: int, signature: bytes) -> None:
        if not 0 <= slot < firmware.V1_SIGNATURE_SLOTS:
            raise ValueError("Invalid slot number")
        if not 0 < key_index <= len(firmware.V1_BOOTLOADER_KEYS):
            raise ValueError("Invalid key index")
        if not isinstance(self.header.v1_key_indexes, list):
            self.header.v1_key_indexes = list(self.header.v1_key_indexes)
        if not isinstance(self.header.v1_signatures, list):
            self.header.v1_signatures = list(self.header.v1_signatures)
        self.header.v1_key_indexes[slot] = key_index
        self.header.v1_signatures[slot] = signature

    def format(self, verbose: bool = False) -> str:
        return format_header(
            self.header,
            self.code_hashes(),
            self.digest(),
            _check_signature_any(self),
        )

    def public_keys(
        self, dev_keys: bool = False, signature_version: int = 3
    ) -> t.Sequence[bytes]:
        keymap: t.Dict[t.Tuple[int, bool], fw_models.ModelKeys] = {
            (3, False): fw_models.LEGACY_V3,
            (3, True): fw_models.LEGACY_V3_DEV,
            (2, False): fw_models.LEGACY_V1V2,
            (2, True): fw_models.LEGACY_V1V2_DEV,
        }
        if not (signature_version, dev_keys) in keymap:
            raise ValueError("Unsupported signature version")
        return keymap[signature_version, dev_keys].firmware_keys

    def slots(self) -> t.Iterable[int]:
        return self.header.v1_key_indexes


def parse_image(image: bytes) -> SignableImageProto:
    try:
        return VendorFirmware.parse(image)
    except c.ConstructError:
        pass

    try:
        return VendorHeader.parse(image)
    except c.ConstructError:
        pass

    try:
        firmware_img = firmware.core.FirmwareImage.parse(image)
        if firmware_img.header.magic == firmware.core.HeaderType.BOOTLOADER:
            return BootloaderImage.parse(image)
        if firmware_img.header.magic == firmware.core.HeaderType.FIRMWARE:
            return LegacyV2Firmware.parse(image)
        raise ValueError("Unrecognized firmware header magic")
    except c.ConstructError:
        pass

    try:
        return LegacyFirmware.parse(image)
    except c.ConstructError:
        pass

    raise ValueError("Unrecognized firmware type")
