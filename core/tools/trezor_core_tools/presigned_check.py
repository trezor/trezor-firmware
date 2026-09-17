#!/usr/bin/env python3
"""Prove a presigned release set (bootloader, bundle, secmon pair, nRF) still agrees.

Per model and key set: signature verifies, bundle roots match the header, the
custom leaf recomputed from the committed secmon folds to firmware_root, the nRF
hashes to the recorded image_hash. Not-yet-promoted sets are skipped, not failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from trezorlib.firmware import pq_secure
from trezorlib.firmware.core import BootableImage
from trezorlib.merkle_tree import evaluate_proof

from . import firmware_module, nrf_tree
from .common import MODELS_DIR

# Per key set: committed-artifact suffix, dev keys?, secmon pair (named `_DEV`).
KEY_SETS: dict[str, dict[str, Any]] = {
    "production": {
        "suffix": "",
        "dev_keys": False,
        "secmon": ("secmon.bin", "secmon_api.o"),
    },
    "devel": {
        "suffix": "_devel",
        "dev_keys": True,
        "secmon": ("secmon_DEV.bin", "secmon_api_DEV.o"),
    },
}


class Mismatch(Exception):
    """A committed set disagrees with itself."""


def uses_pq_secure_boot(model_dir: Path) -> bool:
    """Whether model.toml lists pq_secure_boot (line-scanned, no TOML dependency)."""
    model_toml = model_dir / "model.toml"
    if not model_toml.is_file():
        return False
    for raw in model_toml.read_text().splitlines():
        line = raw.split("#", 1)[0].strip().rstrip(",").strip()
        if line == '"pq_secure_boot"':
            return True
    return False


def tree_models() -> list[str]:
    return sorted(
        d.name for d in MODELS_DIR.iterdir() if d.is_dir() and uses_pq_secure_boot(d)
    )


def _hex(value: bytes | str) -> str:
    return value.hex() if isinstance(value, bytes) else value


def _short(value: bytes | str) -> str:
    return _hex(value)[:16] + "…"


def load_bundle(path: Path) -> dict[str, dict[str, Any]]:
    """Read a bundle as a model -> body map; an unreadable container is a Mismatch."""
    raw = json.loads(path.read_text())
    try:
        return firmware_module.container_models(raw, path)
    except SystemExit as e:
        raise Mismatch(str(e)) from e


def _custom_entry(body: dict[str, Any], model: str) -> dict[str, Any]:
    entry = next(
        (
            v
            for v in body["variants"]
            if v.get("firmware_type") == pq_secure.FirmwareVariant.CUSTOM
        ),
        None,
    )
    if entry is None:
        raise Mismatch(
            f"{model} has no CUSTOM variant, so nothing presigned can be built from it"
        )
    return entry


def _custom_manifest(entry: dict[str, Any]) -> bytes | None:
    """The custom variant's authenticity manifest, if recorded (needed to
    recompute the leaf and so bind the secmon)."""
    raw = entry.get("authenticity_manifest")
    return bytes.fromhex(raw) if raw else None


def detect_key_set(bootloader: Path) -> str | None:
    """Which key set signed this bootloader (read off the signature), or None."""
    if not bootloader.is_file():
        return None
    try:
        boot = BootableImage.parse(bootloader.read_bytes())
    except Exception:
        return None
    for name, spec in KEY_SETS.items():
        try:
            boot.verify(dev_keys=spec["dev_keys"])
            return name
        except Exception:
            continue
    return None


def check_model(
    model: str,
    body: dict[str, Any],
    key_set: str,
    bl_path: Path,
    nrf_dir: Path,
) -> list[str]:
    """Check one model's entry against its bootloader, secmon and nRF image."""
    spec = KEY_SETS[key_set]
    model_dir = MODELS_DIR / model
    out: list[str] = []

    if not bl_path.is_file():
        raise Mismatch(
            f"the bundle has an entry for {model} but {bl_path.name} is absent"
        )

    boot = BootableImage.parse(bl_path.read_bytes())

    # 1. the signature must verify against THIS key set, not merely one of them.
    try:
        boot.verify(dev_keys=spec["dev_keys"])
    except Exception as e:
        raise Mismatch(
            f"{bl_path.name} does not verify with the {key_set} keys: {e}"
        ) from e
    out.append(f"    bootloader     {bl_path.name}: signature OK ({key_set} keys)")

    # 2 + 3. the entry must describe THIS bootloader.
    fw_root = boot.header.firmware_root
    if fw_root == bytes(32):
        raise Mismatch(
            f"{bl_path.name} carries firmware_root = 0 -- it is a BARE bootloader "
            "(the input to `xtask release`), not the release-signed one a presigned "
            "set must reference"
        )
    if _hex(fw_root) != body["firmware_root"]:
        raise Mismatch(
            f"firmware_root disagrees: bootloader {_short(fw_root)} vs "
            f"bundle {_short(body['firmware_root'])}"
        )
    out.append(f"    firmware_root  {_short(fw_root)} agrees")

    model_root = boot.merkle_root()
    if _hex(model_root) != body["bootloader"]["signed_root"]:
        raise Mismatch(
            f"modelRoot disagrees: bootloader signs {_short(model_root)} vs "
            f"bundle {_short(body['bootloader']['signed_root'])}"
        )
    out.append(
        f"    modelRoot      {_short(model_root)} agrees (what the signature covers)"
    )

    # 4. the secmon binding, via the custom leaf.
    custom = _custom_entry(body, model)
    manifest = _custom_manifest(custom)
    secmon_bin, secmon_api = (model_dir / "secmon" / n for n in spec["secmon"])

    if manifest is None:
        out.append(
            "    SKIP  secmon binding: no `authenticity_manifest` for the custom "
            "variant, so its leaf cannot be recomputed"
        )
    elif not secmon_bin.is_file():
        out.append(f"    SKIP  secmon binding: {secmon_bin.name} is not committed")
    else:
        if not secmon_api.is_file():
            raise Mismatch(
                f"{secmon_bin.name} is committed but {secmon_api.name} is not -- "
                "the kernel links that veneer and secure-faults if the two drift, "
                "so they travel together"
            )
        parsed = pq_secure.PqSecureManifest.parse(manifest)
        entries = [
            e for e in parsed.entries if e.module_type == pq_secure.ModuleType.SECMON
        ]
        if not entries:
            raise Mismatch(f"{model}'s custom manifest has no SECMON entry")
        secmon_entry = entries[0]
        code = secmon_bin.read_bytes()
        actual = pq_secure.module_code_hash(code, secmon_entry.chunk_size)
        if len(code) != secmon_entry.size or actual != secmon_entry.code_hash:
            raise Mismatch(
                f"the committed {secmon_bin.name} is not the one this set was "
                f"signed over: manifest says size={secmon_entry.size} "
                f"hash={_short(secmon_entry.code_hash)}, committed binary is "
                f"size={len(code)} hash={_short(actual)}"
            )
        out.append(
            f"    secmon         {secmon_bin.name} matches the signed custom leaf"
        )

        leaf = pq_secure.variant_leaf(manifest)
        if _hex(leaf) != custom["leaf"]:
            raise Mismatch(
                f"the custom leaf recomputed from the manifest is {_short(leaf)}, "
                f"but the bundle records {_short(custom['leaf'])}"
            )
        folded = evaluate_proof(
            pq_secure.authenticity_bytes(manifest),
            [bytes.fromhex(n) for n in custom["proof"]],
        )
        if folded != fw_root:
            raise Mismatch(
                f"the custom co-path folds to {_short(folded)}, not the signed "
                f"firmware_root {_short(fw_root)}"
            )
        out.append(
            f"    custom co-path folds to firmware_root ({len(custom['proof'])} nodes)"
        )

    # 5. the nRF image, under the same signed modelRoot.
    nrf = firmware_module.container_coprocessor(body, "nrf", 0)
    if not nrf:
        out.append("    SKIP  nRF: no nRF co-processor entry for this model")
        return out
    if _hex(model_root) != nrf["model_root"]:
        raise Mismatch(
            f"the nRF entry names modelRoot {_short(nrf['model_root'])}, but the "
            f"bootloader signs {_short(model_root)}"
        )
    if nrf.get("image_model_id") not in (None, model):
        raise Mismatch(
            f"the nRF entry under {model} names image_model_id {nrf['image_model_id']}"
        )
    nrf_path = nrf_dir / nrf["file"]
    if not nrf_path.is_file():
        out.append(f"    SKIP  nRF: {nrf['file']} not found beside the set")
        return out
    # image_hash describes the SIGNED file (PQ-native signing rewrites the image).
    recorded = nrf.get("image_hash")
    if recorded is None:
        out.append(
            f"    SKIP  nRF: {nrf['file']} present, but the entry records no "
            "image_hash to check it against"
        )
        return out
    # Recomputed over the protected region, not read back from TLV 0x10.
    try:
        actual = nrf_tree.mcuboot_image_hash(nrf_path.read_bytes())
    except ValueError as e:
        raise Mismatch(f"{nrf['file']} is not a usable MCUboot image: {e}") from e
    if _hex(actual) != _hex(recorded):
        raise Mismatch(
            f"{nrf['file']} hashes to {_short(actual)} but the entry records "
            f"{_short(recorded)} -- the committed image is not the one that was "
            f"signed (re-promote, or re-cut the release)"
        )
    out.append(f"    nRF            {nrf['file']} matches the signed image")
    return out


def run(key_set: str, release_dir: Path | None, only: str | None) -> tuple[bool, bool]:
    """Check one key set. Returns (failed, anything_checked)."""
    if release_dir is not None:
        bundle_path = release_dir / "bundle.json"
    else:
        bundle_path = MODELS_DIR / f"bundle{KEY_SETS[key_set]['suffix']}.json"

    if not bundle_path.is_file():
        print(f"  SKIP  not promoted yet ({bundle_path} absent)")
        return False, False

    failed = False
    try:
        models = load_bundle(bundle_path)
    except Mismatch as e:
        print(f"  FAIL  {e}")
        return True, True

    expected = tree_models()
    # A partial promotion is expressible; check both directions.
    if only is None:
        for missing in sorted(set(expected) - set(models)):
            print(
                f"  FAIL  {missing} uses pq_secure_boot but has no entry "
                f"in {bundle_path.name}"
            )
            failed = True
    for extra in sorted(set(models) - set(expected)):
        print(
            f"  FAIL  {bundle_path.name} has an entry for {extra}, which does "
            "not use pq_secure_boot"
        )
        failed = True

    for model in sorted(models):
        if only is not None and model != only:
            continue
        if model not in expected:
            continue
        print(f"  {model}")
        if release_dir is not None:
            bl_path = release_dir / models[model]["bootloader"]["file"]
            nrf_dir = release_dir
        else:
            suffix = KEY_SETS[key_set]["suffix"]
            # Promotion replaces the committed bootloader in place.
            bl_path = (
                MODELS_DIR / model / "bootloaders" / f"bootloader_{model}{suffix}.bin"
            )
            nrf_dir = MODELS_DIR / model
        try:
            for line in check_model(model, models[model], key_set, bl_path, nrf_dir):
                print(line)
        except Mismatch as e:
            print(f"    FAIL  {e}")
            failed = True
        except Exception as e:  # a malformed set is a failure, not a crash
            print(f"    FAIL  {type(e).__name__}: {e}")
            failed = True
    return failed, True


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument(
        "-m",
        "--model",
        help="check only this model (default: every model in the bundle)",
    )
    ap.add_argument(
        "--from-release",
        type=Path,
        metavar="DIR",
        help="check a freshly cut release directory (build-xtask/tree/<MODEL>) "
        "instead of the committed set -- use before promoting",
    )
    args = ap.parse_args()

    if args.model and args.model not in tree_models():
        print(f"{args.model} does not use pq_secure_boot, so it has no presigned set")
        return 1
    if not tree_models():
        print("no model uses pq_secure_boot; nothing to check")
        return 0

    if args.from_release is not None:
        # No container read yet, so use the writer's name.
        bl_name = firmware_module.CONTAINER_DEFAULT_BOOTLOADER
        detected = detect_key_set(args.from_release / bl_name)
        if detected is None:
            print(f"{args.from_release}/{bl_name} verifies with neither key set")
            return 1
        key_sets = [detected]
    else:
        key_sets = list(KEY_SETS)

    failed = False
    for key_set in key_sets:
        print(f"[{key_set}]")
        f, _ = run(key_set, args.from_release, args.model)
        failed = failed or f
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
