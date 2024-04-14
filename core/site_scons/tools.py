from __future__ import annotations

import subprocess
import zlib
from pathlib import Path

HERE = Path(__file__).parent.resolve()

# go up from site_scons to core/
PROJECT_ROOT = HERE.parent.resolve()


def add_font(
    font_name: str, font: str | None, defines: list[str], sources: list[str]
) -> None:
    if font is not None:
        font_filename = font.replace("_upper", "").lower()
        defines += [
            "TREZOR_FONT_" + font_name + "_ENABLE=" + font,
            "TREZOR_FONT_" + font_name + '_INCLUDE=\\"' + font_filename + '.h\\"',
        ]
        sourcefile = "embed/lib/fonts/" + font_filename + ".c"
        if sourcefile not in sources:
            sources.append(sourcefile)


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


def _compress(data: bytes) -> bytes:
    z = zlib.compressobj(level=9, wbits=-10)
    return z.compress(data) + z.flush()


def get_bindgen_defines(
    defines: list[str | tuple[str, str]], paths: list[str]
) -> tuple(str, str):
    rest_defs = []
    for d in defines:
        if type(d) is tuple:
            d = f"-D{d[0]}={d[1]}"
        else:
            d = f"-D{d}"
        d = (
            d.replace('\\"', '"')
            .replace("'", "'\"'\"'")
            .replace('"<', "<")
            .replace('>"', ">")
        )
        rest_defs.append(d)
    for d in paths:
        rest_defs.append(f"-I../../{d}")

    return ",".join(rest_defs)


def embed_binary(obj_program, env, section, target_, file):
    _in = f"embedded_{section}.bin.deflated"

    def redefine_sym(name):
        src = (
            "_binary_build_firmware_"
            + _in.replace("/", "_").replace(".", "_")
            + "_"
            + name
        )
        dest = (
            "_binary_"
            + target_.replace("/", "_").replace(".o", "_bin_deflated")
            + "_"
            + name
        )
        return f" --redefine-sym {src}={dest}"

    def compress_action(target, source, env):
        srcf = Path(str(source[0]))
        dstf = Path(str(target[0]))
        compressed = _compress(srcf.read_bytes())
        dstf.write_bytes(compressed)
        return 0

    compress = env.Command(target=_in, source=file, action=compress_action)

    obj_program.extend(
        env.Command(
            target=target_,
            source=_in,
            action="$OBJCOPY -I binary -O elf32-littlearm -B arm"
            f" --rename-section .data=.{section}"
            + redefine_sym("start")
            + redefine_sym("end")
            + redefine_sym("size")
            + " $SOURCE $TARGET",
        )
    )

    env.Depends(obj_program, compress)
