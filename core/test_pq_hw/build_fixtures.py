#!/usr/bin/env python3
"""Build the binary fixtures for the PQ secure boot hardware tests (T3W1).

Each source branch is built in its own persistent git worktree under work/, so
the branches never share a checkout and rebuilds stay incremental. Outputs go to
fixtures/, a worktree of the orphan branch tychovrahe/pq/hw_fixtures, and
fixtures/manifest.json records where every file came from.

Run from anywhere inside the nix-shell, with the repo .venv present:

    python core/test_pq_hw/build_fixtures.py                # everything
    python core/test_pq_hw/build_fixtures.py --only release-A
    python core/test_pq_hw/build_fixtures.py --commit       # also commit the set

--only rebuilds the named targets and everything that depends on them: the
intermediaries embed release A's exact bootloader bytes, so they are rebuilt
whenever A is.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import inspect
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORK = HERE / "work"
LOGS = WORK / "logs"
FIXTURES = HERE / "fixtures"
FIXTURES_BRANCH = "tychovrahe/pq/hw_fixtures"
MODEL = "T3W1"

DEFAULT_REFS = {
    "pq": "tychovrahe/pq/bootloader12",
    "intermediary": "tychovrahe/pq/intermediary_exp",
    # Legacy is built from where the intermediary branched off main, so the
    # baseline is the firmware the intermediary was written against.
    "legacy": None,
}

DEVEL = ["--bootloader-devel"]

# Cut points the hardware tests break at, per ELF; each must exist and match
# the staged image. See pqhw/cutpoint.py.
CUT_SYMBOLS = {
    "bootloader": [
        "ucb_stage_verify",
        "nrf_staging_write_desc",
        "ucb_stage_arm",
        "nrf_update_with_progress",
        "nrf_staging_clear",
    ],
    "kernel": ["nrf_update"],
    "secmon": ["boot_image_replace", "boot_ucb_write"],
}
# Firmware debuglink exists only under __debug__, hence pyopt off. Optiga is
# off: every wallet set-up advances its security counter, which lives in the
# chip and survives flash-erase, and a high counter slows every later run.
# Storage then takes its non-Optiga path, so every firmware here (legacy,
# intermediary, PQ) must agree on it.
DEBUG_FW = ["--debug-link", "--pyopt=false", "--disable-animation", "--disable-optiga"]
# Animations off in the bootloaders too: the SWD screenshots then catch
# settled screens, and stall-based confirms are not racing a transition.
DEBUG_BL = ["--debug-link", "--disable-animation"]

FW_VARIANT_SEC = {"universal": 0x5A5A5A5A, "btc-only": 0xA5A5A5A5}


# --------------------------------------------------------------------------
# plumbing


class BuildError(Exception):
    pass


def git(*args: str, cwd: Path = REPO) -> str:
    res = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        raise BuildError(f"git {' '.join(args)} (in {cwd}):\n{res.stderr.strip()}")
    return res.stdout.strip()


def resolve(ref: str) -> str:
    return git("rev-parse", "--verify", f"{ref}^{{commit}}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(msg: str) -> None:
    print(f"[fixtures] {msg}", flush=True)


def run(cmd: list[str], cwd: Path, logname: str, env: dict | None = None) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    logfile = LOGS / f"{logname}.log"
    log(f"$ {' '.join(cmd)}   (in {cwd.relative_to(REPO)}, log {logfile.name})")
    with logfile.open("a") as f:
        f.write(f"\n$ {' '.join(cmd)}\n")
        f.flush()
        res = subprocess.run(cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        tail = logfile.read_text().splitlines()[-40:]
        raise BuildError(f"command failed ({res.returncode}):\n" + "\n".join(tail))


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise BuildError(f"{path}: expected exactly one match for edit:\n{old}")
    path.write_text(text.replace(old, new))


# --------------------------------------------------------------------------
# worktrees


def module_dirs(repo_dir: Path, modules_root: Path) -> dict[str, Path]:
    """Submodule path -> its git dir in the main checkout's .git/modules."""
    gm = repo_dir / ".gitmodules"
    if not gm.exists():
        return {}
    out = git("config", "-f", str(gm), "--get-regexp", r"^submodule\..*\.path$")
    result = {}
    for line in out.splitlines():
        key, path = line.split(" ", 1)
        name = key[len("submodule.") : -len(".path")]
        result[path] = modules_root / name
    return result


def sync_submodules(repo_dir: Path, modules_root: Path) -> None:
    """Check out every gitlink at its pinned commit as a shared clone.

    `git submodule update` would write the superproject's config; a shared
    clone of the main checkout's module directory needs nothing but objects
    that are already on disk.
    """
    dirs = module_dirs(repo_dir, modules_root)
    tree = git("ls-tree", "-r", "HEAD", cwd=repo_dir)
    for line in tree.splitlines():
        meta, path = line.split("\t", 1)
        mode, _, commit = meta.split()
        if mode != "160000":
            continue
        src = dirs.get(path)
        if src is None or not src.exists():
            continue  # not initialised in the main checkout either
        dst = repo_dir / path
        if not (dst / ".git").exists():
            dst.mkdir(parents=True, exist_ok=True)
            git("clone", "--quiet", "--shared", "--no-checkout", str(src), str(dst))
        try:
            git(
                "-c",
                "advice.detachedHead=false",
                "checkout",
                "-q",
                "-f",
                commit,
                cwd=dst,
            )
        except BuildError as e:
            raise BuildError(
                f"{path} is pinned to {commit}, which the main checkout does not "
                f"have; fetch it in {src}\n{e}"
            ) from None
        sync_submodules(dst, src / "modules")


def prepare_worktree(name: str, commit: str) -> Path:
    wt = WORK / name
    if not (wt / ".git").exists():
        WORK.mkdir(parents=True, exist_ok=True)
        log(f"creating worktree {name} at {commit[:10]}")
        git("worktree", "add", "--detach", str(wt), commit)
    else:
        git(
            "-c",
            "advice.detachedHead=false",
            "checkout",
            "-q",
            "-f",
            "--detach",
            commit,
            cwd=wt,
        )
        # Untracked files only: ignored build directories survive, so cargo
        # stays incremental.
        git("clean", "-fdq", cwd=wt)
    sync_submodules(wt, REPO / ".git" / "modules")
    return wt


def prepare_fixtures_dir() -> None:
    if (FIXTURES / ".git").exists():
        return
    exists = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "-q", f"refs/heads/{FIXTURES_BRANCH}"],
            cwd=REPO,
            capture_output=True,
        ).returncode
        == 0
    )
    if exists:
        git("worktree", "add", str(FIXTURES), FIXTURES_BRANCH)
    else:
        git("worktree", "add", "--orphan", "-b", FIXTURES_BRANCH, str(FIXTURES))


def build_env(wt: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("VENDOR_HEADER", None)
    env["PATH"] = f"{REPO / '.venv' / 'bin'}{os.pathsep}{env['PATH']}"
    # Each tree signs with its own tools and its own trezorlib.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(wt / "core" / "tools"), str(wt / "python" / "src")]
    )
    env.update(extra or {})
    return env


def xtask(ctx: Ctx, *args: str, env: dict[str, str] | None = None) -> None:
    run(
        ["cargo", "xtask", *args],
        cwd=ctx.wt / "core" / "embed",
        logname=ctx.target,
        env=build_env(ctx.wt, env),
    )


# --------------------------------------------------------------------------
# source edits (applied to the scratch worktrees only, never committed)


def edit_keep_storage(wt: Path) -> None:
    """Debug builds wipe storage on every hardware boot; seed checks need it kept."""
    replace_once(
        wt / "core" / "src" / "boot.py",
        "if __debug__ and not utils.EMULATOR:\n    config.wipe()\n",
        "# test_pq_hw: storage is kept across reboots in this test build\n",
    )


def edit_stamp_by_variant(wt: Path) -> None:
    """Stamp the variant this build is, and rebuild when the input changes."""
    path = wt / "core" / "embed" / "projects" / "firmware" / "build.rs"
    if "copy_from_slice(&FW_VARIANT_SEC_UNIVERSAL" not in path.read_text():
        log("stamp edit: build.rs no longer stamps UNIVERSAL unconditionally, skipped")
        return
    replace_once(
        path,
        "fn stamp_firmware_type(path: &str) -> Result<String> {\n",
        "fn stamp_firmware_type(path: &str) -> Result<String> {\n"
        '    println!("cargo:rerun-if-changed={path}");\n',
    )
    replace_once(
        path,
        "    let current = u32_at(&img, offset);\n"
        "    if current != FW_VARIANT_SEC_NONE && current != FW_VARIANT_SEC_UNIVERSAL {\n",
        '    let stamp: u32 = if env::var("CARGO_FEATURE_UNIVERSAL_FW").is_ok() {\n'
        "        FW_VARIANT_SEC_UNIVERSAL\n"
        "    } else {\n"
        "        0xA5A5_A5A5 // FW_VARIANT_SEC_BITCOIN_ONLY\n"
        "    };\n"
        "    let current = u32_at(&img, offset);\n"
        "    if current != FW_VARIANT_SEC_NONE && current != stamp {\n",
    )
    replace_once(
        path,
        "copy_from_slice(&FW_VARIANT_SEC_UNIVERSAL.to_le_bytes());",
        "copy_from_slice(&stamp.to_le_bytes());",
    )
    replace_once(
        path,
        "firmware_type=0x{FW_VARIANT_SEC_UNIVERSAL:08X}",
        "firmware_type=0x{stamp:08X}",
    )


@dataclass
class Edit:
    name: str
    apply: Callable[[Path], None]
    desc: str
    args: dict = field(default_factory=dict)


def source_edit(fn: Callable[[Path], None]) -> Edit:
    src_hash = hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()[:16]
    return Edit(fn.__name__, fn, f"source {src_hash}")


def set_defines(path: Path, values: dict[str, int]) -> None:
    text = path.read_text()
    for name, value in values.items():
        new, n = re.subn(
            rf"^(#define {name}) +\d+$", rf"\g<1> {value}", text, flags=re.M
        )
        if n != 1:
            raise BuildError(f"{path}: expected one #define {name}")
        text = new
    path.write_text(text)


def version_defines(prefix: str, version: str) -> dict[str, int]:
    parts = [int(x) for x in version.split(".")]
    parts += [0] * (4 - len(parts))
    keys = ("MAJOR", "MINOR", "PATCH", "BUILD")
    return {f"{prefix}_{k}": v for k, v in zip(keys, parts)}


def edit_versions(
    firmware: str | None = None,
    bootloader: str | None = None,
    fix: str | None = None,
    min_prev: str | None = None,
    monotonic: int | None = None,
) -> Edit:
    """Version fields for a release, so the sets install in a meaningful order.

    fix and min_prev are the BOOTLOADER header's floors, compared against
    bootloader versions.
    """
    args = dict(
        firmware=firmware,
        bootloader=bootloader,
        fix=fix,
        min_prev=min_prev,
        monotonic=monotonic,
    )

    def apply(wt: Path) -> None:
        proj = wt / "core" / "embed" / "projects"
        if firmware:
            set_defines(
                proj / "firmware" / "version.h", version_defines("VERSION", firmware)
            )
        bl = {}
        if bootloader:
            bl |= version_defines("VERSION", bootloader)
        if fix:
            bl |= version_defines("FIX_VERSION", fix)
        if min_prev:
            bl |= version_defines("MIN_PREV_VERSION", min_prev)
        if bl:
            set_defines(proj / "bootloader" / "version.h", bl)
        if monotonic is not None:
            set_defines(
                wt / "core" / "embed" / "models" / MODEL / "versions.h",
                {"BOOTLOADER_MONOTONIC_VERSION": monotonic},
            )

    set_args = {k: v for k, v in args.items() if v is not None}
    desc = ", ".join(f"{k}={v}" for k, v in set_args.items())
    return Edit("versions", apply, desc, set_args)


def nrf_version(image: bytes) -> str:
    """MCUboot image header version: major.minor.revision."""
    major, minor, rev = struct.unpack_from("<BBH", image, 20)
    return f"{major}.{minor}.{rev}"


def edit_nrf_input(name: str) -> Edit:
    """Release this nRF build instead of the tree's committed one.

    `name` is a file under fixtures/inputs/, frozen there so a rebuild does not
    depend on whatever the nordic build directory holds at the time.
    """
    src = FIXTURES / "inputs" / name

    def apply(wt: Path) -> None:
        if not src.exists():
            raise BuildError(f"missing nRF input {src}")
        dst = wt / "core" / "embed" / "models" / MODEL / "trezor-ble-dev-bare.bin"
        shutil.copyfile(src, dst)

    desc = f"{name} sha256 {sha256(src)[:16]}" if src.exists() else name
    version = nrf_version(src.read_bytes()) if src.exists() else None
    return Edit("nrf-input", apply, desc, {"nrf_version": version})


def touch_version_includers(wt: Path) -> None:
    """Force a recompile of everything that includes a version.h.

    The build's dependency tracking misses headers pulled into assembly files
    (header.S, manifest_header.S), so a version edit would otherwise leave the
    previous version in the image.
    """
    embed = wt / "core" / "embed"
    skip = {"build-xtask", "target", "vendor"}
    for path in embed.rglob("*"):
        if skip & set(path.relative_to(embed).parts):
            continue
        if path.suffix in (".c", ".S", ".h") and path.is_file():
            if "version.h" in path.read_text(errors="ignore"):
                path.touch()


# --------------------------------------------------------------------------
# manifest


@dataclass
class Ctx:
    target: str
    source: str
    commit: str
    wt: Path
    edits: list[Edit] = field(default_factory=list)
    files: dict[str, dict] = field(default_factory=dict)

    def expected(self) -> dict:
        exp: dict = {}
        for e in self.edits:
            exp |= e.args
        return exp

    def stage(
        self, src: Path, rel: str, build: list[str] | None = None, **info
    ) -> Path:
        dst = FIXTURES / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        self.files[rel] = {
            "sha256": sha256(dst),
            "size": dst.stat().st_size,
            "target": self.target,
            "source": self.source,
            "commit": self.commit,
            "edits": {e.name: e.desc for e in self.edits},
            "build": build or [],
            **info,
        }
        log(f"staged {rel}")
        return dst


def check_elf_matches(elf: Path, image: bytes, symbol: str) -> None:
    """The code at `symbol` in `elf` is in `image`: the ELF the cut-point driver
    takes addresses from is the build that was released, not a later one."""
    from elftools.elf.elffile import ELFFile

    with elf.open("rb") as f:
        e = ELFFile(f)
        sym = next(
            (
                s
                for s in e.get_section_by_name(".symtab").iter_symbols()
                if s.name == symbol
            ),
            None,
        )
        if sym is None:
            raise BuildError(f"{elf.name}: no symbol {symbol}")
        addr = sym["st_value"] & ~1
        for sec in e.iter_sections():
            start, size = sec["sh_addr"], sec["sh_size"]
            if sec["sh_type"] == "SHT_PROGBITS" and start <= addr < start + size:
                code = sec.data()[addr - start : addr - start + 64]
                break
        else:
            raise BuildError(f"{elf.name}: {symbol} is in no loadable section")
    if code not in image:
        raise BuildError(
            f"{elf.name}: the code at {symbol} is not in the staged image "
            "(the ELF is from another build)"
        )


def load_manifest() -> dict:
    path = FIXTURES / "manifest.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"model": MODEL, "files": {}}


def bootloader_info(path: Path) -> dict:
    """Header fields worth seeing at a glance, read with the repo's trezorlib."""
    try:
        sys.path.insert(0, str(REPO / "python" / "src"))
        from trezorlib.firmware import core

        h = core.BootableImage.parse(path.read_bytes()).header
        fmt = lambda v: ".".join(str(x) for x in v)  # noqa: E731
        return {
            "version": fmt(h.version),
            "fix_version": fmt(h.fix_version),
            "min_prev_version": fmt(h.min_prev_version),
            "monotonic": h.monotonic,
        }
    except Exception as e:  # informational only
        return {"header": f"unparsed: {type(e).__name__}"}


# --------------------------------------------------------------------------
# targets


def artifacts(ctx: Ctx) -> Path:
    return ctx.wt / "core" / "build-xtask" / "artifacts" / MODEL


def build_vendorheader_btc(ctx: Ctx) -> None:
    """Dev-signed vendor header with fw_type 3.

    Every --bootloader-devel legacy build uses vendor_dev_DO_NOT_SIGN, whose
    fw_type is 2 whatever --btc-only says, so a devel "btc-only" legacy unit
    would really salt its storage as universal.
    """
    vh_dir = ctx.wt / "core" / "embed" / "models" / MODEL / "vendorheader"
    spec = json.loads((vh_dir / "vendor_dev_DO_NOT_SIGN.json").read_text())
    spec["fw_type"] = 3
    spec["text"] = "DEV ONLY BTC, DO NOT USE!"
    name = "dev_btconly_DO_NOT_SIGN"
    (vh_dir / f"vendor_{name}.json").write_text(json.dumps(spec, indent=4) + "\n")
    shutil.copyfile(
        vh_dir / "vendor_dev_DO_NOT_SIGN.toif", vh_dir / f"vendor_{name}.toif"
    )

    env = build_env(ctx.wt)
    run(
        [
            sys.executable,
            str(ctx.wt / "core" / "tools" / "build_vendorheader"),
            "--quiet",
            f"vendor_{name}.json",
        ],
        cwd=vh_dir,
        logname=ctx.target,
        env=env,
    )
    signed = vh_dir / f"vendorheader_{name}_signed_dev.bin"
    shutil.copyfile(vh_dir / f"vendorheader_{name}_unsigned.bin", signed)
    run(
        ["headertool", "--quiet", "-D", str(signed)],
        cwd=vh_dir,
        logname=ctx.target,
        env=env,
    )
    ctx.stage(signed, "legacy/vendorheader_dev_btconly_signed_dev.bin", fw_type=3)


def build_legacy(ctx: Ctx) -> None:
    out = artifacts(ctx)
    vh_dir = ctx.wt / "core" / "embed" / "models" / MODEL / "vendorheader"
    vh_uni = vh_dir / "vendorheader_dev_DO_NOT_SIGN_signed_dev.bin"
    vh_btc = FIXTURES / "legacy" / "vendorheader_dev_btconly_signed_dev.bin"
    if not vh_btc.exists():
        raise BuildError(
            "legacy needs the btc-only vendor header: build vendorheader-btc"
        )

    args = ["build", "boardloader", "-m", MODEL, *DEVEL]
    xtask(ctx, *args)
    ctx.stage(out / "boardloader.bin", "legacy/boardloader.bin", args)

    args = ["build", "bootloader", "-m", MODEL, *DEVEL, *DEBUG_BL]
    xtask(ctx, *args)
    ctx.stage(
        out / "bootloader.bin",
        "legacy/bootloader.bin",
        args,
        **bootloader_info(out / "bootloader.bin"),
    )

    for variant, extra, vh in (
        ("universal", [], vh_uni),
        ("btc-only", ["--btc-only"], vh_btc),
    ):
        args = ["build", "firmware", "-m", MODEL, *DEVEL, *DEBUG_FW, *extra]
        env = {"VENDOR_HEADER": str(vh)} if variant == "btc-only" else None
        xtask(ctx, *args, env=env)
        fw = out / "firmware.bin"
        if fw.read_bytes()[: vh.stat().st_size] != vh.read_bytes():
            raise BuildError(
                f"legacy {variant}: firmware does not start with {vh.name}"
            )
        ctx.stage(
            fw,
            f"legacy/firmware-{variant}.bin",
            args + ([f"VENDOR_HEADER={vh.name}"] if env else []),
            variant=variant,
        )


def build_release(ctx: Ctx, name: str) -> None:
    out = artifacts(ctx)
    tree = ctx.wt / "core" / "build-xtask" / "tree"

    xtask(ctx, "build", "boardloader", "-m", MODEL, *DEVEL)
    args_bl = ["build", "bootloader", "-m", MODEL, *DEVEL, *DEBUG_BL]
    xtask(ctx, *args_bl)
    # Kept before the release step, which builds other projects into the same
    # artifacts directory; checked against the released bootloader below.
    bl_elf = LOGS / f"{name}-bootloader.elf"
    shutil.copyfile(out / "bootloader.elf", bl_elf)
    args = ["release", "--bootloader", "built", *DEVEL, *DEBUG_FW]
    xtask(ctx, *args)

    bundle = json.loads((tree / MODEL / "bundle.json").read_text())
    check_release_versions(ctx, tree / MODEL, bundle)
    names = ["bundle.json", bundle["bootloader"]["file"]]
    names += [v["file"] for v in bundle["variants"]]
    names += [c["file"] for c in bundle.get("coprocessors", [])]
    for n in names:
        info = (
            bootloader_info(tree / MODEL / n)
            if n == bundle["bootloader"]["file"]
            else {}
        )
        ctx.stage(
            tree / MODEL / n, f"{name}/{MODEL}/{n}", args_bl + ["&&"] + args, **info
        )
    ctx.stage(tree / f"{MODEL}.zip", f"{name}/{MODEL}.zip", args)
    # Symbols for the SWD cut-point driver (pqhw/cutpoint.py).
    bl_bin = (tree / MODEL / bundle["bootloader"]["file"]).read_bytes()
    for sym in CUT_SYMBOLS["bootloader"]:
        check_elf_matches(bl_elf, bl_bin, sym)
    ctx.stage(bl_elf, f"{name}/{MODEL}/bootloader.elf", args_bl)
    devel_zip = tree / "release-devel.zip"
    if devel_zip.exists():
        ctx.stage(devel_zip, f"{name}/release-devel.zip", args)

    args = ["combine", "prodtest", "-m", MODEL]
    xtask(ctx, *args)
    ctx.stage(out / "combined-prodtest.bin", f"{name}/combined-prodtest.bin", args)
    log(f"{name}: variants {[v['variant'] for v in bundle['variants']]}")


def check_release_versions(ctx: Ctx, rel_dir: Path, bundle: dict) -> None:
    """The images must carry the versions the edit asked for."""
    exp = ctx.expected()
    bl = bootloader_info(rel_dir / bundle["bootloader"]["file"])
    wanted = {
        "version": exp.get("bootloader"),
        "fix_version": exp.get("fix"),
        "min_prev_version": exp.get("min_prev"),
    }
    for key, want in wanted.items():
        if want and bl.get(key) != f"{want}.0":
            raise BuildError(
                f"{ctx.target}: bootloader {key} is {bl.get(key)}, expected {want}"
            )
    if "monotonic" in exp and bl.get("monotonic") != exp["monotonic"]:
        raise BuildError(f"{ctx.target}: bootloader monotonic is {bl.get('monotonic')}")
    if exp.get("nrf_version"):
        for c in bundle.get("coprocessors", []):
            got = nrf_version((rel_dir / c["file"]).read_bytes())
            if got != exp["nrf_version"]:
                raise BuildError(
                    f"{ctx.target}: nRF image is {got}, expected {exp['nrf_version']}"
                )
    if "firmware" in exp:
        want = f"{exp['firmware']}.0"
        for v in bundle["variants"]:
            if v["variant"] == "prodtest":
                continue  # prodtest has its own version.h
            data = (rel_dir / v["file"]).read_bytes()
            got = ".".join(str(x) for x in data[8:12])
            if data[:4] != b"TRZD" or got != want:
                raise BuildError(
                    f"{ctx.target}: {v['variant']} manifest says {got}, expected {want}"
                )


def legacy_fw_version(path: Path) -> str:
    sys.path.insert(0, str(REPO / "python" / "src"))
    from trezorlib import firmware

    fw = firmware.parse(path.read_bytes())
    return ".".join(str(x) for x in fw.firmware.header.version)


def build_intermediary(ctx: Ctx) -> None:
    rel_dir = FIXTURES / "release-A" / MODEL
    bundle_path = rel_dir / "bundle.json"
    if not bundle_path.exists():
        raise BuildError("the intermediaries embed release A: build release-A first")
    bundle = json.loads(bundle_path.read_text())
    a_bl = (rel_dir / bundle["bootloader"]["file"]).read_bytes()
    nrf = [c for c in bundle.get("coprocessors", []) if c["kind"] == "nrf"]
    if len(nrf) != 1:
        raise BuildError("release A must carry exactly one nRF image")
    a_nrf = (rel_dir / nrf[0]["file"]).read_bytes()
    ft = bundle["bootloader"]["firmware_type"]

    models = ctx.wt / "core" / "embed" / "models" / MODEL
    vh_btc = FIXTURES / "legacy" / "vendorheader_dev_btconly_signed_dev.bin"
    out = artifacts(ctx)

    for variant, extra in (("universal", []), ("btc-only", ["--btc-only"])):
        # Re-copied for each build: the worktree reset restores the tracked files.
        (models / "bootloaders" / f"bootloader_{MODEL}_devel.bin").write_bytes(a_bl)
        (models / "trezor-ble-dev.bin").write_bytes(a_nrf)
        args = ["build", "firmware", "-m", MODEL, *DEVEL, *DEBUG_FW, *extra]
        env = {"VENDOR_HEADER": str(vh_btc)} if variant == "btc-only" else None
        xtask(ctx, *args, env=env)

        fw = (out / "firmware.bin").read_bytes()
        stamped = bytearray(a_bl)
        off, ln = ft["offset"], ft["len"]
        stamped[off : off + ln] = FW_VARIANT_SEC[variant].to_bytes(ln, "little")
        if bytes(stamped) not in fw:
            raise BuildError(
                f"intermediary {variant}: release A's bootloader stamped "
                f"0x{FW_VARIANT_SEC[variant]:08X} is not embedded (stale build or wrong stamp)"
            )
        if a_nrf not in fw:
            raise BuildError(
                f"intermediary {variant}: release A's nRF image is not embedded"
            )
        want = ctx.expected().get("firmware")
        got = legacy_fw_version(out / "firmware.bin")
        if want and got != f"{want}.0":
            raise BuildError(
                f"intermediary {variant}: firmware version {got}, expected {want}"
            )
        if variant == "btc-only" and not fw.startswith(vh_btc.read_bytes()):
            raise BuildError("intermediary btc-only: wrong vendor header")
        for part in ("kernel", "secmon"):
            for sym in CUT_SYMBOLS[part]:
                check_elf_matches(out / f"{part}.elf", fw, sym)
            ctx.stage(
                out / f"{part}.elf",
                f"intermediary/{part}-{variant}.elf",
                args,
                variant=variant,
            )
        ctx.stage(
            out / "firmware.bin",
            f"intermediary/firmware-{variant}.bin",
            args + (["VENDOR_HEADER=" + vh_btc.name] if env else []),
            variant=variant,
            stamp=f"0x{FW_VARIANT_SEC[variant]:08X}",
            embeds={
                "bootloader": sha256(rel_dir / bundle["bootloader"]["file"]),
                "nrf": sha256(rel_dir / nrf[0]["file"]),
            },
        )


@dataclass
class Target:
    name: str
    source: str
    deps: list[str]
    edits: list[Edit]
    build: Callable[[Ctx], None]


KEEP = source_edit(edit_keep_storage)
STAMP = source_edit(edit_stamp_by_variant)


# Releases from B on carry a second nRF build, so A -> B is a real nRF push.
NRF_B = "nrf-1.1.3-dev-bare.bin"


def release(name: str, nrf: str | None = None, **versions) -> Target:
    edits = [KEEP, edit_versions(**versions)]
    if nrf:
        edits.append(edit_nrf_input(nrf))
    return Target(name, "pq", [], edits, lambda ctx: build_release(ctx, name))


# Versions climb in install order: legacy 2.13.0 / bl 2.1.18 (main, unchanged)
# -> intermediary 2.13.1 -> A -> B; the floor releases sit above B.
TARGETS = [
    Target("vendorheader-btc", "legacy", [], [], build_vendorheader_btc),
    Target("legacy", "legacy", ["vendorheader-btc"], [KEEP], build_legacy),
    release("release-A", firmware="2.14.0", bootloader="2.1.19"),
    Target(
        "intermediary",
        "intermediary",
        ["release-A", "vendorheader-btc"],
        [KEEP, STAMP, edit_versions(firmware="2.13.1")],
        build_intermediary,
    ),
    release("release-B", nrf=NRF_B, firmware="2.14.1", bootloader="2.1.20"),
    # Seed is kept only by releases at or above 2.1.20: B-fix -> A wipes, -> B keeps.
    release(
        "release-B-fix", nrf=NRF_B, firmware="2.14.2", bootloader="2.1.20", fix="2.1.20"
    ),
    # Installs only over a bootloader >= 2.1.20: refused from A, accepted from B.
    release(
        "release-C-minprev",
        nrf=NRF_B,
        firmware="2.14.3",
        bootloader="2.1.21",
        min_prev="2.1.20",
    ),
    # Burns bootloader monotonic 4; afterwards A and B are refused. flash-erase resets.
    release(
        "release-E-mono", nrf=NRF_B, firmware="2.14.4", bootloader="2.1.22", monotonic=4
    ),
]
BY_NAME = {t.name: t for t in TARGETS}


def selected(only: list[str] | None) -> list[Target]:
    if not only:
        return TARGETS
    unknown = set(only) - BY_NAME.keys()
    if unknown:
        raise BuildError(f"unknown targets {sorted(unknown)}; have {list(BY_NAME)}")
    chosen = set(only)
    changed = True
    while changed:  # add every dependent
        changed = False
        for t in TARGETS:
            if t.name not in chosen and chosen & set(t.deps):
                chosen.add(t.name)
                changed = True
    return [t for t in TARGETS if t.name in chosen]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--only",
        nargs="+",
        metavar="TARGET",
        help=f"targets to rebuild, plus their dependents: {list(BY_NAME)}",
    )
    p.add_argument(
        "--ref",
        action="append",
        default=[],
        metavar="SOURCE=REF",
        help=f"override a source ref; sources: {list(DEFAULT_REFS)}",
    )
    p.add_argument(
        "--commit",
        action="store_true",
        help=f"commit the resulting set on {FIXTURES_BRANCH}",
    )
    a = p.parse_args()

    refs = dict(DEFAULT_REFS)
    for item in a.ref:
        k, _, v = item.partition("=")
        if k not in refs or not v:
            p.error(f"--ref {item}: expected one of {list(refs)}=REF")
        refs[k] = v
    labels = dict(refs)
    if refs["legacy"] is None:
        refs["legacy"] = git("merge-base", refs["intermediary"], "main")
        labels["legacy"] = f"merge-base({refs['intermediary']}, main)"

    try:
        commits = {k: resolve(v) for k, v in refs.items()}
        prepare_fixtures_dir()
        manifest = load_manifest()
        for t in selected(a.only):
            log(f"=== {t.name} ({t.source} @ {commits[t.source][:10]})")
            wt = prepare_worktree(t.source, commits[t.source])
            for e in t.edits:
                e.apply(wt)
            touch_version_includers(wt)
            ctx = Ctx(t.name, t.source, commits[t.source], wt, t.edits)
            t.build(ctx)
            manifest["files"] = {
                k: v for k, v in manifest["files"].items() if v["target"] != t.name
            }
            manifest["files"].update(ctx.files)
            manifest["sources"] = {
                k: {"ref": labels[k], "commit": commits[k]} for k in refs
            }
            manifest["builder"] = git("rev-parse", "HEAD")
            manifest["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
            (FIXTURES / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            )
        if a.commit:
            git("add", "-A", cwd=FIXTURES)
            src = ", ".join(f"{k} {c[:10]}" for k, c in commits.items())
            git("commit", "-q", "-m", f"fixtures: {MODEL} ({src})", cwd=FIXTURES)
            log(f"committed on {FIXTURES_BRANCH}")
    except BuildError as e:
        log(f"FAILED: {e}")
        return 1
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
