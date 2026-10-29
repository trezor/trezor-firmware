"""Run native vault tests using a built emulator's crypto archive (inside Nix)."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def find_crypto():
    host = next(
        (
            line.split(": ", 1)[1]
            for line in subprocess.check_output(
                ["rustc", "-vV"], text=True
            ).splitlines()
            if line.startswith("host: ")
        )
    )
    roots = [
        ROOT / "core/build" / host / "debug/build",
        ROOT / "core/build/debug/build",
    ]
    for root in roots:
        candidates = sorted(
            root.glob("crypto-*/out/libcrypto.a"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            names = subprocess.check_output(
                ["nm", "--defined-only", candidate], text=True
            )
            if " gcm_init_and_key\n" in names and " zkp_context_init\n" in names:
                return candidate
    raise SystemExit(
        "Build the emulator first: xtask build firmware --emulator -m T3T1 -p test-live --btc-only"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crypto-archive", type=Path)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--mode", choices=("gcm",), action="append")
    args = parser.parse_args()
    archive = args.crypto_archive or find_crypto()
    print(f"Crypto archive: {archive}", flush=True)
    flags = [
        "-std=gnu11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-DUSE_BIP32_CACHE=0",
        "-DUSE_BIP39_CACHE=0",
        "-DBITCOIN_ONLY=1",
        "-Icrypto",
        "-Icore",
        "-Icore/embed/sec/vault/inc",
    ]
    compiler = "clang" if args.sanitize else "cc"
    if args.sanitize:
        flags += ["-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    with tempfile.TemporaryDirectory(prefix="vault-native-") as output:
        suite = json.loads(
            (
                ROOT / "crypto/tests/wycheproof/testvectors_v1/aes_siv_cmac_test.json"
            ).read_text()
        )
        vectors = [
            t for g in suite["testGroups"] if g["keySize"] == 512 for t in g["tests"]
        ]
        header = Path(output) / "vault_siv_vectors.h"
        rows = []
        for t in vectors:
            assert len(t["msg"]) <= 256 and len(t["aad"]) <= 128
            fields = [json.dumps(t[k]) for k in ("key", "aad", "msg", "ct")]
            fields.append("true" if t["result"] == "valid" else "false")
            rows.append("{" + ",".join(fields) + "}")
        header.write_text(
            "typedef struct {const char *key, *aad, *message, *ciphertext; bool valid;} vector_t;\nstatic const vector_t vectors[] = {"
            + ",\n".join(rows)
            + "};\n"
        )
        for unrolled in (False, True):
            binary = str(Path(output) / f"sha2-erasure-{unrolled}")
            subprocess.run(
                [
                    compiler,
                    *flags,
                    *(["-DSHA2_UNROLL_TRANSFORM"] if unrolled else []),
                    "core/tests/native/test_sha2_erasure.c",
                    "crypto/memzero.c",
                    "-o",
                    binary,
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([binary], cwd=ROOT, check=True)
        for mode in args.mode or ("gcm",):
            selection = {"gcm": 3}[mode]
            print(f"Vault mode: {mode}", flush=True)
            names = [
                "test_vault_sealing",
                "test_vault_bytes",
                "test_vault_coreapp",
                "test_vault_slip21",
            ]
            if True:
                names += ["test_ed25519_cleanup"]
            for name in names:
                inputs = [
                    f"core/tests/native/{name}.c",
                    "crypto/slip21.c",
                    str(archive),
                ]
                if name == "test_ecdsa_cleanup":
                    inputs += [
                        f"-Wl,--wrap={symbol}"
                        for symbol in ("memzero", "init_rfc6979", "generate_k_rfc6979")
                    ]
                if name == "test_ed25519_keys":
                    inputs += [
                        "-Wl,--wrap=ed25519_sign",
                        "-Wl,--wrap=ed25519_sign_keccak",
                    ]
                binary = str(Path(output) / f"{name}-{mode}")
                subprocess.run(
                    [
                        compiler,
                        *flags,
                        "-I" + output,
                        f"-DVAULT_SEAL_MODE={selection}",
                        *inputs,
                        "-o",
                        binary,
                    ],
                    cwd=ROOT,
                    check=True,
                )
                subprocess.run([binary], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
