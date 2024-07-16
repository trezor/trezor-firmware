from pathlib import Path

import construct
import pytest
import requests

from trezorlib import firmware
from trezorlib.firmware import (
    LegacyFirmware,
    LegacyV2Firmware,
    VendorFirmware,
    VendorHeader,
)

CORE_FW_VERSION = "2.4.2"
CORE_FW_FINGERPRINT = "54ccf155510b5292bd17ed748409d0d135112e24e62eb74184639460beecb213"
LEGACY_FW_VERSION = "1.10.3"
LEGACY_FW_FINGERPRINT = (
    "bf0cc936a9afbf0a4ae7b727a2817fb69fba432d7230a0ff7b79b4a73b845197"
)

CORE_FW = f"https://data.trezor.io/firmware/2/trezor-{CORE_FW_VERSION}.bin"
LEGACY_FW = f"https://data.trezor.io/firmware/1/trezor-{LEGACY_FW_VERSION}.bin"

HERE = Path(__file__).parent

VENDOR_HEADER = (
    HERE.parent.parent
    / "core"
    / "embed"
    / "models"
    / "T2T1"
    / "vendorheader"
    / "vendorheader_satoshilabs_signed_prod.bin"
)


def _fetch(url: str, version: str) -> bytes:
    path = HERE / f"trezor-{version}.bin"
    if not path.exists():
        r = requests.get(url)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path.read_bytes()


@pytest.fixture()
def legacy_fw() -> bytes:
    return _fetch(LEGACY_FW, LEGACY_FW_VERSION)


@pytest.fixture()
def core_fw() -> bytes:
    return _fetch(CORE_FW, CORE_FW_VERSION)


def test_core_basic(core_fw: bytes) -> None:
    fw = VendorFirmware.parse(core_fw)
    fw.verify()
    assert fw.digest().hex() == CORE_FW_FINGERPRINT
    version_str = ".".join(str(x) for x in fw.firmware.header.version)
    assert version_str.startswith(CORE_FW_VERSION)
    assert fw.vendor_header.text == "SatoshiLabs"
    assert fw.build() == core_fw


def test_vendor_header(core_fw: bytes) -> None:
    fw = VendorFirmware.parse(core_fw)

    vh_data = fw.vendor_header.build()
    assert vh_data in core_fw
    assert vh_data == VENDOR_HEADER.read_bytes()

    vh = VendorHeader.parse(vh_data)
    assert vh == fw.vendor_header
    vh.verify()

    with pytest.raises(construct.ConstructError):
        VendorFirmware.parse(vh_data)


def test_core_code_hashes(core_fw: bytes) -> None:
    fw = VendorFirmware.parse(core_fw)
    fw.firmware.header.hashes = []
    assert fw.digest().hex() == CORE_FW_FINGERPRINT


def test_legacy_basic(legacy_fw: bytes) -> None:
    fw = LegacyFirmware.parse(legacy_fw)
    fw.verify()
    assert fw.digest().hex() == LEGACY_FW_FINGERPRINT
    assert fw.build() == legacy_fw


def test_unsigned(legacy_fw: bytes) -> None:
    legacy = LegacyFirmware.parse(legacy_fw)

    legacy.verify()
    legacy.key_indexes = [0, 0, 0]
    legacy.signatures = [b"", b"", b""]

    with pytest.raises(firmware.Unsigned):
        legacy.verify()

    assert legacy.embedded_v2 is not None
    legacy.embedded_v2.verify()

    legacy.embedded_v2.header.v1_key_indexes = [0, 0, 0]
    legacy.embedded_v2.header.v1_signatures = [b"", b"", b""]
    with pytest.raises(firmware.Unsigned):
        legacy.embedded_v2.verify()


def test_disallow_unsigned(core_fw: bytes) -> None:
    core = VendorFirmware.parse(core_fw)
    core.firmware.header.sigmask = 0
    core.firmware.header.signature = b""
    with pytest.raises(firmware.InvalidSignatureError):
        core.verify()


def test_embedded_v2(legacy_fw: bytes) -> None:
    legacy = LegacyFirmware.parse(legacy_fw)
    assert legacy.embedded_v2 is not None
    legacy.embedded_v2.verify()

    embedded_data = legacy.embedded_v2.build()
    cutoff_data = legacy_fw[256:]
    assert cutoff_data == embedded_data
    embedded = LegacyV2Firmware.parse(cutoff_data)
    assert embedded == legacy.embedded_v2


def test_integrity_legacy(legacy_fw: bytes) -> None:
    legacy = LegacyFirmware.parse(legacy_fw)
    legacy.verify()

    modified_data = bytearray(legacy_fw)
    modified_data[-1] ^= 0x01
    modified = LegacyFirmware.parse(modified_data)
    assert modified.digest() != legacy.digest()
    with pytest.raises(firmware.InvalidSignatureError):
        modified.verify()


def test_integrity_core(core_fw: bytes) -> None:
    core = VendorFirmware.parse(core_fw)
    core.verify()

    modified_data = bytearray(core_fw)
    modified_data[-1] ^= 0x01
    modified = VendorFirmware.parse(modified_data)
    assert modified.digest() != core.digest()
    with pytest.raises(firmware.FirmwareIntegrityError):
        modified.verify()
