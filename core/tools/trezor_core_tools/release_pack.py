#!/usr/bin/env python3
"""Pack bundles into archives: one model's bundle, or a whole release.

bundle archive = bundle.json + the files it names.
release archive (release[-devel].zip) = release.json (TRZL-set index) + one
self-contained <MODEL>/ bundle per model, each with its own bundle.json.
Members come from what the manifests name, never from globbing. Unsigned by
design; see docs/core/build/xtask.md.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from trezor_core_tools import firmware_module
from trezorlib._internal import firmware_headers

#: The key sets a signed bundle can carry, and how each verifies.
KEY_SETS = (("production", False), ("devel", True))
#: A prepared-but-not-yet-signed bundle: a real state, not an error.
UNSIGNED = "unsigned"


def _state(bootloader: Path) -> str:
    """Signing state read off the bootloader bytes (not a build flag)."""
    boot = firmware_headers.BootloaderV2Image.parse(bootloader.read_bytes())
    if not boot.signature_present():
        return UNSIGNED
    for name, dev_keys in KEY_SETS:
        try:
            boot.verify(dev_keys=dev_keys)
            return name
        except Exception:
            continue
    raise SystemExit(
        f"{bootloader} carries a signature that verifies with neither key set"
    )


def _suffix(state: str, devel_build: bool) -> str:
    """Release archive name suffix: from the key set when signed, from `devel_build`
    only when there is no signature to read."""
    if state == UNSIGNED:
        return "-devel-unsigned" if devel_build else "-unsigned"
    return "" if state == "production" else f"-{state}"


def _write_zip(out: Path, entries: list[tuple[str, bytes]]) -> None:
    """Deterministic zip writer (fixed mtime and mode, sorted order)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(entries, key=lambda e: e[0]):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)


def _members(body: dict, model_dir: Path) -> list[Path]:
    """The files one model's bundle names, in a stable order."""
    names = [body["bootloader"]["file"]]
    names += [v["file"] for v in body.get("variants", [])]
    names += [c["file"] for c in body.get("coprocessors", []) if "file" in c]

    out = []
    for name in names:
        path = model_dir / name
        if not path.is_file():
            raise SystemExit(
                f"{body.get('model', model_dir.name)} names {name} but "
                f"{path} is missing -- re-cut the release"
            )
        out.append(path)
    return out


def _check_images(body: dict, model_dir: Path) -> None:
    """The signature covers firmware_root only; every member must still fold to it."""
    bl_path = model_dir / body["bootloader"]["file"]
    boot = firmware_headers.BootloaderV2Image.parse(bl_path.read_bytes())
    try:
        checked = firmware_module.check_bundle_images(
            body, model_dir, bytes(boot.header.firmware_root)
        )
    except firmware_module.BundleImageMismatch as e:
        raise SystemExit(f"{e} -- not packing a bundle the header does not commit to")
    model = body.get("model", model_dir.name)
    for line in checked:
        print(f"  {model:8} {line}")


def pack_bundle(model_dir: Path, out: Path) -> None:
    """Pack ONE model's bundle into its archive (what `xtask upload` /
    `trezorctl -f` install)."""
    bundle_path = model_dir / "bundle.json"
    body = firmware_module.check_manifest(
        json.loads(bundle_path.read_text()), bundle_path
    )
    members = _members(body, model_dir)
    _check_images(body, model_dir)
    entries = [("bundle.json", bundle_path.read_bytes())]
    for member in members:
        entries.append((member.name, member.read_bytes()))
    _write_zip(out, entries)
    total = sum(len(d) for _, d in entries)
    print(f"bundle archive : {out} ({len(entries)} members, {total} B uncompressed)")


def pack_release(
    manifest_path: Path, release_dir: Path, out_dir: Path, devel_build: bool
) -> None:
    doc = json.loads(manifest_path.read_text())
    models = firmware_module.manifest_models(doc, manifest_path)
    if "models" not in doc:
        raise SystemExit(
            f"{manifest_path} is a bundle manifest; a release archive is packed "
            "from the release manifest"
        )

    entries: list[tuple[str, bytes]] = [
        ("release.json", manifest_path.read_bytes()),
    ]
    states: dict[str, str] = {}
    for model, body in sorted(models.items()):
        model_dir = release_dir / model
        if not model_dir.is_dir():
            raise SystemExit(
                f"{manifest_path} has an entry for {model} but {model_dir} is absent"
            )
        per_model = model_dir / "bundle.json"
        members = _members(body, model_dir)
        # before any archive is written
        _check_images(body, model_dir)
        model_entries: list[tuple[str, bytes]] = [
            ("bundle.json", per_model.read_bytes())
        ]
        for member in members:
            model_entries.append((member.name, member.read_bytes()))
        # The model's bundle archive, written once the release is finished.
        bundle_zip = release_dir / f"{model}.zip"
        _write_zip(bundle_zip, model_entries)
        print(f"bundle archive : {bundle_zip}")
        entries += [(f"{model}/{name}", data) for name, data in model_entries]
        states[model] = _state(model_dir / body["bootloader"]["file"])

    # A mixed signing state is not a release.
    distinct = sorted(set(states.values()))
    if len(distinct) > 1:
        detail = ", ".join(f"{m}={k}" for m, k in sorted(states.items()))
        raise SystemExit(
            f"the models in {manifest_path} are not in one signing state "
            f"({detail}) -- re-cut the release"
        )
    state = distinct[0]
    out = out_dir / f"release{_suffix(state, devel_build)}.zip"

    _write_zip(out, entries)

    total = sum(len(d) for _, d in entries)
    label = state if state == UNSIGNED else f"{state} keys"
    print(
        f"release archive: {out} "
        f"({label}, {len(models)} model(s), {len(entries)} members, "
        f"{total} B uncompressed)"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--bundle",
        type=Path,
        help="pack ONE model's bundle (its directory) into a bundle archive "
        "rather than a release; requires --out",
    )
    ap.add_argument(
        "--release",
        type=Path,
        help="the release manifest written by `xtask release` "
        "(build/artifacts/release/release[_devel].json)",
    )
    ap.add_argument(
        "--dir",
        type=Path,
        help="the release directory, holding one bundle subdirectory per model",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        help="where to write the release archive; its NAME is derived from the "
        "key set that signed the release, not passed in",
    )
    ap.add_argument(
        "--devel-build",
        action="store_true",
        help="the release was built with --bootloader-devel. Used ONLY to name "
        "an UNSIGNED release archive, which carries no signature to read the answer "
        "off; a signed one is named from its signatures either way.",
    )
    ap.add_argument(
        "--out", type=Path, help="with --bundle: the bundle archive to write"
    )
    args = ap.parse_args()
    if args.bundle is not None:
        if args.out is None:
            raise SystemExit("--bundle needs --out")
        pack_bundle(args.bundle, args.out)
        return
    if args.release is None or args.dir is None or args.out_dir is None:
        raise SystemExit("--release, --dir and --out-dir are required")
    pack_release(args.release, args.dir, args.out_dir, args.devel_build)


if __name__ == "__main__":
    main()
