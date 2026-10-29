"""Exercise hardware-key readiness in the actual SAES driver with mocked registers."""

import subprocess
import sys
import tempfile
from pathlib import Path

HEADERS = {
    "trezor_bsp.h": """#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#define ensure_true(e,m) assert(e)
typedef struct { volatile uint32_t SR,ISR; } AES_TypeDef;
extern AES_TypeDef fake_saes;
#define SAES (&fake_saes)
#define AES_SR_BUSY 1u
#define AES_SR_KEYVALID 2u
#define AES_ISR_KEIF 4u
#define AES_ISR_RNGEIF 8u
#define CRYP_NO_SWAP 0u
#define CRYP_KEYSIZE_256B 0u
#define CRYP_DATAWIDTHUNIT_BYTE 0u
#define CRYP_HEADERWIDTHUNIT_BYTE 0u
#define CRYP_KEYIVCONFIG_ALWAYS 0u
#define CRYP_KEYNOCONFIG 1u
#define CRYP_KEYMODE_WRAPPED 1u
#define CRYP_KEYMODE_NORMAL 0u
#define CRYP_KEYSEL_HW 1u
#define CRYP_KEYSEL_NORMAL 0u
#define CRYP_AES_ECB 0u
#define CRYP_AES_GCM_GMAC 1u
#define HAL_CRYP_ERROR_KEY 1u
#define HAL_CRYP_ERROR_RNG 2u
#define HAL_CRYP_ERROR_TIMEOUT 4u
#define HAL_OK 0
#define HAL_ERROR 1
typedef struct {
 uint32_t DataType,KeySize,KeySelect,KeyMode,Algorithm,DataWidthUnit;
 uint32_t HeaderWidthUnit,KeyIVConfigSkip,HeaderSize;
 uint32_t *pKey,*pInitVect,*Header;
} CRYP_ConfigTypeDef;
typedef struct {
 AES_TypeDef *Instance; CRYP_ConfigTypeDef Init; uint32_t ErrorCode;
} CRYP_HandleTypeDef;
int HAL_CRYP_Init(CRYP_HandleTypeDef*);
int HAL_CRYP_GetConfig(CRYP_HandleTypeDef*,CRYP_ConfigTypeDef*);
int HAL_CRYP_SetConfig(CRYP_HandleTypeDef*,CRYP_ConfigTypeDef*);
int HAL_CRYPEx_WrapKey(CRYP_HandleTypeDef*,uint32_t*,uint32_t*,uint32_t);
int HAL_CRYPEx_UnwrapKey(CRYP_HandleTypeDef*,uint32_t*,uint32_t);
int HAL_CRYP_Encrypt(CRYP_HandleTypeDef*,uint32_t*,uint32_t,uint32_t*,uint32_t);
int HAL_CRYP_Decrypt(CRYP_HandleTypeDef*,uint32_t*,uint32_t,uint32_t*,uint32_t);
int HAL_CRYPEx_AESGCM_GenerateAuthTAG(CRYP_HandleTypeDef*,uint32_t*,uint32_t);
""",
    "trezor_types.h": """#pragma once
#include <stdint.h>
typedef uint32_t secbool;
#define sectrue 0xAAAAAAAAu
#define secfalse 0u
""",
    "sec/rng_strong.h": """void rng_fill_buffer_strong(void*,size_t);
""",
    "sec/secure_aes.h": """#include <trezor_types.h>
#define SECURE_AES_KEY_BHK 2
secbool secure_aes_init(void);
secbool secure_aes_ecb_encrypt_hw(const uint8_t*,size_t,uint8_t*,int);
secbool secure_aes_ecb_decrypt_hw(const uint8_t*,size_t,uint8_t*,int);
""",
    "sys/systick.h": """uint32_t ticks_timeout(uint32_t);
bool ticks_expired(uint32_t);
""",
}

PROGRAM = r"""#include <trezor_bsp.h>
#include <stdio.h>
#include "driver_under_test.c"
AES_TypeDef fake_saes;
static uint32_t ticks, initial_error;
static bool never_ready, init_fails;
int HAL_CRYP_Init(CRYP_HandleTypeDef*h){
 fake_saes.SR=AES_SR_BUSY; fake_saes.ISR=initial_error;
 return init_fails ? HAL_ERROR : HAL_OK;
}
uint32_t ticks_timeout(uint32_t delay){return ticks+delay;}
bool ticks_expired(uint32_t deadline){
 ++ticks;
 if(!never_ready && ticks==3) fake_saes.SR=AES_SR_KEYVALID;
 return ticks>=deadline;
}
static void reset(void){
 ticks=initial_error=0; never_ready=init_fails=false;
}
int main(void){
 CRYP_HandleTypeDef h;
 reset(); assert(saes_setup(&h,1,1,0));
 assert(ticks==3 && fake_saes.SR==AES_SR_KEYVALID);
 reset(); initial_error=AES_ISR_KEIF; assert(!saes_setup(&h,1,1,0));
 assert(h.ErrorCode & HAL_CRYP_ERROR_KEY);
 reset(); initial_error=AES_ISR_RNGEIF; assert(!saes_setup(&h,1,1,0));
 assert(h.ErrorCode & HAL_CRYP_ERROR_RNG);
 reset(); never_ready=true; assert(!saes_setup(&h,1,1,0));
 assert(ticks==SAES_TIMEOUT && (h.ErrorCode & HAL_CRYP_ERROR_TIMEOUT));
 reset(); init_fails=true; assert(!saes_setup(&h,1,1,0)); assert(ticks==0);
 puts("SAES delayed readiness, key/RNG errors, timeout and Init failure passed");
}
"""


def main():
    root = Path(__file__).resolve().parents[2]
    driver = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else root / "embed/sec/vault_kek/stm32u5/vault_kek.c"
    )
    with tempfile.TemporaryDirectory(prefix="saes-readiness-") as directory:
        work = Path(directory)
        for name, content in HEADERS.items():
            path = work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Keep the driver's relative include valid without changing its source.
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
                "cc",
                "-DSECURE_MODE",
                "-DVAULT_SEAL_MODE=3",
                "-DPRODUCTION=1",
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
                "-o",
                str(binary),
            ],
            check=True,
        )
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
