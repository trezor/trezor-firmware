#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# Line above is for Path.copy().

import contextlib
import json
import logging
import subprocess
import tempfile
import time
import typing as t
from pathlib import Path

import click

LOG = logging.getLogger(__name__)

SUBPROCESS_LOG = []

BOARDLOADER_VERSIONS = {
    "t2b1": "2.1.4",
    "t2t1": "2.1.4",
    "t3b1": "2.1.3",
    "t3t1": "2.1.4",
    "t3w1": "2.1.4",
}

# maybe try without --depth=1?
BLACKLIST_BOOTLOADERS = [
    "2.0.0",  # can't fetch micropython commit
    "2.0.2",  # fatal: Failed to recurse into submodule path 'vendor/micropython'
    "2.0.3",  # fatal: dumb http transport does not support shallow capabilities
    "2.1.0",  # TypeError: canonicalize_version() got an unexpected keyword argument 'strip_trailing_zero'
]

BLACKLIST_FIRMWARE = [
    ("t3t1", "2.7.2"),  # does not fit flash with PYOPT=0
    ("t3t1", "2.8.0"),  # region `FLASH' overflowed by 7680 bytes
]

# I think this might be achieved by setting environment variable (not "Makefile variable" that
# goes at the end of make commandline) XTASK_BUILD_OPTS to --force-bootloader-upgrade but we
# don't support envvars (yet).
PATCH_XTASK_BOOTLOADER_QA = """
--- a/core/Makefile
+++ b/core/Makefile
@@ -64,6 +64,9 @@ endif
 ifeq ($(BITCOIN_ONLY),1)
 XTASK_BUILD_OPTS += --btc-only
 endif
+ifeq ($(BOOTLOADER_QA),1)
+XTASK_BUILD_OPTS += --force-bootloader-upgrade
+endif
 ifeq ($(BOOTLOADER_DEVEL),1)
 XTASK_BUILD_OPTS += --bootloader-devel
 endif
"""

# Before dadff32f390c062ec554794d1fc5aa89a068fe30 SCons didn't know T2B1 and T2T1
PATCH_INTERNAL_MODELS = """
--- a/core/Makefile
+++ b/core/Makefile
@@ -4,6 +4,13 @@ JOBS = 4
 MAKE = make -j $(JOBS)
 SCONS = scons -Q -j $(JOBS)

+ifeq ($(TREZOR_MODEL),T2B1)
+override TREZOR_MODEL = R
+endif
+ifeq ($(TREZOR_MODEL),T2T1)
+override TREZOR_MODEL = T
+endif
+
 BUILD_DIR             = build
 BOARDLOADER_BUILD_DIR = $(BUILD_DIR)/boardloader
 BOOTLOADER_BUILD_DIR  = $(BUILD_DIR)/bootloader
"""


def setup_logging() -> None:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="[{asctime}] {levelname:<7} {message}", style="{")
    handler.setFormatter(formatter)
    LOG.setLevel(logging.DEBUG)
    LOG.addHandler(handler)


def version_str(vtup: tuple[int, int, int]) -> str:
    return ".".join(map(str, vtup))


def ensure_options(options: str, model: str, opt_file: Path) -> str:
    options = f"{options} TREZOR_MODEL={model.upper()}"
    options = options.strip()
    if not opt_file.exists():
        opt_file.write_text(options + "\n")
    else:
        options_from_file = opt_file.read_text().strip()
        if options != options_from_file:
            LOG.error(
                f"Saved options {opt_file.name} not matching: {options_from_file}"
            )
            raise click.ClickException("Trying to rebuild with different options")
    return options


def guess_model(releases: list[dict]) -> str:
    url = releases[0]["url"].split("/")
    model = url[-2]
    assert len(model) == 4
    assert model[0] == "t"
    assert f"{model[1]}{model[3]}".isnumeric()
    return model


class EnvInfo:
    env_setup: list[str]
    env_fmt: str
    boardloader_path: Path
    bootloader_path: Path
    firmware_path: Path
    bootloader_replace: list[Path]
    repo_dir: Path

    def __init__(self, model: str, repo_dir: Path) -> None:
        self.repo_dir = repo_dir

        # nix changed symlink handling at some point
        self.env_setup = ["ln -s ci/pyright ."]

        # Poetry or uv?
        if (repo_dir / "uv.lock").is_file():
            self.env_fmt = 'nix-shell --pure --run "uv run {}"'
        elif (repo_dir / "poetry.lock").is_file():
            self.env_setup.append('nix-shell --pure --run "poetry install"')
            self.env_fmt = 'nix-shell --pure --run "poetry run {}"'
        else:
            raise click.ClickException(
                f"Neither poetry.lock nor uv.lock found in {repo_dir}"
            )

        # SCons or xtask?
        if (repo_dir / "core" / "embed" / "xtask").exists():
            self.add_patch("xtask-bootloader-qa", PATCH_XTASK_BOOTLOADER_QA)
            self.boardloader_path = Path(
                f"core/build-xtask/artifacts/{model.upper()}/boardloader.bin"
            )
            self.bootloader_path = Path(
                f"core/build-xtask/artifacts/{model.upper()}/bootloader.bin"
            )
            self.firmware_path = Path(
                f"core/build-xtask/artifacts/{model.upper()}/firmware.bin"
            )
        else:
            self.boardloader_path = Path("core/build/boardloader/boardloader.bin")
            self.bootloader_path = Path("core/build/bootloader/bootloader.bin")
            self.firmware_path = Path("core/build/firmware/firmware.bin")

            if "TREZOR_MODEL ?= T\n" in (repo_dir / "core" / "Makefile").read_text():
                self.add_patch("internal-models", PATCH_INTERNAL_MODELS)

        # bootloader replacement
        old_bl_replacement = Path(
            f"core/embed/models/{model.upper()}/bootloaders/bootloader_{model.upper()}.bin"
        )
        new_bl_replacement = Path(
            f"core/embed/firmware/bootloaders/bootloader_{model.upper()}.bin"
        )
        t2t1_old_bl_replacement = Path("core/embed/firmware/bootloader.bin")
        if old_bl_replacement.is_file():
            self.bootloader_replace = [
                old_bl_replacement,
                old_bl_replacement.with_name(f"bootloader_{model.upper()}_qa.bin"),
            ]
        elif new_bl_replacement.is_file():
            self.bootloader_replace = [
                new_bl_replacement,
                new_bl_replacement.with_name(f"bootloader_{model.upper()}_qa.bin"),
            ]
        elif model == "T2T1" and t2t1_old_bl_replacement.is_file():
            self.bootloader_replace = [t2t1_old_bl_replacement]
        else:
            raise click.ClickException("Unknown bootloader replacement path.")

    def add_patch(self, name: str, contents: str) -> None:
        patch_file = self.repo_dir / f"{name}.patch"
        patch_file.write_text(contents)
        self.env_setup.append(f"patch -p1 -i {patch_file}")

    def setup(self) -> None:
        for cmd in self.env_setup:
            sh(cmd)

    def env_sh(self, cmd: str) -> None:
        sh(self.env_fmt.format(cmd))


def bootloader_versions(releases: list[dict]) -> list[str]:
    all_versions = {tuple(rel["bootloader_version"]) for rel in releases}
    return [version_str(v) for v in sorted(all_versions)]


def firmware_versions(releases: list[dict]) -> list[tuple[str, str]]:
    all_versions = [
        (tuple(rel["version"]), tuple(rel["bootloader_version"])) for rel in releases
    ]
    return [(version_str(vfw), version_str(vbl)) for vfw, vbl in sorted(all_versions)]


def sh(command: str) -> None:  # TODO timeout
    LOG.debug(f"Runing: {command}")
    written = 0
    p = subprocess.Popen(
        command, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE
    )
    log_file = SUBPROCESS_LOG[-1]
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    log_file.write(f"RUN: {command}  # {timestamp}\n".encode())
    while True:
        try:
            out, _err = p.communicate(None, timeout=1)
        except subprocess.TimeoutExpired as exc:
            out_len = len(exc.output or ())
            if out_len > written:
                log_file.write(exc.output[written:])
                log_file.flush()
                written = out_len
        else:
            log_file.write(out[written:])
            break
    if p.returncode != 0:
        raise click.ClickException(f"Command failed (code: {p.returncode})")


@contextlib.contextmanager
def log_commands(log_path: Path) -> t.Generator:
    LOG.debug(f"Logging to: {log_path} (use tail -f to watch)")
    with log_path.open("wb") as log_file:
        SUBPROCESS_LOG.append(log_file)
        try:
            yield
        except Exception:
            LOG.error(f"Log saved to {log_path}")
            raise
        finally:
            SUBPROCESS_LOG.pop()


@contextlib.contextmanager
def in_worktree(tag: str) -> t.Generator:
    prefix = f"trezor-firmware-{tag.replace('/', '-')}-"
    tempdir = tempfile.TemporaryDirectory(prefix=prefix, delete=False)
    dir = Path(tempdir.name)
    LOG.debug(f"Creating git worktree from tag {tag}: {dir}")
    try:
        sh(f"git worktree add {dir} {tag}")
        with contextlib.chdir(dir):
            sh("git submodule update --recursive --init --depth=1")
            yield dir
    except Exception:
        LOG.error(f"Operation failed in directory {dir} - not deleting")
        raise
    else:
        tempdir.cleanup()
        LOG.debug(f"Deleted {dir}")
        sh("git worktree prune")


def build_boardloader(
    model: str, version: str, options: str, bin_file: Path, log_file: Path
) -> None:
    git_tag = f"core/boardloader/v{version}"
    LOG.info(f"Rebuilding boardloader {git_tag} with {options}")
    with log_commands(log_file), in_worktree(git_tag) as workdir:
        t = EnvInfo(model, workdir)
        t.setup()
        t.env_sh(f"make -C core build_boardloader {options}")
        t.boardloader_path.copy(bin_file)


def build_bootloader(
    model: str, version: str, options: str, bin_file: Path, log_file: Path
) -> None:
    git_tag = f"core/bl{version}"
    LOG.info(f"Rebuilding bootloader {git_tag} with {options}")
    with log_commands(log_file), in_worktree(git_tag) as workdir:
        t = EnvInfo(model, workdir)
        t.setup()
        t.env_sh(f"make -C core build_bootloader {options}")
        t.bootloader_path.copy(bin_file)


def build_firmware(
    model: str,
    fw_version: str,
    options: str,
    bootloader_bin: Path,
    firmware_bin: Path,
    log_file: Path,
) -> None:
    if not bootloader_bin.is_file():
        raise click.ClickException(f"Missing bootloader {bootloader_bin}")
    git_tag = f"core/v{fw_version}"
    LOG.info(f"Rebuilding firmware {git_tag} with {options}")
    with log_commands(log_file), in_worktree(git_tag) as workdir:
        t = EnvInfo(model, workdir)
        t.setup()
        for dest in t.bootloader_replace:
            bootloader_bin.copy(dest)
        t.env_sh("make gen")
        t.env_sh(f"make -C core build_firmware {options}")
        t.firmware_path.copy(firmware_bin)


def build_combined(
    model: str,
    boardloader_bin: Path,
    bootloader_bin: Path,
    firmware_bin: Path,
    combined_bin: Path,
    log_file: Path,
) -> None:
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent
    LOG.info(f"Making combined from {firmware_bin.name}")
    artifacts_dir = repo_root / "core" / "build-xtask" / "artifacts" / model.upper()
    artifacts_dir.mkdir(exist_ok=True, parents=True)

    for f in ("boardloader", "bootloader", "firmware", "combined-firmware"):
        (artifacts_dir / f"{f}.bin").unlink(missing_ok=True)
    boardloader_bin.copy(artifacts_dir / "boardloader.bin")
    bootloader_bin.copy(artifacts_dir / "bootloader.bin")
    firmware_bin.copy(artifacts_dir / "firmware.bin")

    with contextlib.chdir(repo_root), log_commands(log_file):
        sh(f'nix-shell --run "uv run xtask combine -m {model} firmware"')
    (artifacts_dir / "combined-firmware.bin").copy(combined_bin)


def rebuild_boardloader(
    model: str, boardloader_options: str, log_dir: Path, output_dir: Path
) -> Path:
    boardloader_options = ensure_options(
        boardloader_options, model, output_dir / "boardloader-options.txt"
    )
    boardloader_version = BOARDLOADER_VERSIONS[model]
    boardloader_bin = output_dir / f"boardloader-{boardloader_version}.bin"
    if not boardloader_bin.exists():
        log_file = log_dir / f"boardloader-{boardloader_version}.txt"
        build_boardloader(
            model, boardloader_version, boardloader_options, boardloader_bin, log_file
        )
    else:
        LOG.debug(f"Exists: {boardloader_bin.name}")
    return boardloader_bin


def rebuild_bootloaders(
    model: str,
    releases: list[dict],
    bootloader_options: str,
    log_dir: Path,
    output_dir: Path,
) -> None:
    bootloader_options = ensure_options(
        bootloader_options, model, output_dir / "bootloader-options.txt"
    )
    blv = bootloader_versions(releases)
    LOG.debug(f"Bootloader versions ({len(blv)}): {', '.join(blv)}")
    for bl_version in blv:
        bootloader_bin = output_dir / f"bootloader-{bl_version}.bin"
        if bootloader_bin.exists():
            LOG.debug(f"Exists: {bootloader_bin.name}")
            continue
        if bl_version in BLACKLIST_BOOTLOADERS:
            LOG.warning(f"Skipping blacklisted bootloader {bl_version}")
            continue
        log_file = log_dir / f"bootloader-{bl_version}.txt"
        build_bootloader(
            model, bl_version, bootloader_options, bootloader_bin, log_file
        )
    LOG.info("Bootloaders done")


def rebuild_firmware(
    model: str,
    releases: list[dict],
    firmware_options: str,
    boardloader_bin: Path,
    log_dir: Path,
    output_dir: Path,
) -> None:
    firmware_options = ensure_options(
        firmware_options, model, output_dir / "firmware-options.txt"
    )
    bfw = firmware_versions(releases)
    LOG.debug(f"Firmware versions ({len(bfw)}): {', '.join(v for v, _ in bfw)}")
    for fw_version, bl_version in bfw:
        firmware_bin = output_dir / f"firmware-{fw_version}.bin"
        bootloader_bin = output_dir / f"bootloader-{bl_version}.bin"
        if bl_version in BLACKLIST_BOOTLOADERS:
            LOG.warning(
                f"Skipping firmware {fw_version} with blacklisted bootloader {bl_version}"
            )
            continue
        elif (model, fw_version) in BLACKLIST_FIRMWARE:
            LOG.warning(f"Skipping blacklisted firmware {fw_version}")
            continue
        elif not firmware_bin.exists():
            log_file = log_dir / f"firmware-{fw_version}.txt"
            build_firmware(
                model,
                fw_version,
                firmware_options,
                bootloader_bin,
                firmware_bin,
                log_file,
            )
        else:
            LOG.debug(f"Exists: {firmware_bin.name}")

        combined_bin = output_dir / f"combined-firmware-{fw_version}.bin"
        if not combined_bin.exists():
            log_file = log_dir / f"combined-firmware-{fw_version}.txt"
            build_combined(
                model,
                boardloader_bin,
                bootloader_bin,
                firmware_bin,
                combined_bin,
                log_file,
            )
        else:
            LOG.debug(f"Exists: {combined_bin.name}")
    LOG.info("Firmware done")


@click.command()
@click.argument(
    "releases_json", type=click.Path(exists=True, file_okay=True, dir_okay=False)
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Directory where binaries and logs will be stored.",
)
@click.option(
    "--boardloader-options",
    default="BOOTLOADER_DEVEL=1 PRODUCTION=0",
    help="Boardloader options, without TREZOR_MODEL.",
)
@click.option(
    "--bootloader-options",
    default="BOOTLOADER_DEVEL=1 PRODUCTION=0",
    help="Bootloader options, without TREZOR_MODEL.",
)
@click.option(
    "--firmware-options",
    default="BOOTLOADER_DEVEL=1 BOOTLOADER_QA=1 PRODUCTION=0 PYOPT=0",
    help="Firmware options, without TREZOR_MODEL.",
)
def main(
    output_dir: Path | str,
    releases_json: Path | str,
    boardloader_options: str,
    bootloader_options: str,
    firmware_options: str,
) -> None:
    """
    Rebuild all released firmware versions and bootloaders. You must provide releases.json file
    which is located in the trezor/data repository in the `firmware/<model>` directory.

    Must be started from within a git repository. The repository will be used to create combined images.
    """
    setup_logging()

    releases_json = Path(releases_json)
    with Path(releases_json).open() as fh:
        releases = json.load(fh)

    model = guess_model(releases)
    LOG.info(f"Model: {model.upper()}")
    LOG.info(f"Release file: {releases_json.resolve()}")

    output_dir = Path(output_dir).resolve() / model
    LOG.info(f"Output dir: {output_dir}")
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    boardloader_bin = rebuild_boardloader(
        model, boardloader_options, log_dir, output_dir
    )
    rebuild_bootloaders(model, releases, bootloader_options, log_dir, output_dir)
    rebuild_firmware(
        model, releases, firmware_options, boardloader_bin, log_dir, output_dir
    )


if __name__ == "__main__":
    main()
