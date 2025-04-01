from __future__ import annotations

import shlex
import subprocess
import zlib
from pathlib import Path

HERE = Path(__file__).parent.resolve()

# go up from site_scons to core/
PROJECT_ROOT = HERE.parent.resolve()


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
        subprocess.check_output(["git", "rev-parse", "--verify", "HEAD"])
        .decode("ascii")
        .strip()[:7]
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
            val = d[1].replace('"', '\\"').replace("(", "\\(").replace(")", "\\)")
            result.append(f'{d[0]}="{val}"')
        else:
            result.append(d)
    return result


def _compress(data: bytes) -> bytes:
    z = zlib.compressobj(level=9, wbits=-10)
    return z.compress(data) + z.flush()


def get_bindgen_defines(defines: list[str | tuple[str, str]], paths: list[str]) -> str:
    rest_defs = []
    for d in defines:
        if type(d) is tuple:
            d = f"-D{d[0]}={d[1]}"
        else:
            d = f"-D{d}"
        rest_defs.append(d)
    for d in paths:
        rest_defs.append(f"-I../../{d}")

    return ",".join(rest_defs)


def embed_compressed_binary(obj_program, env, section, target_, file, build, symbol):
    _in = f"embedded_{section}.bin.deflated"

    def redefine_sym(suffix):
        src = (
            f"_binary_build_{build}_"
            + _in.replace("/", "_").replace(".", "_")
            + "_"
            + suffix
        )
        dest = f"_deflated_{symbol}_{suffix}"
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


def embed_raw_binary(obj_program, env, section, target_, file):
    obj_program.extend(
        env.Command(
            target=target_,
            source=file,
            action="$OBJCOPY -I binary -O elf32-littlearm -B arm"
            f" --rename-section .data=.{section}" + " $SOURCE $TARGET",
        )
    )


def add_rust_lib(*, env, build, profile, features, all_paths, build_dir):
    RUST_LIB = "trezor_lib"
    RUST_TARGET = env.get("ENV")["RUST_TARGET"]

    # Determine the profile build flags.
    if profile == "release":
        profile = "--release"
        RUST_LIBDIR = f"build/{build}/rust/{RUST_TARGET}/release"
    else:
        profile = ""
        RUST_LIBDIR = f"build/{build}/rust/{RUST_TARGET}/debug"
    RUST_LIBPATH = f"{RUST_LIBDIR}/lib{RUST_LIB}.a"

    def cargo_build():
        lib_features = []
        lib_features.extend(features)
        lib_features.append("ui")

        cargo_opts = [
            f"--target={RUST_TARGET}",
            f"--target-dir=../../build/{build}/rust",
            "--no-default-features",
            "--features " + ",".join(lib_features),
            "-Z build-std=core",
            "-Z build-std-features=panic_immediate_abort",
        ]
        build_cmd = f"cargo build {profile} " + " ".join(cargo_opts)

        unstable_rustc_flags = [
            # see https://nnethercote.github.io/perf-book/type-sizes.html#measuring-type-sizes for more details
            "print-type-sizes",
            # Adds an ELF section with Rust functions' stack sizes. See the following links for more details:
            # - https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/emit-stack-sizes.html
            # - https://blog.japaric.io/stack-analysis/
            # - https://github.com/japaric/stack-sizes/
            "emit-stack-sizes",
        ]

        env.Append(ENV={"RUSTFLAGS": " ".join(f"-Z {f}" for f in unstable_rustc_flags)})

        bindgen_macros = get_bindgen_defines(env.get("CPPDEFINES"), all_paths)

        return (
            f"export BINDGEN_MACROS={shlex.quote(bindgen_macros)}; "
            f"export BUILD_DIR='{build_dir}'; "
            f"cd embed/rust; {build_cmd} > {build_dir}/rust-type-sizes.log"
        )

    rust = env.Command(
        target=RUST_LIBPATH,
        source="",
        action=cargo_build(),
    )

    env.Append(LINKFLAGS=[f"-L{RUST_LIBDIR}"])
    env.Append(LINKFLAGS=[f"-l{RUST_LIB}"])

    return rust
