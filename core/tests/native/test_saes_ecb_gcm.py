"""Compare the actual SAES driver with software GCM using an ECB-only HAL model."""

import argparse
import subprocess
import tempfile
from pathlib import Path

from saes_test_hal import HAL_MODEL
from test_saes_key_ready import HEADERS

PROGRAM = (
    HAL_MODEL
    + r"""static void zero_data(const vault_saes_request_t*r){
 for(size_t i=0;i<sizeof(r->data);i++)assert(r->data[i]==0);
}
static void bad(vault_saes_request_t r){
 r.op=VAULT_SAES_OPEN;
 unsigned before=blocks;
 assert(saes_request(&record_key,&r)==VAULT_SAES_AUTH_FAILED);
 /* H and J0 only: no payload counter block before successful authentication. */
 assert(blocks-before==2);
 zero_data(&r);
}
int main(void){
 for(unsigned seed=0;seed<4;seed++){
 for(unsigned i=0;i<32;i++)test_key[i]=seed ? seed+7*i : 0;
 saes_key_drop(&record_key);
 for(size_t n=1;n<=VAULT_SAES_RECORD_SIZE;n++){
  vault_saes_request_t r={.op=VAULT_SAES_SEAL,.length=n};
  for(size_t i=0;i<sizeof(r.iv);i++)r.iv[i]=n+3*i;
  for(size_t i=0;i<sizeof(r.aad);i++)r.aad[i]=1+7*i;
  for(size_t i=0;i<n;i++)r.data[i]=n+19*i;
  uint8_t plaintext[160],expected[160],tag[16];
  memcpy(plaintext,r.data,n);memcpy(expected,r.data,n);
  gcm_ctx software;
  assert(gcm_init_and_key(test_key,32,&software)==RETURN_GOOD);
  assert(gcm_encrypt_message(r.iv,12,r.aad,32,expected,n,tag,16,&software)==RETURN_GOOD);
  assert(saes_request(&record_key,&r)==VAULT_SAES_OK);
  assert(!memcmp(r.data,expected,n) && !memcmp(r.tag,tag,16));
  vault_saes_request_t altered=r;altered.data[n-1]^=1;bad(altered);
  altered=r;altered.iv[0]^=1;bad(altered);
  altered=r;altered.aad[0]^=1;bad(altered);
  altered=r;altered.tag[0]^=1;bad(altered);
  if(n<=3 || n==15 || n==16 || n==17 || n==139 || n==160){
   for(size_t i=0;i<n;i++){altered=r;altered.data[i]^=0x80;bad(altered);}
  }
  altered=r;altered.op=VAULT_SAES_OPEN;
  assert(saes_request(&record_key,&altered)==VAULT_SAES_OK);
  assert(!memcmp(altered.data,plaintext,n));
 }
 }
 vault_saes_request_t r={.op=VAULT_SAES_SEAL,.length=16};
 memset(r.data,0x5a,16);fail_at=blocks+1;
 assert(saes_request(&record_key,&r)==VAULT_SAES_FAILED);zero_data(&r);
 fail_at=0; r=(vault_saes_request_t){.op=VAULT_SAES_SEAL,.length=16};
 assert(saes_request(&record_key,&r)==VAULT_SAES_OK);
 r.op=VAULT_SAES_OPEN;reset_failure_at=resets+2;
 assert(saes_request(&record_key,&r)==VAULT_SAES_FAILED);zero_data(&r);
 puts("SAES ECB-only GCM: four keys, lengths 1..160, independent ciphertext/tag, tamper rejection and block failure passed");
}
"""
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crypto_archive", type=Path)
    parser.add_argument("--driver", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    driver = args.driver or root / "embed/sec/vault_kek/stm32u5/vault_kek.c"
    with tempfile.TemporaryDirectory(prefix="saes-gcm-") as directory:
        work = Path(directory)
        for name, content in HEADERS.items():
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        nested = work / "embed/sec/vault_kek/stm32u5"
        nested.mkdir(parents=True)
        (nested / "driver_under_test.c").write_text(driver.read_text())
        vault = work / "embed/sec/vault"
        vault.mkdir()
        (vault / "keywrap.h").write_text(
            (root / "embed/sec/vault/keywrap.h").read_text()
        )
        (vault / "siv_core.h").write_text(
            (root / "embed/sec/vault/siv_core.h").read_text()
        )
        (vault / "inc/sec").mkdir(parents=True)
        (vault / "inc/sec/vault_mode.h").write_text(
            (root / "embed/sec/vault/inc/sec/vault_mode.h").read_text()
        )
        for name in ("gcm.h", "record_backend.h", "kwp.h", "inc/sec/vault_cipher.h"):
            source = root / "embed/sec/vault" / name
            if not source.exists():
                continue
            path = vault / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source.read_text())
        (work / "test.c").write_text(PROGRAM)
        binary = work / "test"
        subprocess.run(
            [
                "clang",
                "-std=gnu11",
                "-O2",
                "-g",
                "-fsanitize=address,undefined",
                "-DSECURE_MODE",
                "-DVAULT_SEAL_MODE=3",
                "-DPRODUCTION=0",
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
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
