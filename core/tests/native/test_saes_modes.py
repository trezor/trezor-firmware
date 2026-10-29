"""Check the actual SAES driver against independent GCM vectors."""

import argparse
import subprocess
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from saes_test_hal import HAL_MODEL
from test_saes_key_ready import HEADERS

PROGRAM = (
    HAL_MODEL
    + '\n#include "vectors.h"\n\nstatic void zero_data(const vault_saes_request_t*r){\n for(size_t i=0;i<sizeof(r->data);i++)assert(!r->data[i]);\n}\nstatic void install(saes_key_t *slot,const uint8_t *key){\n for(unsigned i=0;i<8;i++)slot->wrapped[i]=saes_be32(key+4*i);\n slot->ready=true;\n}\nstatic void check_bad(vault_saes_request_t r){\n r.op=VAULT_SAES_OPEN;\n assert(vault_saes_record(&r)==VAULT_SAES_AUTH_FAILED);zero_data(&r);\n}\nint main(void){\n distinct_rng=true;\n assert(saes_known_answer());\n for(size_t v=0;v<sizeof(vectors)/sizeof(vectors[0]);v++){\n  const vector_t *vector=&vectors[v];unsigned n=vector->length;\n  uint8_t key[64],plain[160];\n  for(unsigned i=0;i<64;i++)key[i]=vector->seed+7*i;\n  install(&record_key,key);\n  vault_saes_request_t r={.op=VAULT_SAES_SEAL,.length=n};\n  for(unsigned i=0;i<12;i++)r.iv[i]=n+3*i;\n  for(unsigned i=0;i<32;i++)r.aad[i]=1+7*i;\n  for(unsigned i=0;i<n;i++)plain[i]=r.data[i]=n+19*i;\n  assert(vault_saes_record(&r)==VAULT_SAES_OK);\n  assert(!memcmp(r.data,vector->ciphertext,n));\n  assert(!memcmp(r.tag,vector->tag,VAULT_TAG_SIZE));\n  vault_saes_request_t bad=r;bad.data[n-1]^=1;check_bad(bad);\n  bad=r;bad.aad[0]^=1;check_bad(bad);\n  for(unsigned i=0;i<VAULT_TAG_SIZE;i++){bad=r;bad.tag[i]^=1;check_bad(bad);}\n  bad=r;bad.iv[0]^=1;check_bad(bad);\n  r.op=VAULT_SAES_OPEN;assert(vault_saes_record(&r)==VAULT_SAES_OK);\n  assert(!memcmp(r.data,plain,n));\n  // Internal errors, including the final reset, never release output.\n  r.op=VAULT_SAES_SEAL;fail_at=blocks+1;\n  assert(vault_saes_record(&r)==VAULT_SAES_FAILED);zero_data(&r);fail_at=0;\n }\n vault_saes_request_t r={.op=VAULT_SAES_RESET};\n assert(vault_saes_record(&r)==VAULT_SAES_OK && !record_key.ready);\n r=(vault_saes_request_t){.op=VAULT_SAES_SEAL,.length=32};\n assert(vault_saes_record(&r)==VAULT_SAES_OK);\n r.op=VAULT_SAES_OPEN;reset_failure_at=resets+2;\n assert(vault_saes_record(&r)==VAULT_SAES_FAILED);zero_data(&r);reset_failure_at=0;\n r=(vault_saes_request_t){.op=VAULT_SAES_SEAL,.length=161};\n assert(vault_saes_record(&r)==VAULT_SAES_FAILED);zero_data(&r);\n // Storage cache stays authenticated GCM even in ECB/SIV record builds.\n r=(vault_saes_request_t){.op=VAULT_SAES_SEAL,.length=48};\n assert(vault_saes_storage(&r)==VAULT_SAES_OK);\n r.op=VAULT_SAES_OPEN;r.tag[0]^=1;\n assert(vault_saes_storage(&r)==VAULT_SAES_AUTH_FAILED);zero_data(&r);\n puts("SAES mode: independent vectors, tampering, distinct keys, reset and failures passed");\n}\n'
)


def values(data):
    return "{" + ",".join((str(x) for x in data)) + "}"


def vectors(mode):
    rows = []
    for seed in range(4):
        key = bytes(((seed + 7 * i) % 256 for i in range(64)))
        for length in range(1, 161):
            if mode == "ecb" and length % 16 or (mode == "kw" and length % 8):
                continue
            plain = bytes(((length + 19 * i) % 256 for i in range(length)))
            aad = bytes(((1 + 7 * i) % 256 for i in range(32)))
            iv = bytes(((length + 3 * i) % 256 for i in range(12)))
            result = AESGCM(key[:32]).encrypt(iv, plain, aad)
            ciphertext, tag = (result[:-16], result[-16:])
            rows.append(
                f"{{{seed},{length},{values(ciphertext)},{values(tag or bytes(16))}}}"
            )
    return (
        "typedef struct {unsigned seed,length;uint8_t ciphertext[160],tag[40];} vector_t;\nstatic const vector_t vectors[]={"
        + ",\n".join(rows)
        + "};\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crypto_archive", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="saes-modes-") as directory:
        work = Path(directory)
        for name, content in HEADERS.items():
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        nested = work / "embed/sec/vault_kek/stm32u5"
        nested.mkdir(parents=True)
        (nested / "driver_under_test.c").write_text(
            (root / "embed/sec/vault_kek/stm32u5/vault_kek.c").read_text()
        )
        vault = work / "embed/sec/vault"
        for name in ("keywrap.h", "kwp.h", "siv_core.h", "inc/sec/vault_mode.h"):
            path = vault / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text((root / "embed/sec/vault" / name).read_text())
        for name in ("gcm.h", "record_backend.h", "kwp.h", "inc/sec/vault_cipher.h"):
            path = vault / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text((root / "embed/sec/vault" / name).read_text())
        (work / "test.c").write_text(PROGRAM)
        for mode, selection in (("kw", 4), ("siv", 1), ("ecb", 2), ("gcm", 3)):
            (work / "vectors.h").write_text(vectors(mode))
            binary = work / mode
            subprocess.run(
                [
                    "clang",
                    "-std=gnu11",
                    "-O2",
                    "-g",
                    "-fsanitize=address,undefined",
                    "-DSECURE_MODE",
                    "-DPRODUCTION=0",
                    f"-DVAULT_SEAL_MODE={selection}",
                    "-ffunction-sections",
                    "-Wl,--gc-sections",
                    "-I",
                    str(work),
                    "-I",
                    str(nested),
                    "-I",
                    str(root / "embed/sec/vault_kek/inc"),
                    "-I",
                    str(vault / "inc"),
                    "-I",
                    str(root.parent / "crypto"),
                    str(work / "test.c"),
                    str(args.crypto_archive),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            print(f"SAES {mode}", flush=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
