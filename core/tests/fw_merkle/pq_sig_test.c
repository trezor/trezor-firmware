/*
 * End-to-end test of the nRF's founder verification (MCUboot fork:
 * boot/bootutil/src/image_pq.c) against REAL signatures.
 *
 * The other harness (nrf_crossvalidate.c) proves the leaf/fold agree with the STM
 * and Python, but it cannot exercise the signature path: the host has no SLH-DSA
 * available and the founder's real keys are not in the tree. So this test generates
 * its OWN key pool (3 SLH-DSA + 3 Ed25519), builds a PQ-native MCUboot image, signs
 * the modelRoot exactly as the founder would, and checks that pq_image_verify
 * accepts it -- and rejects every tampering we can think of.
 *
 * That validates the parts most likely to be silently wrong: the message
 * construction (SLH-DSA over modelRoot; Ed25519 over SHA256(modelRoot||slh_sig)),
 * which MUST match the STM's boot_header_check_signature or the two MCUs disagree
 * about which images are authentic, and the 2-of-3 key derivation (the image
 * declares no sigmask, so the verifier searches the pool and must require two
 * DISTINCT keys).
 *
 * Build (from core/):
 *   see tests/fw_merkle/run_founder_sig.sh
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bootutil/image_pq.h"

/* sphincsplus from the mcuboot repo's own ext/ submodule, addressed via its
 * containing dir -- NEVER with ref/ on the include path, or its sha2.h shadows
 * trezor-crypto's for this file (it did, first try). */
#include "ext/sphincsplus/ref/api.h" /* crypto_sign_keypair / _signature */

#include "ed25519-donna/ed25519.h"
#include "sha2.h" /* trezor-crypto */

/* trezor-crypto's consteq() calls this if its loop-completion check fails. The
 * bootloader supplies a real one (image_validate.c); this stands in for it here. */
void tc_fault_handler(const char *msg) {
  printf("FAULT: %s\n", msg);
  abort();
}

/* ---- deterministic randombytes -------------------------------------------
 * sphincsplus' own randombytes.c reads /dev/urandom; a fixed PRNG instead keeps
 * this test reproducible (and independent of the sandbox's /dev access). */
static uint64_t prng_state = 0x123456789abcdefULL;
void randombytes(unsigned char *x, unsigned long long xlen) {
  for (unsigned long long i = 0; i < xlen; i++) {
    prng_state = prng_state * 6364136223846793005ULL + 1442695040888963407ULL;
    x[i] = (unsigned char)(prng_state >> 33);
  }
}

/* ---- flat-buffer reader (same shim the device's flash_area reader replaces) */
struct flat {
  const uint8_t *buf;
  uint32_t len;
};
static int flat_read(void *ctx, uint32_t off, void *dst, uint32_t len) {
  const struct flat *f = (const struct flat *)ctx;
  if ((uint64_t)off + len > (uint64_t)f->len) return -1;
  memcpy(dst, f->buf + off, len);
  return 0;
}

/* ---- MCUboot image construction ------------------------------------------ */
#define IMG_MAGIC 0x96f3b83dU
#define TLV_PROT_INFO_MAGIC 0x6908U
#define TLV_INFO_MAGIC 0x6907U
#define TLV_MODEL_ID 0x00A3U
#define HDR_SIZE 32u
#define PAYLOAD_SIZE 512u

#define NUM_KEYS 3
#define COPATH_NODES 4

static uint8_t image[64 * 1024];
static uint32_t image_len;
static uint32_t off_slh[PQ_SIG_COUNT], off_ec[PQ_SIG_COUNT], off_copath;

static void put16(uint32_t off, uint16_t v) {
  image[off] = (uint8_t)(v & 0xff);
  image[off + 1] = (uint8_t)(v >> 8);
}
static void put32(uint32_t off, uint32_t v) {
  for (int i = 0; i < 4; i++) image[off + i] = (uint8_t)(v >> (8 * i));
}

/* Lay out a PQ-native image with the founder records contiguous, last and with no
 * slack -- not because the leaf requires it (it does not; the leaf is the image
 * hash) but because that is the shape the verifiers whitelist. The founder values
 * are left zeroed here: they live in the UNPROTECTED area, outside the image hash,
 * so they do not affect the leaf -- which is exactly what makes signing possible at
 * all (otherwise the signature would have to cover itself). */
/* -1 => omit the security-counter TLV entirely */
static long g_sec_cnt = -1;
/* absolute offset of the counter value in `image`, 0 when omitted */
static size_t off_sec_cnt = 0;

static void build_image(uint8_t sigmask) {
  memset(image, 0, sizeof(image));

  /* protected TLVs: model id + sigmask. Both are inside the image hash AND the
   * founder leaf, so both are committed by the signature. */
  uint8_t prot[64];
  uint32_t pl = 0;
  prot[pl++] = TLV_MODEL_ID & 0xff; prot[pl++] = TLV_MODEL_ID >> 8;
  prot[pl++] = 4; prot[pl++] = 0;
  memcpy(&prot[pl], "T3T2", 4); pl += 4;
  prot[pl++] = IMAGE_TLV_PQ_SIGMASK & 0xff;
  prot[pl++] = IMAGE_TLV_PQ_SIGMASK >> 8;
  prot[pl++] = 1; prot[pl++] = 0;
  prot[pl++] = sigmask;
  /* Security counter, PROTECTED like the real imgtool writes it -- so it lands
   * inside the image hash and inside the founder leaf. g_sec_cnt < 0 omits it,
   * which is the "image built without -s" case. */
  size_t sec_cnt_rel = 0;
  if (g_sec_cnt >= 0) {
    sec_cnt_rel = pl + 4; /* value starts after this record's type+len */
    prot[pl++] = IMAGE_TLV_PQ_SEC_CNT & 0xff;
    prot[pl++] = IMAGE_TLV_PQ_SEC_CNT >> 8;
    prot[pl++] = 4; prot[pl++] = 0;
    const uint32_t c = (uint32_t)g_sec_cnt;
    prot[pl++] = c & 0xff; prot[pl++] = (c >> 8) & 0xff;
    prot[pl++] = (c >> 16) & 0xff; prot[pl++] = (c >> 24) & 0xff;
  }
  const uint16_t prot_area = (uint16_t)(4 + pl);

  put32(0, IMG_MAGIC);
  put32(4, 0);
  put16(8, (uint16_t)HDR_SIZE);
  put16(10, prot_area);
  put32(12, PAYLOAD_SIZE);
  put32(16, 0);

  for (uint32_t i = 0; i < PAYLOAD_SIZE; i++) image[HDR_SIZE + i] = (uint8_t)i;

  uint32_t p = HDR_SIZE + PAYLOAD_SIZE;
  put16(p, TLV_PROT_INFO_MAGIC);
  put16(p + 2, prot_area);
  memcpy(&image[p + 4], prot, pl);
  /* Absolute offset of the counter VALUE, for the tamper case below. */
  off_sec_cnt = (g_sec_cnt >= 0) ? (p + 4 + sec_cnt_rel) : 0;
  p += prot_area;

  /* Unprotected area: the image-hash TLV (0x10) then the founder records. 0x10
   * carries the TRUE hash over header+payload+protected TLVs -- the leaf IS that
   * value, so a stand-in would make the fixture self-inconsistent in exactly the
   * way MCUboot rejects, and the shape check whitelists it. */
  const uint16_t unprot_area =
      (uint16_t)(4 + (4 + 32) + 2 * (4 + PQ_SLH_SIG_LEN) +
                 2 * (4 + PQ_EC_SIG_LEN) + (4 + COPATH_NODES * 32));
  put16(p, TLV_INFO_MAGIC);
  put16(p + 2, unprot_area);
  uint32_t q = p + 4;

  {
    SHA256_CTX c;
    sha256_Init(&c);
    sha256_Update(&c, image, p); /* header + payload + protected area */
    put16(q, IMAGE_TLV_PQ_IMAGE_HASH);
    put16(q + 2, 32);
    sha256_Final(&c, &image[q + 4]);
    q += 4 + 32;
  }

  const uint16_t slh_t[] = {IMAGE_TLV_PQ_SLH_SIG_0, IMAGE_TLV_PQ_SLH_SIG_1};
  const uint16_t ec_t[] = {IMAGE_TLV_PQ_EC_SIG_0, IMAGE_TLV_PQ_EC_SIG_1};
  for (int i = 0; i < PQ_SIG_COUNT; i++) {
    put16(q, slh_t[i]); put16(q + 2, PQ_SLH_SIG_LEN);
    off_slh[i] = q + 4; q += 4 + PQ_SLH_SIG_LEN;
  }
  for (int i = 0; i < PQ_SIG_COUNT; i++) {
    put16(q, ec_t[i]); put16(q + 2, PQ_EC_SIG_LEN);
    off_ec[i] = q + 4; q += 4 + PQ_EC_SIG_LEN;
  }
  put16(q, IMAGE_TLV_PQ_MERKLE_PROOF); put16(q + 2, COPATH_NODES * 32);
  off_copath = q + 4; q += 4 + COPATH_NODES * 32;

  image_len = q;
}

int main(void) {
  int fails = 0;

  /* --- key pool: 3 of each, as on the STM (<=3, 2-of-3 policy) --- */
  static uint8_t pq_pk[NUM_KEYS][CRYPTO_PUBLICKEYBYTES];
  static uint8_t pq_sk[NUM_KEYS][CRYPTO_SECRETKEYBYTES];
  static uint8_t ec_pk[NUM_KEYS][32], ec_sk[NUM_KEYS][32];
  const uint8_t *pq_keys[NUM_KEYS], *ec_keys[NUM_KEYS];

  printf("generating %d SLH-DSA + %d Ed25519 keypairs (slow: 128s)...\n", NUM_KEYS,
         NUM_KEYS);
  for (int i = 0; i < NUM_KEYS; i++) {
    if (crypto_sign_keypair(pq_pk[i], pq_sk[i]) != 0) {
      printf("FAIL: crypto_sign_keypair\n");
      return 1;
    }
    randombytes(ec_sk[i], sizeof(ec_sk[i]));
    ed25519_publickey(ec_sk[i], ec_pk[i]);
    pq_keys[i] = pq_pk[i];
    ec_keys[i] = ec_pk[i];
  }

  /* --- sigmask 0b101 names keys 0 and 2: a NON-ADJACENT pair, so a wrong slot->key
   *     mapping (e.g. 0,1) is caught instead of accidentally matching. Slot 0 -> key
   *     0, slot 1 -> key 2 (i-th lowest set bit), same convention as the STM. --- */
  const uint8_t sigmask = 0x05;
  const int slot_key[PQ_SIG_COUNT] = {0, 2};

  build_image(sigmask);
  struct flat img = {image, image_len};

  /* modelRoot = fold(H(0x00 || image hash), co-path). The co-path is arbitrary
   * here: the founder signs whatever root the tree yields. */
  uint8_t copath[COPATH_NODES * 32];
  randombytes(copath, sizeof(copath));
  memcpy(&image[off_copath], copath, sizeof(copath));

  uint8_t img_hash[32], leaf[32], root[32];
  if (pq_image_hash(flat_read, &img, image_len, img_hash) != 0) {
    printf("FAIL: pq_image_hash\n");
    return 1;
  }
  {
    SHA256_CTX c;
    const uint8_t p0 = 0x00;
    sha256_Init(&c);
    sha256_Update(&c, &p0, 1);
    sha256_Update(&c, img_hash, 32);
    sha256_Final(&c, leaf);
  }
  pq_merkle_fold(leaf, copath, COPATH_NODES, root);

  /* --- sign as the founder does: SLH-DSA over modelRoot, then Ed25519 over
   *     SHA256(modelRoot || slh_sig) so the EC half commits to the PQ half. --- */
  printf("signing modelRoot with 2 hybrid signature pairs...\n");
  for (int slot = 0; slot < PQ_SIG_COUNT; slot++) {
    size_t siglen = 0;
    static uint8_t sig[CRYPTO_BYTES];
    if (crypto_sign_signature(sig, &siglen, root, sizeof(root),
                              pq_sk[slot_key[slot]]) != 0 ||
        siglen != PQ_SLH_SIG_LEN) {
      printf("FAIL: crypto_sign_signature (siglen=%zu)\n", siglen);
      return 1;
    }
    memcpy(&image[off_slh[slot]], sig, PQ_SLH_SIG_LEN);

    uint8_t hash[32];
    SHA256_CTX ctx;
    sha256_Init(&ctx);
    sha256_Update(&ctx, root, sizeof(root));
    sha256_Update(&ctx, sig, PQ_SLH_SIG_LEN);
    sha256_Final(&ctx, hash);

    uint8_t ec_sig[64];
    ed25519_sign(hash, sizeof(hash), ec_sk[slot_key[slot]], ec_sig);
    memcpy(&image[off_ec[slot]], ec_sig, sizeof(ec_sig));
  }

  /* ---------------- positive ---------------- */
  uint8_t got_root[32];
  /* Exercise the real FIH contract, exactly as image_validate.c must: FIH_CALL
   * (seeds FIH_FAILURE, validates the CFI counter) then compare against
   * FIH_SUCCESS. Under profile MEDIUM success is a masked value (0x1AAAAAAA), so
   * a plain `!= 0` here would silently invert every verdict below. */
  FIH_DECLARE(fih_rc, FIH_FAILURE);
  FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL, pq_keys,
           ec_keys, NUM_KEYS, got_root);
  if (FIH_NOT_EQ(fih_rc, FIH_SUCCESS)) {
    printf("FAIL: genuine founder signature REJECTED\n");
    fails++;
  } else if (memcmp(got_root, root, 32) != 0) {
    printf("FAIL: pq_image_verify returned the wrong modelRoot\n");
    fails++;
  } else {
    printf("genuine hybrid 2-of-3 (keys 0,2) accepted, modelRoot matches: OK\n");
  }

  /* ---------------- negatives ---------------- */
  static uint8_t good[sizeof(image)];
  memcpy(good, image, image_len);
#define RESTORE() memcpy(image, good, image_len)
#define EXPECT_REJECT(label)                                                      \
  do {                                                                            \
    FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL,            \
             pq_keys, ec_keys, NUM_KEYS, NULL);                                    \
    if (FIH_EQ(fih_rc, FIH_SUCCESS)) {                                              \
      printf("FAIL: %s ACCEPTED\n", label);                                        \
      fails++;                                                                     \
    } else {                                                                       \
      printf("%s rejected: OK\n", label);                                           \
    }                                                                              \
    RESTORE();                                                                      \
  } while (0)

  image[off_slh[0]] ^= 0xFF;
  EXPECT_REJECT("tampered SLH-DSA signature");

  image[off_ec[0]] ^= 0xFF;
  EXPECT_REJECT("tampered Ed25519 signature");

  image[off_copath] ^= 0xFF;
  EXPECT_REJECT("tampered co-path (different modelRoot)");

  image[HDR_SIZE + 10] ^= 0xFF;
  EXPECT_REJECT("tampered payload (leaf changes)");

  /* Reordering the two (SLH, EC) pairs between slots must now be REJECTED: the
   * committed sigmask binds slot i to a specific key, so order is meaningful again
   * (unlike a derive-the-key scheme, where the same two signatures in either order
   * would be the same authorization). */
  {
    static uint8_t tmp[PQ_SLH_SIG_LEN];
    memcpy(tmp, &good[off_slh[0]], PQ_SLH_SIG_LEN);
    memcpy(&image[off_slh[0]], &good[off_slh[1]], PQ_SLH_SIG_LEN);
    memcpy(&image[off_slh[1]], tmp, PQ_SLH_SIG_LEN);
    uint8_t etmp[64];
    memcpy(etmp, &good[off_ec[0]], 64);
    memcpy(&image[off_ec[0]], &good[off_ec[1]], 64);
    memcpy(&image[off_ec[1]], etmp, 64);
    EXPECT_REJECT("reordered signature pairs (sigmask binds slot->key)");
  }

  /* Swap ONLY the EC halves, leaving the SLH halves in place. Every signature is
   * individually genuine, but slot i's Ed25519 now signs SHA256(root || the OTHER
   * slot's slh_sig), so no key can verify it. This is the PQ<->EC BINDING that
   * stops a PQ-signature substitution -- the reason the EC half signs the PQ half
   * rather than modelRoot alone. */
  memcpy(&image[off_ec[0]], &good[off_ec[1]], 64);
  memcpy(&image[off_ec[1]], &good[off_ec[0]], 64);
  EXPECT_REJECT("EC halves swapped (PQ<->EC binding broken)");

  /* A sigmask naming keys 0+1 while the signatures are from keys 0+2. The mask is
   * PROTECTED, so altering it also changes the image hash, the leaf and therefore
   * modelRoot -- the signatures no longer match anything. Rebuilt rather than
   * patched, since patching in place would leave an inconsistent image hash. */
  build_image(0x03);
  memcpy(&image[off_copath], copath, sizeof(copath));
  for (int slot = 0; slot < PQ_SIG_COUNT; slot++) {
    memcpy(&image[off_slh[slot]], &good[off_slh[slot]], PQ_SLH_SIG_LEN);
    memcpy(&image[off_ec[slot]], &good[off_ec[slot]], 64);
  }
  FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL, pq_keys,
           ec_keys, NUM_KEYS, NULL);
  if (FIH_EQ(fih_rc, FIH_SUCCESS)) {
    printf("FAIL: altered sigmask ACCEPTED\n");
    fails++;
  } else {
    printf("sigmask 0b011 vs signatures from keys 0,2 rejected: OK\n");
  }

  /* A single-key sigmask must not satisfy the 2-of-3 threshold. */
  build_image(0x01);
  memcpy(&image[off_copath], copath, sizeof(copath));
  FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL, pq_keys,
           ec_keys, NUM_KEYS, NULL);
  if (FIH_EQ(fih_rc, FIH_SUCCESS)) {
    printf("FAIL: single-key sigmask ACCEPTED (2-of-3 not enforced)\n");
    fails++;
  } else {
    printf("single-key sigmask rejected (2-of-3 enforced): OK\n");
  }

  /* ---- security counter (rollback protection input) ---- */
  {
    /* Absent must read as 0, not fail: any stored counter above 0 then refuses
     * the image, so absence can only ever be MORE restrictive. */
    g_sec_cnt = -1;
    build_image(0x05);
    memcpy(&image[off_copath], copath, sizeof(copath));
    uint32_t got = 0xdeadbeef;
    if (pq_image_security_counter(flat_read, &img, image_len, &got) != 0 ||
        got != 0) {
      printf("FAIL: absent security counter did not read as 0 (rc/val %u)\n",
             (unsigned)got);
      fails++;
    } else {
      printf("absent security counter reads as 0: OK\n");
    }

    /* Present, and byte-order correct: a big-endian read of 0x01020304 would
     * yield 0x04030201, which silently inverts the ordering of every release. */
    g_sec_cnt = 0x01020304;
    build_image(0x05);
    memcpy(&image[off_copath], copath, sizeof(copath));
    got = 0;
    if (pq_image_security_counter(flat_read, &img, image_len, &got) != 0 ||
        got != 0x01020304u) {
      printf("FAIL: security counter read as 0x%08x, expected 0x01020304\n",
             (unsigned)got);
      fails++;
    } else {
      printf("security counter read little-endian (0x01020304): OK\n");
    }

    /* It is PROTECTED, so it is inside the founder leaf: flipping it must break
     * the signature. This is what makes the counter unforgeable rather than
     * merely present. */
    image[off_sec_cnt] ^= 0xFF;
    FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL,
             pq_keys, ec_keys, NUM_KEYS, NULL);
    if (FIH_EQ(fih_rc, FIH_SUCCESS)) {
      printf("FAIL: tampered security counter ACCEPTED (not covered by the leaf)\n");
      fails++;
    } else {
      printf("tampered security counter rejected (inside the founder leaf): OK\n");
    }
    g_sec_cnt = -1;
  }

  /* A sigmask naming a key outside the pool must be rejected on range, not
   * silently indexed. */
  build_image(0x09); /* keys 0 and 3 -- key 3 does not exist */
  memcpy(&image[off_copath], copath, sizeof(copath));
  FIH_CALL(pq_image_verify, fih_rc, flat_read, &img, image_len, NULL, pq_keys,
           ec_keys, NUM_KEYS, NULL);
  if (FIH_EQ(fih_rc, FIH_SUCCESS)) {
    printf("FAIL: sigmask naming a key outside the pool ACCEPTED\n");
    fails++;
  } else {
    printf("sigmask naming out-of-pool key rejected: OK\n");
  }

  printf("\nRESULT: %s\n", fails == 0 ? "all founder signature checks OK" : "FAILURES");
  return fails != 0;
}
