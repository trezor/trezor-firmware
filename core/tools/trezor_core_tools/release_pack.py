#!/usr/bin/env python3
"""Pack every model's signed release into ONE publishable container.

A release is not a per-model thing. One source tag builds every model, the
ceremony signs each model's `modelRoot`, and what gets published is the whole
set -- so the artifact carries no model in its name:

    release.zip
    |-- bundle.json          the cross-model index (TRZL-set)
    |-- T3W1/bundle.json     that model's own container (TRZL)
    |-- T3W1/bootloader.bin
    |-- T3W1/universal.bin
    |-- T3W1/...
    `-- <MODEL>/...          one subtree per model in the release

Each model's subtree is SELF-CONTAINED: it holds its own `bundle.json`, so
extracting one subtree gives a working per-model release and the ordinary
per-model reader works on it unchanged. The root index says what the container
holds without listing directories. The duplication between the two is
deliberate and cannot drift -- both are written from the same cut.

Members come from what each model's container NAMES (its bootloader, its
variants, its co-processors), never from globbing the release directory. That
directory also accumulates derived files -- `bootloader-<variant>.bin` written
by `xtask flash`/`combine` when stamping -- and sweeping those in would put
several near-copies of the bootloader in a published artifact.

No signature covers this container, and none is needed: each model's boot-header
signature is the trust root, and the device pins the stamped `firmware_type` to
the authenticated manifest variant, so tampering is a fail-closed DoS and never
a forgery.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from trezor_core_tools import firmware_module
from trezorlib._internal import firmware_headers

#: The key sets a signed release can carry, and how each verifies.
KEY_SETS = (("production", False), ("devel", True))
#: A release that has not been signed yet. A real state, not an error: the
#: release flow prepares everything first and signs it as a whole afterwards.
UNSIGNED = "unsigned"


def _state(bootloader: Path) -> str:
    """Whether this bootloader is signed, and by which keys -- from the BYTES.

    Read off the artifact rather than taken from a build flag, because a flag
    states intent while the signature is fact, and the two diverge: signing is
    always done with development keys today, so a release cut without
    `--bootloader-devel` would otherwise be handed the production name while
    carrying devel signatures.

    The signatures live in the boot header's UNAUTHENTICATED region inside
    `bootloader.bin` (`slh_signature[]` / `ec_signature[]`), so nothing extra
    has to be recorded in the container for this to be answerable.
    """
    boot = firmware_headers.BootloaderV2Image.parse(bootloader.read_bytes())
    # The canonical predicate, which covers BOTH signature families -- an
    # open-coded zero check looking at only one of them would call a
    # half-attached release unsigned.
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
    """The container's name suffix for a release in `state`.

    Signed: the key set decides, and the flag is ignored -- the signature is the
    fact. Unsigned: there is no signature to read, so the only thing that
    distinguishes a development bundle from a production candidate is how it was
    built, and that is what `devel_build` carries.
    """
    if state == UNSIGNED:
        return "-devel-unsigned" if devel_build else "-unsigned"
    return "" if state == "production" else f"-{state}"


def _write_zip(out: Path, entries: list[tuple[str, bytes]]) -> None:
    """One deterministic archive writer for every archive a release produces.

    Identical inputs must give identical bytes so a container can be digested
    and that digest published, which `ZipFile.write` defeats by stamping each
    member's mtime. Fixed timestamp and mode, sorted order.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(entries, key=lambda e: e[0]):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)


def _members(body: dict, model_dir: Path) -> list[Path]:
    """The files one model's container names, in a stable order."""
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


def pack_single(model_dir: Path, out: Path) -> None:
    """Pack ONE model's published set into a container.

    What `xtask upload` installs. `trezorctl firmware update -f` takes a FILE,
    so the published directory -- which is what `flash` installs and therefore
    the one canonical set -- has to be packed for it. Built from the same
    manifest and the same deterministic writer as a release container, so the
    two cannot describe the set differently.
    """
    bundle_path = model_dir / "bundle.json"
    body = firmware_module.check_container(
        json.loads(bundle_path.read_text()), bundle_path
    )
    entries = [("bundle.json", bundle_path.read_bytes())]
    for member in _members(body, model_dir):
        entries.append((member.name, member.read_bytes()))
    _write_zip(out, entries)
    total = sum(len(d) for _, d in entries)
    print(f"install        : {out} ({len(entries)} members, {total} B uncompressed)")


def pack(set_path: Path, tree_dir: Path, out_dir: Path, devel_build: bool) -> None:
    doc = json.loads(set_path.read_text())
    models = firmware_module.container_models(doc, set_path)
    if "models" not in doc:
        raise SystemExit(
            f"{set_path} is a single-model container; the publishable release "
            "is packed from the cross-model set"
        )

    entries: list[tuple[str, bytes]] = [
        ("bundle.json", set_path.read_bytes()),
    ]
    states: dict[str, str] = {}
    for model, body in sorted(models.items()):
        model_dir = tree_dir / model
        if not model_dir.is_dir():
            raise SystemExit(
                f"{set_path} has an entry for {model} but {model_dir} is absent"
            )
        # The model's own container first, so its subtree stands alone.
        per_model = model_dir / "bundle.json"
        model_entries: list[tuple[str, bytes]] = [
            ("bundle.json", per_model.read_bytes())
        ]
        for member in _members(body, model_dir):
            model_entries.append((member.name, member.read_bytes()))
        # The per-model archive: what a single device install consumes, and what
        # `trezorctl firmware update -f` takes. Written HERE rather than by the
        # signer, because a release is packed only once it is finished -- an
        # archive cut before signatures were attached would hold an unsigned
        # bootloader while the directory beside it held a signed one.
        per_model_zip = tree_dir / f"{model}.zip"
        _write_zip(per_model_zip, model_entries)
        # Announced, because this OVERWRITES the file `xtask upload` installs.
        # Cutting a release replacing it silently made "did my build reach the
        # device?" unanswerable from the log.
        print(f"per-model     : {per_model_zip}")
        entries += [(f"{model}/{name}", data) for name, data in model_entries]
        states[model] = _state(model_dir / body["bootloader"]["file"])

    # One run signs every model together, so a mixed set is not a release -- it
    # is two half-releases sharing a directory, and naming the container after
    # either half would be wrong.
    distinct = sorted(set(states.values()))
    if len(distinct) > 1:
        detail = ", ".join(f"{m}={k}" for m, k in sorted(states.items()))
        raise SystemExit(
            f"the models in {set_path} are not in one signing state "
            f"({detail}) -- re-cut the release"
        )
    state = distinct[0]
    out = out_dir / f"release{_suffix(state, devel_build)}.zip"

    _write_zip(out, entries)

    total = sum(len(d) for _, d in entries)
    label = state if state == UNSIGNED else f"{state} keys"
    print(
        f"release        : {out} "
        f"({label}, {len(models)} model(s), {len(entries)} members, "
        f"{total} B uncompressed)"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--single",
        type=Path,
        help="pack ONE model's published set (its directory) rather than a "
        "cross-model release; requires --out",
    )
    ap.add_argument(
        "--set",
        type=Path,
        help="the cross-model bundle written by `xtask release` "
        "(build-xtask/tree/bundle[_devel].json)",
    )
    ap.add_argument(
        "--tree",
        type=Path,
        help="the directory holding one subdirectory per released model",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        help="where to write the container; its NAME is derived from the key "
        "set that signed the release, not passed in",
    )
    ap.add_argument(
        "--devel-build",
        action="store_true",
        help="the release was built with --bootloader-devel. Used ONLY to name "
        "an UNSIGNED container, which carries no signature to read the answer "
        "off; a signed one is named from its signatures either way.",
    )
    ap.add_argument("--out", type=Path, help="with --single: the container to write")
    args = ap.parse_args()
    if args.single is not None:
        if args.out is None:
            raise SystemExit("--single needs --out")
        pack_single(args.single, args.out)
        return
    if args.set is None or args.tree is None or args.out_dir is None:
        raise SystemExit("--set, --tree and --out-dir are required")
    pack(args.set, args.tree, args.out_dir, args.devel_build)


if __name__ == "__main__":
    main()
