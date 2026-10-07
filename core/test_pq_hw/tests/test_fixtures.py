"""The fixture set is what the hardware tests assume it is. Runs on the host."""

from __future__ import annotations

import struct

import pytest
from pqhw.cutpoint import CutPoint
from pqhw.fixtures import VARIANTS, Fixtures

from trezorlib import firmware
from trezorlib.firmware.core import BootableImage

pytestmark = pytest.mark.offline

RELEASES = (
    "release-A",
    "release-B",
    "release-B-fix",
    "release-C-minprev",
    "release-E-mono",
)
ALL_VARIANTS = ("universal", "btc-only", "custom", "prodtest")
FW_VARIANT_SEC = {"universal": 0x5A5A5A5A, "btc-only": 0xA5A5A5A5}
VENDOR_FW_TYPE = {"universal": 2, "btc-only": 3}


def legacy_version(fx: Fixtures, path) -> tuple[int, ...]:
    return tuple(firmware.parse(path.read_bytes()).firmware.header.version)


def pq_firmware_version(fx: Fixtures, release: str) -> tuple[int, ...]:
    data = fx.release_file(release, "universal.bin").read_bytes()
    return tuple(data[8:12])


def nrf_version(fx: Fixtures, release: str) -> tuple[int, ...]:
    meta = fx.release_meta(release)["coprocessors"][0]
    image = fx.release_file(release, meta["file"]).read_bytes()
    return struct.unpack_from("<BBH", image, 20)


@pytest.mark.parametrize("variant", ALL_VARIANTS)
@pytest.mark.parametrize("release", RELEASES)
def test_release_variant_verifies(fx: Fixtures, release: str, variant: str) -> None:
    fx.bundle(release, variant).verify(dev_keys=True)


@pytest.mark.parametrize("variant", VARIANTS)
def test_legacy_salts_as_its_variant(fx: Fixtures, variant: str) -> None:
    """A devel build would otherwise carry the universal dev vendor header."""
    for path in (fx.legacy(variant), fx.intermediary(variant)):
        fw = firmware.parse(path.read_bytes())
        assert fw.vendor_header.fw_type == VENDOR_FW_TYPE[variant], path.name


@pytest.mark.parametrize("variant", VARIANTS)
def test_intermediary_embeds_release_a(fx: Fixtures, variant: str) -> None:
    """Release A's exact bootloader, stamped with the variant's codeword: its
    header commits to A's firmware_root, which is what MG-04 installs."""
    meta = fx.release_meta("release-A")
    ft = meta["bootloader"]["firmware_type"]
    stamped = bytearray(fx.release_bootloader("release-A").read_bytes())
    off = ft["offset"]
    assert int.from_bytes(stamped[off : off + ft["len"]], "little") == ft["bare"]
    stamped[off : off + ft["len"]] = FW_VARIANT_SEC[variant].to_bytes(
        ft["len"], "little"
    )
    image = fx.intermediary(variant).read_bytes()
    assert bytes(stamped) in image
    nrf = fx.release_file("release-A", meta["coprocessors"][0]["file"]).read_bytes()
    assert nrf in image


def test_versions_climb_in_install_order(fx: Fixtures) -> None:
    legacy = legacy_version(fx, fx.legacy("universal"))
    inter = legacy_version(fx, fx.intermediary("universal"))
    a = pq_firmware_version(fx, "release-A")
    b = pq_firmware_version(fx, "release-B")
    assert legacy < inter < a < b

    bl = {r: fx.bundle(r, "universal").bootloader.header for r in RELEASES}
    # firmware.parse() does not dispatch on TRZQ (backlog R16)
    legacy_bl = BootableImage.parse(fx.legacy("bootloader").read_bytes()).header
    assert tuple(legacy_bl.version) < tuple(bl["release-A"].version)
    assert tuple(bl["release-A"].version) < tuple(bl["release-B"].version)
    assert legacy_bl.monotonic == 2
    assert bl["release-A"].monotonic == bl["release-B"].monotonic == 3


def test_floor_releases(fx: Fixtures) -> None:
    b = fx.bundle("release-B", "universal").bootloader.header
    fix = fx.bundle("release-B-fix", "universal").bootloader.header
    minprev = fx.bundle("release-C-minprev", "universal").bootloader.header
    mono = fx.bundle("release-E-mono", "universal").bootloader.header
    assert tuple(fix.fix_version) == tuple(b.version)
    assert tuple(minprev.min_prev_version) == tuple(b.version)
    assert mono.monotonic == b.monotonic + 1


def test_nrf_differs_between_a_and_b(fx: Fixtures) -> None:
    a = fx.release_meta("release-A")["coprocessors"][0]
    b = fx.release_meta("release-B")["coprocessors"][0]
    assert a["image_hash"] != b["image_hash"]
    assert nrf_version(fx, "release-A") < nrf_version(fx, "release-B")


# The cut points the power-loss tests break at; they must resolve in the ELFs
# staged with each image (the builder checked the ELFs match the images).
CUT_POINTS = {
    "bootloader": [
        "ucb_stage_verify",
        "nrf_staging_write_desc",
        "ucb_stage_arm",
        "nrf_update_with_progress",
        "nrf_staging_clear",
        "boot_ucb_write",
    ],
    "kernel": ["nrf_update"],
    "secmon": ["boot_image_replace", "boot_ucb_write"],
}


@pytest.mark.parametrize("release", RELEASES)
def test_release_cut_points_resolve(fx: Fixtures, release: str) -> None:
    for symbol in CUT_POINTS["bootloader"]:
        CutPoint(fx.release_elf(release), symbol).address


@pytest.mark.parametrize("variant", VARIANTS)
def test_intermediary_cut_points_resolve(fx: Fixtures, variant: str) -> None:
    for part in ("kernel", "secmon"):
        for symbol in CUT_POINTS[part]:
            CutPoint(fx.intermediary_elf(variant, part), symbol).address
