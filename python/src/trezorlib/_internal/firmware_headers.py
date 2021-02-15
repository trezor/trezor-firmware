import struct
from enum import Enum
from typing import Any, List, Optional

import click
import construct as c

from .. import cosi, firmware

try:
    from hashlib import blake2s
except ImportError:
    from pyblake2 import blake2s


SYM_OK = click.style("\u2714", fg="green")
SYM_FAIL = click.style("\u274c", fg="red")


class Status(Enum):
    VALID = click.style("VALID", fg="green", bold=True)
    INVALID = click.style("INVALID", fg="red", bold=True)
    MISSING = click.style("MISSING", fg="blue", bold=True)
    DEVEL = click.style("DEVEL", fg="red", bold=True)

    def is_ok(self):
        return self is Status.VALID or self is Status.DEVEL


VHASH_DEVEL = bytes.fromhex(
    "c5b4d40cb76911392122c8d1c277937e49c69b2aaf818001ec5c7663fcce258f"
)


AnyFirmware = c.Struct(
    "vendor_header" / c.Optional(firmware.VendorHeader),
    "image" / c.Optional(firmware.FirmwareImage),
)


class ImageType(Enum):
    VENDOR_HEADER = 0
    BOOTLOADER = 1
    FIRMWARE = 2


def _make_dev_keys(*key_bytes: bytes) -> List[bytes]:
    return [k * 32 for k in key_bytes]


def compute_vhash(vendor_header):
    m = vendor_header.sig_m
    n = vendor_header.sig_n
    pubkeys = vendor_header.pubkeys
    h = blake2s()
    h.update(struct.pack("<BB", m, n))
    for i in range(8):
        if i < n:
            h.update(pubkeys[i])
        else:
            h.update(b"\x00" * 32)
    return h.digest()


def all_zero(data: bytes) -> bool:
    return all(b == 0 for b in data)


def _check_signature_any(
    header: c.Container, m: int, pubkeys: List[bytes], is_devel: bool
) -> Optional[bool]:
    if all_zero(header.signature) and header.sigmask == 0:
        return Status.MISSING
    try:
        digest = firmware.header_digest(header)
        cosi.verify(header.signature, digest, m, pubkeys, header.sigmask)
        return Status.VALID if not is_devel else Status.DEVEL
    except Exception:
        return Status.INVALID


# ====================== formatting functions ====================


class LiteralStr(str):
    pass


def _format_container(
    pb: c.Container,
    indent: int = 0,
    sep: str = " " * 4,
    truncate_after: Optional[int] = 64,
    truncate_to: Optional[int] = 32,
) -> str:
    def mostly_printable(bytes: bytes) -> bool:
        if not bytes:
            return True
        printable = sum(1 for byte in bytes if 0x20 <= byte <= 0x7E)
        return printable / len(bytes) > 0.8

    def pformat(value: Any, indent: int) -> str:
        level = sep * indent
        leadin = sep * (indent + 1)

        if isinstance(value, LiteralStr):
            return value

        if isinstance(value, list):
            # short list of simple values
            if not value or isinstance(value, (int, bool, Enum)):
                return repr(value)

            # long list, one line per entry
            lines = ["[", level + "]"]
            lines[1:1] = [leadin + pformat(x, indent + 1) for x in value]
            return "\n".join(lines)

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
            return "{} bytes {}{}".format(length, output, suffix)

        if isinstance(value, Enum):
            return str(value)

        return repr(value)

    return pformat(pb, indent)


def _format_version(version: c.Container) -> str:
    version_str = ".".join(
        str(version[k]) for k in ("major", "minor", "patch") if k in version
    )
    if "build" in version:
        version_str += " build {}".format(version.build)
    return version_str


# =========================== functionality implementations ===============


class SignableImage:
    NAME = "Unrecognized image"
    BIP32_INDEX = None
    DEV_KEYS = []
    DEV_KEY_SIGMASK = 0b11

    def __init__(self, fw: c.Container) -> None:
        self.fw = fw
        self.header = None
        self.public_keys = None
        self.sigs_required = firmware.V2_SIGS_REQUIRED

    def digest(self) -> bytes:
        return firmware.header_digest(self.header)

    def check_signature(self) -> Status:
        raise NotImplementedError

    def rehash(self) -> None:
        pass

    def insert_signature(self, signature: bytes, sigmask: int) -> None:
        self.header.signature = signature
        self.header.sigmask = sigmask

    def dump(self) -> bytes:
        return AnyFirmware.build(self.fw)

    def format(self, verbose: bool) -> str:
        return _format_container(self.fw)


class VendorHeader(SignableImage):
    NAME = "vendorheader"
    BIP32_INDEX = 1
    DEV_KEYS = _make_dev_keys(b"\x44", b"\x45")

    def __init__(self, fw):
        super().__init__(fw)
        self.header = fw.vendor_header
        self.public_keys = firmware.V2_BOOTLOADER_KEYS

    def check_signature(self) -> Status:
        return _check_signature_any(
            self.header, self.sigs_required, self.public_keys, False
        )

    def _format(self, terse: bool) -> str:
        vh = self.fw.vendor_header
        if not terse:
            vhash = compute_vhash(vh)
            output = [
                "Vendor Header " + _format_container(vh),
                "Pubkey bundle hash: {}".format(vhash.hex()),
            ]
        else:
            output = [
                "Vendor Header for {vendor} version {version} ({size} bytes)".format(
                    vendor=click.style(vh.text, bold=True),
                    version=_format_version(vh.version),
                    size=vh.header_len,
                ),
            ]

        fingerprint = firmware.header_digest(vh)

        if not terse:
            output.append(
                "Fingerprint: {}".format(click.style(fingerprint.hex(), bold=True))
            )

        sig_status = self.check_signature()
        sym = SYM_OK if sig_status.is_ok() else SYM_FAIL
        output.append("{} Signature is {}".format(sym, sig_status.value))

        return "\n".join(output)

    def format(self, verbose: bool = False) -> str:
        return self._format(terse=False)


class BinImage(SignableImage):
    def __init__(self, fw):
        super().__init__(fw)
        self.header = self.fw.image.header
        self.code_hashes = firmware.calculate_code_hashes(
            self.fw.image.code, self.fw.image._code_offset
        )
        self.digest_header = self.header.copy()
        self.digest_header.hashes = self.code_hashes

    def insert_signature(self, signature: bytes, sigmask: int) -> None:
        super().insert_signature(signature, sigmask)
        self.digest_header.signature = signature
        self.digest_header.sigmask = sigmask

    def digest(self) -> bytes:
        return firmware.header_digest(self.digest_header)

    def rehash(self):
        self.header.hashes = self.code_hashes

    def format(self, verbose: bool = False) -> str:
        header_out = self.header.copy()

        if not verbose:
            for key in self.header:
                if key.startswith("v1"):
                    del header_out[key]
                if "version" in key:
                    header_out[key] = LiteralStr(_format_version(self.header[key]))

        all_ok = SYM_OK
        hash_status = Status.VALID
        sig_status = Status.VALID

        hashes_out = []
        for expected, actual in zip(self.header.hashes, self.code_hashes):
            status = SYM_OK if expected == actual else SYM_FAIL
            hashes_out.append(LiteralStr("{} {}".format(status, expected.hex())))

        if all(all_zero(h) for h in self.header.hashes):
            hash_status = Status.MISSING
        elif self.header.hashes != self.code_hashes:
            hash_status = Status.INVALID
        else:
            hash_status = Status.VALID

        header_out["hashes"] = hashes_out

        sig_status = self.check_signature()
        all_ok = SYM_OK if hash_status.is_ok() and sig_status.is_ok() else SYM_FAIL

        output = [
            "Firmware Header " + _format_container(header_out),
            "Fingerprint: {}".format(click.style(self.digest().hex(), bold=True)),
            "{} Signature is {}, hashes are {}".format(
                all_ok, sig_status.value, hash_status.value
            ),
        ]

        return "\n".join(output)


class FirmwareImage(BinImage):
    NAME = "firmware"
    BIP32_INDEX = 2
    DEV_KEYS = _make_dev_keys(b"\x47", b"\x48")

    def __init__(self, fw: c.Container) -> None:
        super().__init__(fw)
        self.public_keys = fw.vendor_header.pubkeys
        self.sigs_required = fw.vendor_header.sig_m

    def check_signature(self) -> Status:
        vhash = compute_vhash(self.fw.vendor_header)
        return _check_signature_any(
            self.digest_header,
            self.sigs_required,
            self.public_keys,
            vhash == VHASH_DEVEL,
        )

    def format(self, verbose: bool = False) -> str:
        return (
            VendorHeader(self.fw)._format(terse=not verbose)
            + "\n"
            + super().format(verbose)
        )


class BootloaderImage(BinImage):
    NAME = "bootloader"
    BIP32_INDEX = 0
    DEV_KEYS = _make_dev_keys(b"\x41", b"\x42")

    def __init__(self, fw):
        super().__init__(fw)
        self._identify_dev_keys()

    def insert_signature(self, signature: bytes, sigmask: int) -> None:
        super().insert_signature(signature, sigmask)
        self._identify_dev_keys()

    def _identify_dev_keys(self):
        # try checking signature with dev keys first
        self.public_keys = firmware.V2_BOARDLOADER_DEV_KEYS
        if not self.check_signature().is_ok():
            # validation with dev keys failed, use production keys
            self.public_keys = firmware.V2_BOARDLOADER_KEYS

    def check_signature(self) -> Status:
        return _check_signature_any(
            self.header,
            self.sigs_required,
            self.public_keys,
            self.public_keys == firmware.V2_BOARDLOADER_DEV_KEYS,
        )


def parse_image(image: bytes):
    fw = AnyFirmware.parse(image)
    if fw.vendor_header and not fw.image:
        return VendorHeader(fw)
    if (
        not fw.vendor_header
        and fw.image
        and fw.image.header.magic == firmware.HeaderType.BOOTLOADER
    ):
        return BootloaderImage(fw)
    if (
        fw.vendor_header
        and fw.image
        and fw.image.header.magic == firmware.HeaderType.FIRMWARE
    ):
        return FirmwareImage(fw)
    raise ValueError("Unrecognized image type")
