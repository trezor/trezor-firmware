/*
 * Host cross-validation harness for the firmware Merkle root.
 *
 * Compiles the *real* on-device tree math (boot_header_merkle.inc) with a host
 * SHA-256 and feeds it the exact module headers produced by the Python signer
 * (tools/trezor_core_tools/firmware_pq_sign.py --vector-out). It then asserts
 * the C computes the same firmware_root as Python, via both code paths:
 *   Case A: calc_firmware_root(all modules, no proof)      -- subtree build
 *   Case B: calc_firmware_root(module[0], proof=[leaf(1)]) -- proof fold
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

/* --- shims the shared .inc expects ------------------------------------- */
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
#define FW_MODULE_MAGIC 0x4D5A5254
#define FW_MODULE_SECMON 1
#define FW_MODULE_APP 2
#define FW_VARIANT_NONE 0
#define FW_VARIANT_UNIVERSAL 2
#define FW_VARIANT_BITCOIN_ONLY 3
#define FW_VARIANT_PRODTEST 4
#define FW_TYPE_VARIANT_MASK 0x7F
#define FW_TYPE_CUSTOM_FLAG 0x80

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint32_t hw_model;
  uint32_t module_type;
  /* no firmware_variant: the variant is authenticated in the manifest */
  uint8_t version[4];
  uint32_t code_size;
  merkle_proof_node_t code_hash; /* single SHA-256 over the whole module code */
} firmware_module_header_t;

static inline size_t firmware_module_header_size(
    const firmware_module_header_t *hdr) {
  (void)hdr;
  return sizeof(firmware_module_header_t);
}

typedef struct {
  const firmware_module_header_t *hdr;
  uintptr_t code_address;
} boot_header_module_t;

#define FW_MODULE_HEADER_REGION 0x400
#define FW_MANIFEST_MAGIC 0x445A5254 /* 'TRZD' */

typedef struct __attribute__((packed)) {
  uint32_t module_type;
  uint32_t flags;
  uint32_t addr;
  uint32_t size;
  merkle_proof_node_t header_hash;
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

/* Multi-variant firmware_root vector (FWMV): the founder tree spans several
 * variants, and each variant carries a real proof (co-path) to the shared
 * founder firmware_root. Proves the device fold matches Python for the actual
 * multi-variant scheme (not just the single-variant / synthetic-sibling case).
 * Layout: "FWMV" | founder_root(32) | variant_count(u32) then per variant:
 *   variant_id(u32) | module_count(u32) | [hdr_len(u32)|hdr]... |
 *   proof_count(u32) | [proof_node(32)]...
 * Code is NOT included (the proof/header math is code-independent). */
static int run_multivariant(const uint8_t *buf) {
  const uint8_t *p = buf + 4;  /* skip "FWMV" */
  const uint8_t *founder_root = p;
  p += 32;
  uint32_t variant_count;
  memcpy(&variant_count, p, 4);
  p += 4;

  print_hex("founder firmware_root  : ", founder_root, 32);

  merkle_proof_node_t trusted;
  memcpy(trusted.bytes, founder_root, 32);
  const uint32_t roles[2] = {FW_MODULE_SECMON, FW_MODULE_APP};
  const char *names[] = {"none", "custom",       "universal",
                         "bitcoin-only", "prodtest", "CA"};

  int ok = 1;
  for (uint32_t v = 0; v < variant_count; v++) {
    uint32_t variant_id, module_count;
    memcpy(&variant_id, p, 4);
    p += 4;
    memcpy(&module_count, p, 4);
    p += 4;
    if (module_count == 0 || module_count > BOOT_HEADER_MAX_MODULES) {
      fprintf(stderr, "bad module_count %u\n", module_count);
      return 2;
    }

    boot_header_module_t modules[BOOT_HEADER_MAX_MODULES] = {0};
    for (uint32_t i = 0; i < module_count; i++) {
      uint32_t hdr_len;
      memcpy(&hdr_len, p, 4);
      p += 4;
      modules[i].hdr = (const firmware_module_header_t *)p;
      p += hdr_len;
      modules[i].code_address = 0;  /* code not present in FWMV */
    }

    uint32_t proof_count;
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

    /* 1) fold: variant_root (built from modules) + proof == founder_root */
    merkle_proof_node_t root;
    boot_header_calc_firmware_root(modules, module_count, proof, proof_count,
                                   &root);
    int fold_ok = memcmp(root.bytes, founder_root, 32) == 0;

    /* 2) firmware_verify_headers with the real proof + trusted founder root */
    secbool vh = firmware_verify_headers(modules, module_count, roles, proof,
                                         proof_count, &trusted);
    int vh_ok = (vh == sectrue);

    /* 3) tamper a proof node -> the fold must no longer reach the root */
    int tamper_ok = 1;
    if (proof_count > 0) {
      proof[0].bytes[0] ^= 0xFF;
      secbool vh2 = firmware_verify_headers(modules, module_count, roles, proof,
                                            proof_count, &trusted);
      tamper_ok = (vh2 == secfalse);
      proof[0].bytes[0] ^= 0xFF;
    }

    printf("  variant %u (%-12s): fold %s, verify_headers %s, tamper %s\n",
           variant_id, variant_id < 6 ? names[variant_id] : "?",
           fold_ok ? "MATCH" : "MISMATCH", vh_ok ? "OK" : "FAIL",
           tamper_ok ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= fold_ok & vh_ok & tamper_ok;
  }

  printf("\nRESULT: %s\n", ok ? "C matches Python  OK" : "MISMATCH");
  return ok ? 0 : 1;
}

/* Manifest-based multi-variant vector (FWM2): each variant is a full firmware
 * image [manifest | modules], the variant leaf is H(0x00 || manifest), and a
 * real proof folds it to the founder firmware_root. Replays the REAL device
 * firmware_verify_manifest (authenticity fold + per-module header_hash + code).
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
    uint8_t *image = (uint8_t *)p; /* mutable, for the tamper test */
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

    /* 1) full verify (official): variant leaf folds + module integrity. Also
     *    custom mode must ACCEPT an official image (it's a superset acceptance). */
    secbool r = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                         proof_count, &trusted, secfalse);
    secbool rc = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted, sectrue);
    int verify_ok = (r == sectrue) && (rc == sectrue);

    /* 2) tamper a code byte -> integrity must fail. The last module's code sits
     *    at the end of the image (addr + header region); flip the final byte.
     *    Custom mode must ALSO reject it: it drops the manifest header-hash bind
     *    but still checks code self-consistency, so a code tamper still fails. */
    image[image_len - 1] ^= 0xFF;
    secbool r2 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted, secfalse);
    secbool r2c = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                           proof_count, &trusted, sectrue);
    int tamper_code_ok = (r2 == secfalse) && (r2c == secfalse);
    image[image_len - 1] ^= 0xFF;

    /* 3) tamper a proof node -> authenticity must fail. */
    int tamper_proof_ok = 1;
    if (proof_count > 0) {
      proof[0].bytes[0] ^= 0xFF;
      secbool r3 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted, secfalse);
      tamper_proof_ok = (r3 == secfalse);
      proof[0].bytes[0] ^= 0xFF;
    }

    printf("  variant %u (%-12s): verify %s, tamper-code %s, tamper-proof %s\n",
           variant_id, variant_id < 6 ? names[variant_id] : "?",
           verify_ok ? "OK" : "FAIL",
           tamper_code_ok ? "rejected OK" : "ACCEPTED (bug!)",
           tamper_proof_ok ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= verify_ok & tamper_code_ok & tamper_proof_ok;
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

  /* Legacy subtree multi-variant vector -> the founder-tree/proof runner. */
  if (sz >= 4 && memcmp(buf, "FWMV", 4) == 0) {
    int r = run_multivariant(buf);
    free(buf);
    return r;
  }

  const uint8_t *p = buf;
  if (memcmp(p, "FWXV", 4) != 0) {
    fprintf(stderr, "bad magic\n");
    return 2;
  }
  p += 4;
  const uint8_t *expected_root = p;
  p += 32;
  uint32_t module_count;
  memcpy(&module_count, p, 4);
  p += 4;
  if (module_count == 0 || module_count > BOOT_HEADER_MAX_MODULES) {
    fprintf(stderr, "bad module_count %u\n", module_count);
    return 2;
  }

  boot_header_module_t modules[BOOT_HEADER_MAX_MODULES] = {0};
  uint8_t *code_ptr[BOOT_HEADER_MAX_MODULES] = {0};
  uint32_t code_len[BOOT_HEADER_MAX_MODULES] = {0};
  for (uint32_t i = 0; i < module_count; i++) {
    uint32_t hdr_len;
    memcpy(&hdr_len, p, 4);
    p += 4;
    modules[i].hdr = (const firmware_module_header_t *)p;
    p += hdr_len;
    uint32_t clen;
    memcpy(&clen, p, 4);
    p += 4;
    code_ptr[i] = (uint8_t *)p;
    code_len[i] = clen;
    modules[i].code_address = (uintptr_t)p;
    p += clen;
  }

  print_hex("expected firmware_root : ", expected_root, 32);

  int ok = 1;

  /* Case A: build the whole subtree from all modules, no proof. */
  merkle_proof_node_t root_a;
  boot_header_calc_firmware_root(modules, module_count, NULL, 0, &root_a);
  int a_ok = memcmp(root_a.bytes, expected_root, 32) == 0;
  print_hex("  A) subtree build     : ", root_a.bytes, 32);
  printf("     -> %s\n", a_ok ? "MATCH" : "MISMATCH");
  ok &= a_ok;

  /* Case B: one module + proof = leaf(other module). Exercises the fold path.
     Only meaningful for a 2-module firmware. */
  if (module_count == 2) {
    merkle_proof_node_t sibling;
    boot_header_module_leaf(&modules[1], &sibling);
    merkle_proof_node_t root_b;
    boot_header_calc_firmware_root(&modules[0], 1, &sibling, 1, &root_b);
    int b_ok = memcmp(root_b.bytes, expected_root, 32) == 0;
    print_hex("  B) proof fold        : ", root_b.bytes, 32);
    printf("     -> %s\n", b_ok ? "MATCH" : "MISMATCH");
    ok &= b_ok;
  }

  /* Case C: per-chunk code verification against the header's chunk hashes. */
  for (uint32_t i = 0; i < module_count; i++) {
    secbool r = firmware_module_verify_code(&modules[i]);
    int c_ok = (r == sectrue);
    printf("  C) verify code m%u    : %s\n", i, c_ok ? "OK" : "FAIL");
    ok &= c_ok;
  }

  /* Case D: tamper one code byte -> verification must fail. */
  if (code_len[0] > 0) {
    code_ptr[0][0] ^= 0xFF;
    secbool r = firmware_module_verify_code(&modules[0]);
    int d_ok = (r == secfalse);
    printf("  D) tampered code m0   : %s\n",
           d_ok ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= d_ok;
    code_ptr[0][0] ^= 0xFF;  // restore
  }

  /* Case E: full firmware_verify (role + authenticity + integrity). Only the
     2-module secmon+kernel firmware is exercised here. */
  if (module_count == 2) {
    merkle_proof_node_t trusted;
    memcpy(trusted.bytes, expected_root, 32);
    const uint32_t roles[2] = {FW_MODULE_SECMON, FW_MODULE_APP};
    secbool r = firmware_verify(modules, 2, roles, NULL, 0, &trusted);
    int e_ok = (r == sectrue);
    printf("  E) firmware_verify    : %s\n", e_ok ? "OK" : "FAIL");
    ok &= e_ok;

    /* Case F: wrong roles (swapped) must be rejected by role-binding. */
    const uint32_t bad_roles[2] = {FW_MODULE_APP, FW_MODULE_SECMON};
    secbool r2 = firmware_verify(modules, 2, bad_roles, NULL, 0, &trusted);
    int f_ok = (r2 == secfalse);
    printf("  F) swapped roles      : %s\n",
           f_ok ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= f_ok;

    /* Case H: firmware_type = variant + trust class (both storage axes). The
       variant is authenticated in the manifest now, not the module header, so
       exercise the compose/extract helpers with a fixed value here. */
    uint32_t variant = FW_VARIANT_UNIVERSAL;
    uint8_t ft_official = firmware_type_compose(variant, secfalse);
    uint8_t ft_custom = firmware_type_compose(variant, sectrue);
    int h_ok = firmware_type_variant(ft_official) == variant &&
               firmware_type_is_custom(ft_official) == secfalse &&
               firmware_type_variant(ft_custom) == variant &&
               firmware_type_is_custom(ft_custom) == sectrue &&
               ft_official != ft_custom;
    printf("  H) firmware_type      : official=0x%02x custom=0x%02x -> %s\n",
           ft_official, ft_custom, h_ok ? "OK" : "FAIL");
    ok &= h_ok;

    /* Case I: header-only verification (update preamble). Authenticates the
       module headers against the root WITHOUT touching any code; then a tampered
       header byte (a chunk hash) must break the root and be rejected. */
    secbool ih = firmware_verify_headers(modules, 2, roles, NULL, 0, &trusted);
    int i_ok = (ih == sectrue);
    /* offset 40 is inside the first chunk hash, past the 32-byte fixed part */
    ((uint8_t *)modules[0].hdr)[40] ^= 0xFF;
    secbool ih2 = firmware_verify_headers(modules, 2, roles, NULL, 0, &trusted);
    i_ok &= (ih2 == secfalse);
    ((uint8_t *)modules[0].hdr)[40] ^= 0xFF;  // restore
    printf("  I) verify headers     : %s (tamper %s)\n", ih == sectrue ? "OK" : "FAIL",
           ih2 == secfalse ? "rejected OK" : "ACCEPTED (bug!)");
    ok &= i_ok;
  }

  free(buf);
  printf("\nRESULT: %s\n", ok ? "C matches Python  OK" : "MISMATCH");
  return ok ? 0 : 1;
}
