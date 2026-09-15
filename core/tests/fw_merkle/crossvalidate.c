/*
 * Host cross-validation harness for the firmware Merkle root.
 *
 * Compiles the *real* on-device tree math (boot_header_merkle.c) with a host
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
#include "shims.h"


/* --- harness ----------------------------------------------------------- */
static void print_hex(const char *label, const uint8_t *b, size_t n) {
  printf("%s", label);
  for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
  printf("\n");
}

/* Manifest-based multi-variant vector (FWM3): each variant is a full firmware
 * image [manifest | module code...], the variant leaf is H(0x00 || manifest),
 * and a real proof folds it to the founder firmware_root. Replays the REAL
 * device firmware_verify_manifest (authenticity fold + per-entry code_hash).
 * Layout: "FWM3" | founder_root(32) | variant_count(u32), then per variant:
 *   variant_id(u32) | image_len(u32) | image | manifest_len(u32) |
 *   proof_count(u32) | proof_node(32)...
 * then once: noapp_len(u32) | noapp_manifest | noapp_leaf(32). */
static int run_manifest(const uint8_t *buf) {
  const uint8_t *p = buf + 4; /* skip "FWM3" */
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
      firmware_manifest_entry_t *app_e = NULL;
      for (uint32_t i = 0; i < m->module_count; i++) {
        if (m->entries[i].module_type == FW_MODULE_APP) {
          app_e = &m->entries[i];
          break;
        }
      }
      merkle_proof_node_t *app_ch = app_e ? &app_e->code_hash : NULL;
      uint8_t saved_byte = image[app_addr];
      uint8_t saved_hash[32];
      if (app_ch) memcpy(saved_hash, app_ch->bytes, 32);
      image[app_addr] ^= 0xFF; /* different app code */
      if (app_ch) {            /* keep the manifest self-consistent (chain) */
        firmware_module_code_hash((uintptr_t)image, app_addr, app_size,
                                  app_e->chunk_size, app_ch->bytes);
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

  /* A CUSTOM manifest with no APP entry: there is no app tail to zero, so both
   * sides must hash it VERBATIM -- a mirror that zeroed firmware_version anyway
   * would compute a different leaf here. Checked as a single-leaf tree (empty
   * proof, root = the leaf the signer computed), so this asserts leaf equality
   * and nothing about folding. */
  {
    uint32_t noapp_len;
    memcpy(&noapp_len, p, 4);
    p += 4;
    const firmware_manifest_t *nm = (const firmware_manifest_t *)p;
    p += noapp_len;
    merkle_proof_node_t noapp_leaf;
    memcpy(noapp_leaf.bytes, p, 32);
    p += 32;

    secbool rn =
        firmware_manifest_authentic(nm, noapp_len, NULL, 0, &noapp_leaf);
    int noapp_ok = (rn == sectrue);
    printf("  no-APP custom manifest: leaf %s\n",
           noapp_ok ? "matches the signer OK" : "DIFFERS from the signer (bug!)");
    ok &= noapp_ok;
  }

  /* The variant is a HARDENED codeword in both places it lives (the manifest
   * field and the boot header's firmware_type), so there is no small<->wide
   * conversion on the device -- only the narrowing for the storage KDF.
   * Exercise the predicates plus the two things the codewords exist for:
   * every pair is >= 16 bit flips apart, and a small fw_variant_t value is NOT
   * a variant (so a legacy-shaped or truncated value cannot pass). */
  {
    const fw_variant_sec_t univ = FW_VARIANT_SEC_UNIVERSAL;
    const fw_variant_sec_t custom = FW_VARIANT_SEC_CUSTOM;
    int h_ok = fw_variant_to_fw_type(univ) == FW_VARIANT_UNIVERSAL &&
               fw_variant_to_fw_type(custom) == FW_VARIANT_CUSTOM &&
               fw_variant_to_fw_type(FW_VARIANT_SEC_INVALID) ==
                   FW_VARIANT_NONE &&
               fw_variant_is_custom(custom) == sectrue &&
               fw_variant_is_custom(univ) == secfalse &&
               fw_variant_is_official(univ) == sectrue &&
               fw_variant_is_official(custom) == secfalse &&
               fw_variant_is_official(FW_VARIANT_SEC_NONE) == secfalse &&
               fw_variant_is_official(FW_VARIANT_SEC_INVALID) == secfalse &&
               fw_variant_is_provisioned(univ) == sectrue &&
               fw_variant_is_provisioned(custom) == sectrue &&
               fw_variant_is_provisioned(FW_VARIANT_SEC_NONE) == secfalse &&
               fw_variant_is_provisioned(FW_VARIANT_SEC_INVALID) == secfalse;

    /* A small value must never read as a variant: that is what stops a
     * truncated or legacy-shaped field from being accepted. */
    const uint32_t smalls[] = {FW_VARIANT_NONE, FW_VARIANT_CUSTOM,
                               FW_VARIANT_UNIVERSAL, FW_VARIANT_BITCOIN_ONLY,
                               FW_VARIANT_PRODTEST};
    for (unsigned i = 0; i < sizeof(smalls) / sizeof(smalls[0]); i++) {
      h_ok &= fw_variant_is_provisioned(smalls[i]) == secfalse;
    }

    /* Minimum pairwise Hamming distance over the codeword set, INVALID
     * included -- the property the whole scheme rests on. */
    const fw_variant_sec_t cw[] = {
        FW_VARIANT_SEC_INVALID,      FW_VARIANT_SEC_NONE,
        FW_VARIANT_SEC_CUSTOM,       FW_VARIANT_SEC_UNIVERSAL,
        FW_VARIANT_SEC_BITCOIN_ONLY, FW_VARIANT_SEC_PRODTEST};
    unsigned n = sizeof(cw) / sizeof(cw[0]);
    unsigned min_d = 32;
    for (unsigned i = 0; i < n; i++) {
      for (unsigned j = i + 1; j < n; j++) {
        unsigned d = 0;
        for (uint32_t x = cw[i] ^ cw[j]; x; x >>= 1) {
          d += x & 1u;
        }
        if (d < min_d) {
          min_d = d;
        }
      }
    }
    h_ok &= (min_d >= 16);

    printf(
        "  fw_variant             : univ=0x%08x custom=0x%08x min_dist=%u -> "
        "%s\n",
        univ, custom, min_d, h_ok ? "OK" : "FAIL");
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
  if (sz >= 4 && memcmp(buf, "FWM3", 4) == 0) {
    int r = run_manifest(buf);
    free(buf);
    return r;
  }

  fprintf(stderr, "bad magic (expected FWM3)\n");
  free(buf);
  return 2;
}
