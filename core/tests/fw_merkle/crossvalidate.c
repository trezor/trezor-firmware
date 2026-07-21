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
#define FW_VARIANT_CUSTOM 1
#define FW_VARIANT_UNIVERSAL 2
#define FW_VARIANT_BITCOIN_ONLY 3
#define FW_VARIANT_PRODTEST 4

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
    uint32_t alt_len;
    memcpy(&alt_len, p, 4);
    p += 4;
    const uint8_t *alt_image = p; /* different-size/version custom app (or none) */
    p += alt_len;
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

    int is_custom = (variant_id == FW_VARIANT_CUSTOM);

    /* 1) full verify: the variant leaf (for CUSTOM the app code_hash is zeroed
     *    inside the fold) folds to the founder root, and every module's code
     *    matches its manifest code_hash. Custom-ness is derived from the
     *    manifest variant -- there is no caller flag. */
    secbool r = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                         proof_count, &trusted);
    int verify_ok = (r == sectrue);

    /* 2) tamper an APP code byte WITHOUT updating its manifest code_hash -> the
     *    integrity check must fail for EVERY variant, custom INCLUDED (the
     *    custom app carries the creator's real hash and is corruption-checked;
     *    this is the Mod 2 change from the old allow_custom skip). */
    int tamper_app_ok = 1;
    if (app_size > 0) {
      image[app_addr + app_size - 1] ^= 0xFF;
      secbool r2 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      tamper_app_ok = (r2 == secfalse);
      image[app_addr + app_size - 1] ^= 0xFF;
    }

    /* 3) SUBSTITUTE the app: change the app code AND rewrite its manifest
     *    code_hash to match (a self-consistent DIFFERENT app). The CUSTOM slot
     *    must still verify -- its app is founder-UNbound (the leaf zeroes it) --
     *    while an OFFICIAL variant must now FAIL, because its app code_hash is
     *    founder-signed and changing it breaks the fold. This is the core custom
     *    property (accepts any integrity-consistent app; official does not). */
    int substitute_ok = 1;
    if (app_size > 0) {
      firmware_manifest_t *m = (firmware_manifest_t *)image;
      merkle_proof_node_t *app_ch = NULL;
      for (uint32_t i = 0; i < m->module_count; i++) {
        if (m->entries[i].module_type == FW_MODULE_APP) {
          app_ch = &m->entries[i].code_hash;
          break;
        }
      }
      uint8_t saved_byte = image[app_addr];
      uint8_t saved_hash[32];
      if (app_ch) memcpy(saved_hash, app_ch->bytes, 32);
      image[app_addr] ^= 0xFF; /* different app code */
      if (app_ch) {            /* keep the manifest self-consistent */
        SHA256_CTX c;
        sha256_Init(&c);
        sha256_Update(&c, image + app_addr, app_size);
        sha256_Final(&c, app_ch->bytes);
      }
      secbool rs = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      substitute_ok = is_custom ? (rs == sectrue) : (rs == secfalse);
      image[app_addr] = saved_byte;
      if (app_ch) memcpy(app_ch->bytes, saved_hash, 32);
    }

    /* 4) tamper a SECMON code byte -> reject for EVERY variant: the secure
     *    monitor is always founder-bound, even for the custom slot. */
    image[secmon_addr] ^= 0xFF;
    secbool r4 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted);
    int tamper_secmon_ok = (r4 == secfalse);
    image[secmon_addr] ^= 0xFF;

    /* 5) tamper a proof node -> authenticity must fail. */
    int tamper_proof_ok = 1;
    if (proof_count > 0) {
      proof[0].bytes[0] ^= 0xFF;
      secbool r5 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      tamper_proof_ok = (r5 == secfalse);
      proof[0].bytes[0] ^= 0xFF;
    }

    /* 6) app-agnostic slot (custom only): a DIFFERENT-size/version app (the alt
     *    image) must fold to the SAME founder root + proof. Proves the custom
     *    leaf zeroes the app version/size/code_hash, so it is not tied to one
     *    specific creator build. */
    int alt_ok = 1;
    if (alt_len > 0) {
      const firmware_manifest_t *am = (const firmware_manifest_t *)alt_image;
      size_t am_len = firmware_manifest_size(am);
      secbool ra = firmware_verify_manifest(am, am_len, (uintptr_t)alt_image,
                                            proof, proof_count, &trusted);
      alt_ok = (ra == sectrue);
    }

    printf(
        "  variant %u (%-12s): verify %s, tamper-app %s, substitute-app %s, "
        "tamper-secmon %s, tamper-proof %s%s\n",
        variant_id, variant_id < 6 ? names[variant_id] : "?",
        verify_ok ? "OK" : "FAIL", tamper_app_ok ? "rejected OK" : "ACCEPTED (bug!)",
        substitute_ok ? (is_custom ? "accepted OK" : "rejected OK") : "WRONG (bug!)",
        tamper_secmon_ok ? "rejected OK" : "ACCEPTED (bug!)",
        tamper_proof_ok ? "rejected OK" : "ACCEPTED (bug!)",
        alt_len > 0 ? (alt_ok ? ", alt-app accepted OK" : ", alt-app REJECTED (bug!)")
                    : "");
    ok &= verify_ok & tamper_app_ok & substitute_ok & tamper_secmon_ok &
          tamper_proof_ok & alt_ok;
  }

  /* firmware_type IS the authenticated variant byte (custom-ness == the
   * FW_VARIANT_CUSTOM variant, no flag). Exercise the compose/extract helpers +
   * the positive is_official allow-list. */
  {
    uint8_t ft_univ = firmware_type_compose(FW_VARIANT_UNIVERSAL);
    uint8_t ft_custom = firmware_type_compose(FW_VARIANT_CUSTOM);
    int h_ok = ft_univ == FW_VARIANT_UNIVERSAL && ft_custom == FW_VARIANT_CUSTOM &&
               firmware_type_variant(ft_univ) == FW_VARIANT_UNIVERSAL &&
               firmware_type_is_custom(ft_custom) == sectrue &&
               firmware_type_is_custom(ft_univ) == secfalse &&
               firmware_type_is_official(ft_univ) == sectrue &&
               firmware_type_is_official(ft_custom) == secfalse &&
               firmware_type_is_official(
                   firmware_type_compose(FW_VARIANT_NONE)) == secfalse;
    printf("  firmware_type          : universal=0x%02x custom=0x%02x -> %s\n",
           ft_univ, ft_custom, h_ok ? "OK" : "FAIL");
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
