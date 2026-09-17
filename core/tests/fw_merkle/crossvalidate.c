/*
 * Host cross-validation harness for the firmware Merkle root.
 *
 * Compiles the real boot_header_merkle.c with a host SHA-256 and replays the
 * FWM3 vector from gen_multivariant.py through firmware_verify_manifest,
 * asserting the C computes the same firmware_root as Python and enforces the
 * same accept/reject policy. Build: run.sh (the -include shims.h is required).
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sha2.h"

#include "shims.h"

static void print_hex(const char *label, const uint8_t *b, size_t n) {
  printf("%s", label);
  for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
  printf("\n");
}

/* FWM3 vector (layout in gen_multivariant.py): each variant is a full image
 * [manifest | module code...], the leaf is H(0x00 || manifest), and a real
 * proof folds it to the founder firmware_root. */
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
  const char *names[] = {"none",         "custom",   "universal",
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
    const uint8_t *alt_image =
        p; /* different-size/version custom app (or none) */
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

    /* 1) full verify: the leaf folds to the founder root and every module's
     *    code matches its manifest code_hash. */
    secbool r = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                         proof_count, &trusted);
    int verify_ok = (r == sectrue);

    /* 2) app code byte flipped without updating its code_hash: rejected for
     *    every variant, custom included. */
    int tamper_app_ok = 1;
    if (app_size > 0) {
      image[app_addr + app_size - 1] ^= 0xFF;
      secbool r2 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      tamper_app_ok = (r2 == secfalse);
      image[app_addr + app_size - 1] ^= 0xFF;
    }

    /* 3) self-consistent different app (code and code_hash rewritten): custom
     *    must still verify (its app is founder-unbound), official must fail. */
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
      if (app_ch) {            /* keep the manifest self-consistent */
        firmware_module_code_hash((uintptr_t)image, app_addr, app_size,
                                  app_e->chunk_size, app_ch->bytes);
      }
      secbool rs = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      substitute_ok = is_custom ? (rs == sectrue) : (rs == secfalse);
      image[app_addr] = saved_byte;
      if (app_ch) memcpy(app_ch->bytes, saved_hash, 32);
    }

    /* 4) secmon code byte flipped: rejected for every variant. */
    image[secmon_addr] ^= 0xFF;
    secbool r4 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                          proof_count, &trusted);
    int tamper_secmon_ok = (r4 == secfalse);
    image[secmon_addr] ^= 0xFF;

    /* 5) proof node flipped: authenticity must fail. */
    int tamper_proof_ok = 1;
    if (proof_count > 0) {
      proof[0].bytes[0] ^= 0xFF;
      secbool r5 = firmware_verify_manifest(manifest, manifest_len, base, proof,
                                            proof_count, &trusted);
      tamper_proof_ok = (r5 == secfalse);
      proof[0].bytes[0] ^= 0xFF;
    }

    /* 6) custom only: a different-size/version app folds to the same root
     *    with the same proof. */
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
        verify_ok ? "OK" : "FAIL",
        tamper_app_ok ? "rejected OK" : "ACCEPTED (bug!)",
        substitute_ok ? (is_custom ? "accepted OK" : "rejected OK")
                      : "WRONG (bug!)",
        tamper_secmon_ok ? "rejected OK" : "ACCEPTED (bug!)",
        tamper_proof_ok ? "rejected OK" : "ACCEPTED (bug!)",
        alt_len > 0
            ? (alt_ok ? ", alt-app accepted OK" : ", alt-app REJECTED (bug!)")
            : "");
    ok &= verify_ok & tamper_app_ok & substitute_ok & tamper_secmon_ok &
          tamper_proof_ok & alt_ok;
  }

  /* A custom manifest with no APP entry is hashed verbatim on both sides.
   * Checked as a single-leaf tree (empty proof, root = leaf), so this asserts
   * leaf equality only. */
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

  /* Variant codeword predicates, plus the two properties the codewords exist
   * for: pairwise distance >= 16 bit flips, and no small fw_variant_t value
   * reads as a variant. */
  {
    const fw_variant_sec_t univ = FW_VARIANT_SEC_UNIVERSAL;
    const fw_variant_sec_t custom = FW_VARIANT_SEC_CUSTOM;
    int h_ok =
        fw_variant_to_fw_type(univ) == FW_VARIANT_UNIVERSAL &&
        fw_variant_to_fw_type(custom) == FW_VARIANT_CUSTOM &&
        fw_variant_to_fw_type(FW_VARIANT_SEC_INVALID) == FW_VARIANT_NONE &&
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

    const uint32_t smalls[] = {FW_VARIANT_NONE, FW_VARIANT_CUSTOM,
                               FW_VARIANT_UNIVERSAL, FW_VARIANT_BITCOIN_ONLY,
                               FW_VARIANT_PRODTEST};
    for (unsigned i = 0; i < sizeof(smalls) / sizeof(smalls[0]); i++) {
      h_ok &= fw_variant_is_provisioned(smalls[i]) == secfalse;
    }

    /* Minimum pairwise Hamming distance over the codeword set, INVALID
     * included. */
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
