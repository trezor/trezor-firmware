#!/usr/bin/env python3
"""
Based on simplified gen-fw-release-jsons.py from trezor-suite-firmware-release repo.
Consider merging the scripts before extending this one.

Expects that the binaries have the correct names and are placed in the correct directories,
including translation blobs.
"""

import datetime
import json
import re
from collections import defaultdict
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Dict, Sequence

import click

from trezorlib import firmware

# Update these versions as needed
BOOTLOADER_VERSION = {
    "T3W1": (2, 1, 17),
    "T3T1": (2, 1, 16),
    "T3B1": (2, 1, 16),
    "T2T1": (2, 1, 16),
    "T2B1": (2, 1, 16),
    "T1B1": (1, 12, 1),
}

BOOTLOADER_MIN_VERSION = {
    "T3W1": (2, 1, 13),
    "T3T1": (2, 1, 6),
    "T3B1": (2, 1, 7),
    "T2T1": (2, 0, 0),
    "T2B1": (2, 1, 1),
    "T1B1": (1, 12, 0),
}

FIRMWARE_MIN_VERSION = {
    "T3W1": (2, 9, 3),
    "T3T1": (2, 7, 2),
    "T3B1": (2, 8, 3),
    "T2T1": (2, 0, 8),
    "T2B1": (2, 6, 1),
    "T1B1": (1, 12, 0),
}

MODELS = list(FIRMWARE_MIN_VERSION.keys())
CHANGELOG = "* Nightly trezor-firmware git snapshot."
MIN_SUITE_VERSION = "25.9.0"
URL_PREFIX = "dev/firmware/firmware-nightly"


class DeployType(StrEnum):
    NIGHTLY = "nightly"
    UNKNOWN = auto()


def splitversion(version: str) -> list[int]:
    return [int(x) for x in version.split(".")]


def joinversion(version: list[int]) -> str:
    return ".".join(str(x) for x in version)


def json_write(data: dict, path: Path) -> None:
    """Write JSON with proper formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(json_str)


def parse_firmware_filename(filename: str) -> dict | None:
    """Parse firmware filename to extract metadata.
    Pattern: firmware-T2T1-2.9.0-5e4c97f.bin or firmware-T2T1-2.9.0-a09e6f0-signed.bin
    or firmware-T3B1-btconly-2.9.0-5e4c97f.bin
    """
    pattern = r"firmware-([A-Z0-9]+)(?:-(?:btconly|bitcoinonly))?-(\d+\.\d+\.\d+)-([a-f0-9]+)(?:-signed)?\.bin"
    if not (match := re.match(pattern, filename)):
        return None

    model, version, revision = match.groups()
    return {
        "model": model,
        "version": splitversion(version),
        "revision": revision,
        "variant": (
            "bitcoinonly"
            if ("-btconly-" in filename or "-bitcoinonly-" in filename)
            else "universal"
        ),
        "is_signed": filename.endswith("-signed.bin"),
    }


def parse_translation_filename(filename: str) -> dict | None:
    """Parse translation filename to extract metadata.
    Pattern: translation-T2T1-cs-CZ-2.9.0-unsigned.bin or translation-T2T1-cs-CZ-2.9.0.bin
    """
    pattern = r"translation-([A-Z0-9]+)-([a-z]{2})-([A-Z]{2})-(\d+\.\d+\.\d+)(-unsigned)?\.bin"
    if not (match := re.match(pattern, filename)):
        return None

    model, lang, country, version, sign_type = match.groups()
    return {
        "model": model,
        "language": f"{lang}-{country}",
        "version": splitversion(version),
        "is_signed": sign_type != "-unsigned",
    }


def collect_firmware_files(
    root: Path, version: list[int], deploy_type: DeployType
) -> dict:
    """Collect all firmware files for the given version."""
    firmware_files: Dict[str, Any] = defaultdict(
        lambda: {
            DeployType.NIGHTLY: {},
            "translations": {
                DeployType.NIGHTLY: {},
            },
        }
    )

    # Scan firmware files
    firmware_dir = root
    for model_dir in firmware_dir.iterdir():
        if not model_dir.is_dir() or model_dir.name == "translations":
            continue

        model = model_dir.name.upper()
        if model not in MODELS:
            continue

        for fw_file in model_dir.glob("*.bin"):
            fw_info = parse_firmware_filename(fw_file.name)
            if fw_info and fw_info["version"] == version:
                firmware_files[model][deploy_type][fw_info["variant"]] = fw_file

    # Scan translations
    translations_dir = root / "translations"
    if translations_dir.exists():
        for model_dir in translations_dir.iterdir():
            if not model_dir.is_dir():
                continue

            model = model_dir.name.upper()
            if model not in MODELS:
                continue

            for tr_file in model_dir.glob("*.bin"):
                tr_info = parse_translation_filename(tr_file.name)
                if tr_info and tr_info["version"] == version:
                    firmware_files[model]["translations"][deploy_type][
                        tr_info["language"]
                    ] = tr_file

    return dict(firmware_files)


def get_url_path(root: Path, filepath: Path) -> str:
    return f"{URL_PREFIX}/{filepath.relative_to(root)}"


def generate_release_json(
    root: Path,
    model: str,  # e.g. T2T1, T3B1
    version: list[int],
    firmware_files: dict,
    variant: str,  # universal or bitcoinonly
    changelog: str,
    bld_version: list[int],
    revision: str,
    deploy_type: DeployType,
) -> dict:
    """Generate release JSON for a specific model and variant."""

    fw_file = firmware_files[model][deploy_type][variant]
    fingerprint = firmware.parse(fw_file.read_bytes()).digest().hex()

    translations = {
        lang: get_url_path(root, tr_file)
        for lang, tr_file in firmware_files[model]["translations"][deploy_type].items()
    }

    result = {
        "required": False,
        "version": version,
        "min_bootloader_version": BOOTLOADER_MIN_VERSION[model],
        "min_firmware_version": FIRMWARE_MIN_VERSION[model],
        "bootloader_version": bld_version,
        "firmware_revision": revision,
        "url": get_url_path(root, fw_file),
        "fingerprint": fingerprint,
        "changelog": changelog,
    }
    # Avoid adding an empty "translations" entry to legacy JSONs
    if translations:
        result["translations"] = dict(sorted(translations.items()))

    return result


def get_output_path(root: Path, model: str, version: list[int], variant: str) -> Path:
    version_str = joinversion(version)
    model_lower = model.lower()
    base_dir = root / model_lower / variant
    filename = f"{model_lower}-{version_str}-{variant}.json"

    return base_dir / filename


def generate_index(root: Path, models: Sequence[str], version: list[int]) -> Path:
    """Write releases.v1.json index file."""
    version_str = joinversion(version)
    now = datetime.datetime.now(datetime.UTC)
    now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    now = now[:-3] + "Z"
    result = {
        "version": 1,
        "timestamp": now,
        "sequence": 21000000,
        "releases": {},
        "intermediaries": {},
    }
    for model in models:
        model_json = {}
        model_lower = model.lower()
        for variant in ["universal", "bitcoin-only"]:
            variant_dir = variant.replace("-", "")
            model_json[variant] = {
                "firmware_type": variant,
                "conditions": {
                    "environment": {
                        "min_suite_version": MIN_SUITE_VERSION,
                        "min_suite_native_version": MIN_SUITE_VERSION,
                    },
                    "rollout_probability": 100,
                },
                "releasePath": f"{URL_PREFIX}/{model_lower}/{variant_dir}/{model_lower}-{version_str}-{variant_dir}.json",
            }
        result["releases"][model.upper()] = model_json

    output_file = root / "releases.v1.json"
    json_write(result, output_file)
    return output_file


@click.command()
@click.argument("version", type=splitversion)
@click.option(
    "-r", "--root", type=Path, default=".", help="Root directory of firmware releases"
)
@click.option("--revision", help="Git revision")
def generate_releases(
    version: list[int],
    root: Path,
    revision: str | None,
) -> None:
    """Generate individual release JSON files for each firmware version."""

    version_str = joinversion(version)

    if revision is None:
        raise click.ClickException("Missing --revision.")

    deploy_type = DeployType.NIGHTLY
    firmware_files = collect_firmware_files(root, version, deploy_type)

    if not firmware_files:
        click.echo(f"No firmware files found for version {version_str}")
        return

    for model in firmware_files:
        click.echo(f"Processing {model}...")
        changelog_universal = CHANGELOG
        changelog_bitcoinonly = CHANGELOG

        bld_version = list(BOOTLOADER_VERSION[model])
        for variant, changelog_text in zip(
            ["universal", "bitcoinonly"], [changelog_universal, changelog_bitcoinonly]
        ):
            if variant not in firmware_files[model][deploy_type]:
                continue
            json_data = generate_release_json(
                root,
                model,
                version,
                firmware_files,
                variant,
                changelog_text,
                bld_version,
                revision,
                deploy_type,
            )
            output_file = get_output_path(root, model, version, variant)
            json_write(json_data, output_file)
            click.echo(f"Generated {output_file}")

    index_fname = generate_index(root, sorted(firmware_files.keys()), version)
    click.echo(f"Generated index {index_fname}")


if __name__ == "__main__":
    generate_releases()
