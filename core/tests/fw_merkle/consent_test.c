/*
 * Cross-validation of the interaction-less upgrade consent digest.
 *
 * The digest is a contract between two different binaries: FIRMWARE computes it
 * over a boot header PREFIX it was handed over the wire, then the BOOTLOADER
 * recomputes it over the FULL header the host delivered -- and refuses to
 * install without asking the user unless the two agree. Both call the same
 * boot_header_merkle.c code, and this harness compiles that real source (never
 * a copy) to prove the two views produce identical bytes.
 *
 * The property that makes it work is that the digest covers the authenticated
 * part and the Merkle proof but stops before the unauthenticated part. That is
 * what makes it invariant under the firmware_type byte the bootloader REWRITES
 * while staging, and under signature substitution -- while still pinning
 * everything consent must pin.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shims.h"

#define AUTH sizeof(boot_header_auth_t)
#define NODES 3
#define PROOF (sizeof(boot_header_merkle_proof_t) + NODES * 32)
#define HDRSZ (AUTH + PROOF + sizeof(boot_header_unauth_t))

/* Offset of the byte phase 1 rewrites, derived rather than hardcoded. */
#define FW_TYPE_OFF \
  (AUTH + PROOF + offsetof(boot_header_unauth_t, firmware_type))
/* A signature byte, likewise. */
#define SIG_OFF \
  (AUTH + PROOF + offsetof(boot_header_unauth_t, slh_signature) + 10)

static int fails = 0;

static void ck(const char *what, int ok) {
  printf("  %-56s %s\n", what, ok ? "ok" : "FAIL");
  if (!ok) fails++;
}

static uint8_t manifest[300];

/* Digest as the BOOTLOADER computes it: from the full header in flash. */
static secbool digest_bootloader(const uint8_t *hdr_full,
                                 merkle_proof_node_t *out) {
  const boot_header_auth_t *a = (const boot_header_auth_t *)hdr_full;
  size_t extent = 0;
  if (sectrue != boot_header_prefix_extent(hdr_full, a->header_size, &extent)) {
    return secfalse;
  }
  return boot_header_consent_digest(hdr_full, extent, manifest,
                                    sizeof(manifest), out);
}

/* Digest as FIRMWARE computes it: from one prefix||manifest blob off the wire,
 * splitting it itself -- no length is transmitted for the boundary. */
static secbool digest_firmware(const uint8_t *blob, size_t blob_len,
                               merkle_proof_node_t *out) {
  size_t extent = 0;
  if (sectrue != boot_header_prefix_extent(blob, blob_len, &extent)) {
    return secfalse;
  }
  if (extent >= blob_len) {
    return secfalse;
  }
  return boot_header_consent_digest(blob, extent, blob + extent,
                                    blob_len - extent, out);
}

/* Writes `len` bytes to <dir>/<name>. */
static void dump(const char *dir, const char *name, const void *data,
                 size_t len) {
  char path[512];
  snprintf(path, sizeof(path), "%s/%s", dir, name);
  FILE *f = fopen(path, "wb");
  if (f == NULL) {
    printf("  could not write %s\n", path);
    fails++;
    return;
  }
  fwrite(data, 1, len, f);
  fclose(f);
}

int main(int argc, char **argv) {
  uint8_t *hdr = calloc(1, HDRSZ);
  if (hdr == NULL) return 1;

  boot_header_auth_t *a = (boot_header_auth_t *)hdr;
  a->magic = BOOT_HEADER_MAGIC_TRZQ;
  a->auth_size = AUTH;
  a->header_size = HDRSZ;
  a->code_size = 0x4000;
  a->monotonic_version = 7;
  for (int i = 0; i < 32; i++) a->firmware_root.bytes[i] = (uint8_t)(0xA0 + i);

  boot_header_merkle_proof_t *pr = (boot_header_merkle_proof_t *)(hdr + AUTH);
  pr->node_count = NODES;
  for (size_t i = 0; i < NODES * 32; i++)
    hdr[AUTH + sizeof(*pr) + i] = (uint8_t)(i * 7 + 1);
  for (size_t i = 0; i < sizeof(boot_header_unauth_t); i++)
    hdr[AUTH + PROOF + i] = (uint8_t)(i * 13 + 5);
  hdr[FW_TYPE_OFF] = 0; /* as transmitted: bootloader has not resolved it yet */

  for (size_t i = 0; i < sizeof(manifest); i++)
    manifest[i] = (uint8_t)(i ^ 0x5A);

  printf("== extent ==\n");
  size_t e_full = 0, e_prefix = 0;
  ck("prefix_extent on a FULL header",
     sectrue == boot_header_prefix_extent(hdr, HDRSZ, &e_full));
  ck("extent == auth_size + proof size", e_full == AUTH + PROOF);
  ck("prefix_extent on the PREFIX ALONE (what firmware gets)",
     sectrue == boot_header_prefix_extent(hdr, AUTH + PROOF, &e_prefix));
  ck("same boundary from either view", e_full == e_prefix);

  printf("== the two sides agree ==\n");
  size_t blob_len = AUTH + PROOF + sizeof(manifest);
  uint8_t *blob = malloc(blob_len);
  if (blob == NULL) return 1;
  memcpy(blob, hdr, AUTH + PROOF);
  memcpy(blob + AUTH + PROOF, manifest, sizeof(manifest));

  merkle_proof_node_t bl = {0}, fw = {0};
  ck("bootloader digest computed", sectrue == digest_bootloader(hdr, &bl));
  ck("firmware digest computed",
     sectrue == digest_firmware(blob, blob_len, &fw));
  ck("DIGESTS IDENTICAL", memcmp(bl.bytes, fw.bytes, 32) == 0);

  printf("== invariant under what the bootloader rewrites ==\n");
  merkle_proof_node_t after = {0};
  hdr[FW_TYPE_OFF] = 0x42; /* phase 1: unauth->firmware_type = firmware_type */
  digest_bootloader(hdr, &after);
  ck("unchanged by the firmware_type rewrite",
     memcmp(bl.bytes, after.bytes, 32) == 0);
  hdr[SIG_OFF] ^= 0xFF;
  digest_bootloader(hdr, &after);
  ck("unchanged by a signature byte", memcmp(bl.bytes, after.bytes, 32) == 0);
  hdr[SIG_OFF] ^= 0xFF;

  printf("== but pins everything consent must pin ==\n");
  a->monotonic_version = 8;
  digest_bootloader(hdr, &after);
  ck("changes with monotonic_version", memcmp(bl.bytes, after.bytes, 32) != 0);
  a->monotonic_version = 7;

  a->version.major = 9;
  digest_bootloader(hdr, &after);
  ck("changes with the bootloader version",
     memcmp(bl.bytes, after.bytes, 32) != 0);
  a->version.major = 0;

  a->code_size ^= 0x100;
  digest_bootloader(hdr, &after);
  ck("changes with code_size", memcmp(bl.bytes, after.bytes, 32) != 0);
  a->code_size ^= 0x100;

  a->firmware_root.bytes[0] ^= 0xFF;
  digest_bootloader(hdr, &after);
  ck("changes with firmware_root (the release)",
     memcmp(bl.bytes, after.bytes, 32) != 0);
  a->firmware_root.bytes[0] ^= 0xFF;

  hdr[AUTH + sizeof(*pr)] ^= 0xFF;
  digest_bootloader(hdr, &after);
  ck("changes with a proof node (modelRoot -> the nRF image)",
     memcmp(bl.bytes, after.bytes, 32) != 0);
  hdr[AUTH + sizeof(*pr)] ^= 0xFF;

  manifest[5] ^= 0xFF;
  digest_bootloader(hdr, &after);
  ck("changes with the manifest (variant / version / code_hash)",
     memcmp(bl.bytes, after.bytes, 32) != 0);
  manifest[5] ^= 0xFF;

  digest_bootloader(hdr, &after);
  ck("restored inputs reproduce the original digest",
     memcmp(bl.bytes, after.bytes, 32) == 0);

  printf("== bounds ==\n");
  size_t junk = 0;
  ck("reject: shorter than the auth struct",
     secfalse == boot_header_prefix_extent(hdr, AUTH - 1, &junk));
  ck("reject: no room for the proof header",
     secfalse == boot_header_prefix_extent(hdr, AUTH + 2, &junk));
  ck("reject: truncated mid-proof",
     secfalse ==
         boot_header_prefix_extent(hdr, AUTH + sizeof(*pr) + 32, &junk));
  a->magic = 0xDEADBEEF;
  ck("reject: bad magic",
     secfalse == boot_header_prefix_extent(hdr, HDRSZ, &junk));
  a->magic = BOOT_HEADER_MAGIC_TRZQ;
  a->auth_size = AUTH - 1;
  ck("reject: auth_size below the known struct",
     secfalse == boot_header_prefix_extent(hdr, HDRSZ, &junk));
  a->auth_size = HDRSZ + 1;
  ck("reject: auth_size past the buffer",
     secfalse == boot_header_prefix_extent(hdr, HDRSZ, &junk));
  a->auth_size = AUTH;
  pr->node_count = BOOT_HEADER_MERKLE_PROOF_MAXLEN + 1;
  ck("reject: node_count over the cap",
     secfalse == boot_header_prefix_extent(hdr, HDRSZ, &junk));
  pr->node_count = NODES;
  ck("reject: NULL out",
     secfalse == boot_header_prefix_extent(hdr, HDRSZ, NULL));
  ck("reject: digest with zero-length manifest",
     secfalse == boot_header_consent_digest(hdr, e_full, manifest, 0, &after));
  ck("reject: digest with zero-length prefix",
     secfalse == boot_header_consent_digest(hdr, 0, manifest, sizeof(manifest),
                                            &after));

  /* Firmware must reject a blob with nothing after the prefix. */
  ck("reject: prefix with no manifest following",
     secfalse == digest_firmware(hdr, AUTH + PROOF, &after));

  /* Hand the exact bytes and the resulting digest to the host cross-check, so
   * trezor_core_tools' preamble builder is proven to derive the same boundary
   * and the same digest from a header the device itself accepted. Inputs are
   * back to their original values here (asserted above). */
  if (argc > 1) {
    merkle_proof_node_t final = {0};
    digest_bootloader(hdr, &final);
    dump(argv[1], "header.bin", hdr, HDRSZ);
    dump(argv[1], "manifest.bin", manifest, sizeof(manifest));
    dump(argv[1], "digest.bin", final.bytes, sizeof(final.bytes));
    printf("== dumped vector to %s ==\n", argv[1]);
  }

  printf("\n%s (%d failure%s)\n", fails ? "FAILED" : "ALL PASS", fails,
         fails == 1 ? "" : "s");
  free(blob);
  free(hdr);
  return fails != 0;
}
