/*
 * Host cross-validation harness for the firmware Merkle root.
 *
 * Compiles the *real* on-device tree math (boot_header_merkle.h) with a host
 * SHA-256 and feeds it the exact manifest + module code produced by the Python
 * signer (tests/fw_merkle/gen_multivariant.py). It then asserts the C computes
 * the same firmware_root as Python and enforces the same accept/reject policy,
 * via the REAL device entry point firmware_verify_manifest.
 *
 * Build:
 *   gcc -I embed/sec/image/stm32 -I ../crypto \
 *       tests/fw_merkle/crossvalidate.c ../crypto/sha2.c -o /tmp/crossvalidate
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sha2.h"

/* --- shims the shared .h expects --------------------------------------- */
typedef uint32_t secbool;
#define sectrue 0xAAAAAAAAU
#define secfalse 0x00000000U

#define IMAGE_HASH_DIGEST_LENGTH 32
#define IMAGE_HASH_CTX SHA256_CTX
#define IMAGE_HASH_INIT(ctx) sha256_Init(ctx)
#define IMAGE_HASH_UPDATE(ctx, data, len) sha256_Update(ctx, data, len)
#define IMAGE_HASH_FINAL(ctx, out) sha256_Final(ctx, out)

typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

#define BOOT_HEADER_MAX_MODULES 8
#define FW_MODULE_SECMON 1
#define FW_MODULE_APP 2
#define FW_MODULE_PRODTEST 3
#define FW_VARIANT_NONE 0
#define FW_VARIANT_UNIVERSAL 2
#define FW_VARIANT_BITCOIN_ONLY 3
#define FW_VARIANT_PRODTEST 4
#define FW_TYPE_VARIANT_MASK 0x7F
#define FW_TYPE_CUSTOM_FLAG 0x80

#define FW_MANIFEST_MAGIC 0x445A5254 /* 'TRZD' */

typedef struct __attribute__((packed)) {
  uint32_t module_type;
  uint32_t flags;
  uint32_t addr;
  uint32_t size;
  merkle_proof_node_t code_hash; /* single SHA-256 over the whole module code */
} firmware_manifest_entry_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint32_t firmware_variant;
  uint8_t firmware_version[4];
  merkle_proof_node_t app_root;
  merkle_proof_node_t translations_root;
  uint32_t module_count;
  firmware_manifest_entry_t entries[];
} firmware_manifest_t;

static inline size_t firmware_manifest_size(const firmware_manifest_t *m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/* the real on-device algorithm, verbatim (we supply the shims above) */
#define BOOT_HEADER_MERKLE_SHIMMED
#include "boot_header_merkle.h"

/* --- harness ----------------------------------------------------------- */
static void print_hex(const char *label, const uint8_t *b, size_t n) {
  printf("%s", label);
  for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
  printf("\n");
}

/* Manifest-based multi-variant vector (FWM2): each variant is a full firmware
 * image [manifest | module code...], the variant leaf is H(0x00 || manifest),
 * and a real proof folds it to the founder firmware_root. Replays the REAL
 * device firmware_verify_manifest (authenticity fold + per-entry code_hash).
 * Layout: "FWM2" | founder_root(32) | variant_count(u32), then per variant:
 *   variant_id(u32) | image_len(u32) | image | manifest_len(u32) |
 *   proof_count(u32) | proof_node(32)... */
static int run_manifest(const uint8_t *buf) {
  const uint8_t *p = buf + 4; /* skip "FWM2" */
  const uint8_t *founder_root = p;
  p += 32;
  uint32_t variant_count;
  memcpy(&variant_count, p, 4);
  p += 4;

  print_hex("founder firmware_root  : ", founder_root, 32);

  merkle_proof_node_t trusted;
  memcpy(trusted.bytes, founder_root, 32);
  const char *names[] = {"none", "custom",       "universal",
                         "bitcoin-only", "prodtest", "CA"};

  int ok = 1;
  for (uint32_t v = 0; v < variant_count; v++) {
    uint32_t variant_id, image_len, manifest_len, proof_count;
    memcpy(&variant_id, p, 4);
    p += 4;
    memcpy(&image_len, p, 4);
    p += 4;
    uint8_t *image = (uint8_t *)p; /* mutable, for the tamper tests */
    p += image_len;
    memcpy(&manifest_len, p, 4);
    p += 4;
    memcpy(&proof_count, p, 4);
    p += 4;
    merkle_proof_node_t proof[32];
    if (proof_count > 32) {
      fprintf(stderr, "proof too long %u\n", proof_count);
      return 2;
    }
    for (uint32_t i = 0; i < proof_count; i++) {
      memcpy(proof[i].bytes, p, 32);
      p += 32;
    }

    const firmware_manifest_t *manifest = (const firmware_manifest_t *)image;
    uintptr_t base = (uintptr_t)image;

    /* Locate the secmon and app module code (for the tamper tests). */
    uint32_t secmon_addr = 0, app_addr = 0, app_size = 0;
    for (uint32_t i = 0; i < manifest->module_count; i++) {
      const firmware_manifest_entry_t *e = &manifest->entries[i];
      if (e->module_type == FW_MODULE_SECMON) secmon_addr = e->addr;
      if (e->module_type == FW_MODULE_APP) {
        app_addr = e->addr;
        app_size = e->size;
      }
    }

    /* 1) full verify (official): variant leaf folds + per-entry code integrity.
     *    Custom mode must ALSO accept an official image (superset acceptance). */
    secbool r = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                         proof_count, &trusted, secfalse);
    secbool rc = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted, sectrue);
    int verify_ok = (r == sectrue) && (rc == sectrue);

    /* 2) tamper an APP code byte. Official (secfalse) must REJECT (code_hash
     *    mismatch). Custom (sectrue) must ACCEPT: the app may deviate from the
     *    founder manifest -- its code_hash is not enforced. */
    int tamper_app_ok = 1;
    if (app_size > 0) {
      image[app_addr + app_size - 1] ^= 0xFF;
      secbool r2 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted, secfalse);
      secbool r2c = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                             proof_count, &trusted, sectrue);
      tamper_app_ok = (r2 == secfalse) && (r2c == sectrue);
      image[app_addr + app_size - 1] ^= 0xFF;
    }

    /* 3) tamper a SECMON code byte. BOTH modes must REJECT: the secure monitor
     *    is always founder-bound, even for a custom install. */
    image[secmon_addr] ^= 0xFF;
    secbool r3 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted, secfalse);
    secbool r3c = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                           proof_count, &trusted, sectrue);
    int tamper_secmon_ok = (r3 == secfalse) && (r3c == secfalse);
    image[secmon_addr] ^= 0xFF;

    /* 4) tamper a proof node -> authenticity must fail (both modes). */
    int tamper_proof_ok = 1;
    if (proof_count > 0) {
      proof[0].bytes[0] ^= 0xFF;
      secbool r4 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted, secfalse);
      tamper_proof_ok = (r4 == secfalse);
      proof[0].bytes[0] ^= 0xFF;
    }

    printf(
        "  variant %u (%-12s): verify %s, tamper-app %s, tamper-secmon %s, "
        "tamper-proof %s\n",
        variant_id, variant_id < 6 ? names[variant_id] : "?",
        verify_ok ? "OK" : "FAIL",
        tamper_app_ok ? "policy OK" : "WRONG (bug!)",
        tamper_secmon_ok ? "rejected OK" : "ACCEPTED (bug!)",
        tamper_proof_ok ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= verify_ok & tamper_app_ok & tamper_secmon_ok & tamper_proof_ok;
  }

  /* firmware_type = variant + trust class (both storage axes). The variant is
   * authenticated in the manifest; exercise the compose/extract helpers here. */
  {
    uint32_t variant = FW_VARIANT_UNIVERSAL;
    uint8_t ft_official = firmware_type_compose(variant, secfalse);
    uint8_t ft_custom = firmware_type_compose(variant, sectrue);
    int h_ok = firmware_type_variant(ft_official) == variant &&
               firmware_type_is_custom(ft_official) == secfalse &&
               firmware_type_variant(ft_custom) == variant &&
               firmware_type_is_custom(ft_custom) == sectrue &&
               ft_official != ft_custom;
    printf("  firmware_type          : official=0x%02x custom=0x%02x -> %s\n",
           ft_official, ft_custom, h_ok ? "OK" : "FAIL");
    ok &= h_ok;
  }

  printf("\nRESULT: %s\n", ok ? "C matches Python  OK" : "MISMATCH");
  return ok ? 0 : 1;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <vector-file>\n", argv[0]);
    return 2;
  }
  FILE *f = fopen(argv[1], "rb");
  if (!f) {
    perror("open vector");
    return 2;
  }
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  uint8_t *buf = malloc(sz);
  if (fread(buf, 1, sz, f) != (size_t)sz) {
    fprintf(stderr, "short read\n");
    return 2;
  }
  fclose(f);

  /* Manifest-based multi-variant vector. */
  if (sz >= 4 && memcmp(buf, "FWM2", 4) == 0) {
    int r = run_manifest(buf);
    free(buf);
    return r;
  }

  fprintf(stderr, "bad magic (expected FWM2)\n");
  free(buf);
  return 2;
}
