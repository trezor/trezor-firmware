from __future__ import annotations

from pathlib import Path

import subprocess
from boards import trezor_1, trezor_r_v3, trezor_r_v4, trezor_t, trezor_r_v6, trezor_r_v10, discovery

HERE = Path(__file__).parent.resolve()

# go up from site_scons to core/
PROJECT_ROOT = HERE.parent.resolve()


def add_font(
    font_name: str, font: str | None, defines: list[str], sources: list[str]
) -> None:
    if font is not None:
        defines += [
            "TREZOR_FONT_" + font_name + "_ENABLE=" + font,
            "TREZOR_FONT_" + font_name + '_INCLUDE=\\"' + font.lower() + '.h\\"',
        ]
        sourcefile = "embed/lib/fonts/" + font.lower() + ".c"
        if sourcefile not in sources:
            sources.append(sourcefile)


def configure_board(
    model: str,
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
):
    model_r_version = 10

    if model in ("1",):
        return trezor_1.configure(env, features_wanted, defines, sources)
    elif model in ("T",):
        return trezor_t.configure(env, features_wanted, defines, sources)
    elif model in ("R",):
        if model_r_version == 3:
            return trezor_r_v3.configure(env, features_wanted, defines, sources)
        elif model_r_version == 4:
            return trezor_r_v4.configure(env, features_wanted, defines, sources)
        elif  model_r_version == 6:
            return trezor_r_v6.configure(env, features_wanted, defines, sources)
        elif model_r_version == 10:
            return trezor_r_v10.configure(env, features_wanted, defines, sources)
    elif model in ('DISC1',):
        return discovery.configure(env, features_wanted, defines, sources)
    else:
        raise Exception("Unknown model")


def get_model_identifier(model: str) -> str:
    if model == "1":
        return "T1B1"
    elif model == "T":
        return "T2T1"
    elif model == "R":
        return "T2B1"
    elif model == 'DISC1':
        return "D001"
    else:
        raise Exception("Unknown model")


def get_version(file: str) -> str:
    major = 0
    minor = 0
    patch = 0

    file_path = PROJECT_ROOT / file
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("#define VERSION_MAJOR "):
                major = line.split("VERSION_MAJOR")[1].strip()
            if line.startswith("#define VERSION_MINOR "):
                minor = line.split("VERSION_MINOR")[1].strip()
            if line.startswith("#define VERSION_PATCH "):
                patch = line.split("VERSION_PATCH")[1].strip()
        return f"{major}.{minor}.{patch}"


def get_git_revision_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


def get_git_modified() -> bool:
    return (
        subprocess.check_output(["git", "diff", "--name-status"])
        .decode("ascii")
        .strip()
        != ""
    )


def get_defs_for_cmake(defs: list[str | tuple[str, str]]) -> list[str]:
    result: list[str] = []
    for d in defs:
        if type(d) is tuple:
            result.append(d[0] + "=" + d[1])
        else:
            result.append(d)
    return result
