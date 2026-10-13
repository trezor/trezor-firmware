/*
 * Host cross-validation for the nRF founder-tree device verify.
 *
 * Compiles the real nrf_image.c (image hash, fold, push gate) and the nRF's own
 * verifier (mcuboot image_pq.c, PQ_HOST_TEST) with one host SHA-256 and replays
 * the vectors from gen_nrf_vector.py, so all three implementations (STM, nRF,
 * Python signer) are compared byte-for-byte. Build: run_nrf.sh.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sha2.h"

#include "shims_nrf.h"

#include <io/nrf_image.h> /* nrf_image_model_id (the model-id TLV) */

/* The nRF's own founder verify (mcuboot boot/bootutil/src/image_pq.c). */
#include "bootutil/image_pq.h"

/* trezor-crypto's consteq() fault hook; the bootloader's real one is in
 * image_validate.c. */
void tc_fault_handler(const char *msg) {
  printf("FAULT: %s\n", msg);
  abort();
}

/* Unpack a wire artifact (proof_count || co_path || image) and run the two
 * device checks on it: fold to modelRoot, then pin the model id. The unpacking
 * is harness scaffolding: the bootloader takes co_path/image_len from its
 * staging descriptor and calls the same two primitives. */
static secbool harness_ota_gate(const uint8_t *artifact, size_t artifact_len,
                                const merkle_proof_node_t *trusted_model_root,
                                const uint8_t device_model_id[4],
                                const uint8_t **out_image,
                                size_t *out_image_len) {
  if (out_image != NULL) {
    *out_image = NULL;
  }
  if (out_image_len != NULL) {
    *out_image_len = 0;
  }
  if (artifact_len < sizeof(uint32_t)) {
    return secfalse;
  }
  uint32_t proof_count;
  memcpy(&proof_count, artifact, sizeof(proof_count));
  if (proof_count > MODEL_TREE_MAX_PROOF_NODES) {
    return secfalse;
  }
  size_t header_bytes =
      sizeof(uint32_t) + (size_t)proof_count * sizeof(merkle_proof_node_t);
  if (header_bytes >= artifact_len) {
    return secfalse;
  }
  const merkle_proof_node_t *co_path =
      (const merkle_proof_node_t *)(artifact + sizeof(uint32_t));
  const uint8_t *image = artifact + header_bytes;
  size_t image_len = artifact_len - header_bytes;

  if (nrf_image_verify_in_tree(image, image_len, co_path, proof_count,
                               trusted_model_root) != sectrue) {
    return secfalse;
  }
  uint8_t model_id[4];
  if (!nrf_image_model_id(image, image_len, model_id)) {
    return secfalse;
  }
  if (memcmp(model_id, device_model_id, 4) != 0) {
    return secfalse;
  }
  if (out_image != NULL) {
    *out_image = image;
  }
  if (out_image_len != NULL) {
    *out_image_len = image_len;
  }
  return sectrue;
}

/* Reader shim: a flash_area on device, a bounds-checked flat buffer here. */
struct flat_image {
  const uint8_t *buf;
  uint32_t len;
};

static int flat_read(void *ctx, uint32_t off, void *dst, uint32_t len) {
  const struct flat_image *img = (const struct flat_image *)ctx;
  if ((uint64_t)off + len > (uint64_t)img->len) {
    return -1;
  }
  memcpy(dst, img->buf + off, len);
  return 0;
}

int main(void) {
  merkle_proof_node_t root;
  memcpy(root.bytes, NRF_MODEL_ROOT, 32);
  int fails = 0;

  /* model-id parse sanity */
  uint8_t mid[4];
  if (nrf_image_model_id(NRF_IMAGE, NRF_IMAGE_LEN, mid) &&
      memcmp(mid, DEVICE_MODEL_ID, 4) == 0) {
    printf("model-id TLV parse: %.4s OK\n", mid);
  } else {
    printf("FAIL: model-id parse\n");
    fails++;
  }

  /* genuine OTA artifact: parses, folds, model id matches; out_image is the
   * inner MCUboot image */
  const uint8_t *img = NULL;
  size_t img_len = 0;
  if (harness_ota_gate(NRF_OTA, NRF_OTA_LEN, &root, DEVICE_MODEL_ID, &img,
                       &img_len) != sectrue) {
    printf("FAIL: genuine OTA artifact rejected\n");
    fails++;
  } else if (img_len != NRF_IMAGE_LEN ||
             memcmp(img, NRF_IMAGE, NRF_IMAGE_LEN) != 0) {
    printf("FAIL: OTA out_image != embedded NRF_IMAGE\n");
    fails++;
  } else {
    printf("genuine OTA verify (parse + fold + model id, out_image): OK\n");
  }

  /* classic image: tamper below prot_end (inside the image hash) must break
   * the fold */
  static uint8_t bad_ota[sizeof(NRF_OTA)];
  memcpy(bad_ota, NRF_OTA, NRF_OTA_LEN);
  bad_ota[NRF_OTA_IMAGE_OFF + NRF_IMAGE_PROT_END / 2] ^= 0xFF;
  if (harness_ota_gate(bad_ota, NRF_OTA_LEN, &root, DEVICE_MODEL_ID, &img,
                       &img_len) != secfalse) {
    printf("FAIL: classic tampered (body) OTA accepted\n");
    fails++;
  } else if (img != NULL || img_len != 0) {
    printf("FAIL: reject did not clear out_image\n");
    fails++;
  } else {
    printf("classic: tamper in body rejected (fold): OK\n");
  }

  /* Tamper in the unprotected area (the classic signature TLV): the fold must
   * still pass, since the leaf stops at the protected TLVs. Pins the boundary;
   * the push gate, not the fold, rejects this image. */
  memcpy(bad_ota, NRF_OTA, NRF_OTA_LEN);
  bad_ota[NRF_OTA_LEN - 1] ^= 0xFF;
  if (harness_ota_gate(bad_ota, NRF_OTA_LEN, &root, DEVICE_MODEL_ID, NULL,
                       NULL) != sectrue) {
    printf("FAIL: classic unprotected tamper broke the fold "
           "(leaf boundary moved?)\n");
    fails++;
  } else {
    printf("classic: unprotected tamper still folds (leaf stops at prot): OK\n");
  }

  /* PQ-native image: genuine artifact folds */
  if (harness_ota_gate(PQ_OTA, PQ_OTA_LEN, &root, DEVICE_MODEL_ID, NULL,
                       NULL) != sectrue) {
    printf("FAIL: genuine PQ-native OTA rejected\n");
    fails++;
  } else {
    printf("PQ-native: genuine OTA verify (leaf == image hash): OK\n");
  }

  /* PQ-native, tamper inside the hashed range: must break the fold */
  static uint8_t bad_pq[sizeof(PQ_OTA)];
  memcpy(bad_pq, PQ_OTA, PQ_OTA_LEN);
  bad_pq[NRF_OTA_IMAGE_OFF + PQ_IMAGE_PROT_END / 2] ^= 0xFF;
  if (harness_ota_gate(bad_pq, PQ_OTA_LEN, &root, DEVICE_MODEL_ID, NULL,
                       NULL) != secfalse) {
    printf("FAIL: PQ-native tamper inside covered range accepted\n");
    fails++;
  } else {
    printf("PQ-native: tamper inside covered range rejected: OK\n");
  }

  /* PQ-native, tamper in the PQ material: still folds by design (that material
   * signs modelRoot, so it cannot be inside its own leaf); the push gate covers
   * it below. */
  memcpy(bad_pq, PQ_OTA, PQ_OTA_LEN);
  bad_pq[PQ_OTA_LEN - 1] ^= 0xFF;
  if (harness_ota_gate(bad_pq, PQ_OTA_LEN, &root, DEVICE_MODEL_ID, NULL,
                       NULL) != sectrue) {
    printf("FAIL: PQ-native PQ-material tamper broke the fold\n");
    fails++;
  } else {
    printf("PQ-native: PQ-material tamper still folds (by design): OK\n");
  }

  /* ---- the push gate: what the fold cannot cover ----------------------------
   * The expected signature records are this release's boot header records,
   * byte-identical to the genuine image's here. */
  {
    const uint8_t *e_slh0 = NULL, *e_slh1 = NULL, *e_ec0 = NULL, *e_ec1 = NULL;
    int have =
        (nrf_image_find_unprot_tlv(PQ_IMAGE, PQ_IMAGE_LEN, NRF_PQ_TLV_SLH_SIG_0,
                                   &e_slh0) == NRF_PQ_SLH_SIG_LEN) &&
        (nrf_image_find_unprot_tlv(PQ_IMAGE, PQ_IMAGE_LEN, NRF_PQ_TLV_SLH_SIG_1,
                                   &e_slh1) == NRF_PQ_SLH_SIG_LEN) &&
        (nrf_image_find_unprot_tlv(PQ_IMAGE, PQ_IMAGE_LEN, NRF_PQ_TLV_EC_SIG_0,
                                   &e_ec0) == NRF_PQ_EC_SIG_LEN) &&
        (nrf_image_find_unprot_tlv(PQ_IMAGE, PQ_IMAGE_LEN, NRF_PQ_TLV_EC_SIG_1,
                                   &e_ec1) == NRF_PQ_EC_SIG_LEN);
    if (!have) {
      printf("FAIL: could not read the PQ signature records from the fixture\n");
      fails++;
    }

    /* genuine PQ-native image -> safe to push */
    if (nrf_image_verify_for_push(PQ_IMAGE, PQ_IMAGE_LEN, &root, e_slh0, e_slh1,
                                  e_ec0, e_ec1) != sectrue) {
      printf("FAIL: push gate rejected a genuine PQ-native image\n");
      fails++;
    } else {
      printf("push gate: genuine PQ-native image accepted: OK\n");
    }

    /* rogue TLV: folds and would re-verify, yet MCUboot rejects it on its
     * unprotected-TLV whitelist; the gate must catch it */
    if (nrf_image_verify_for_push(PQ_IMAGE_ROGUE, PQ_IMAGE_ROGUE_LEN, &root,
                                  e_slh0, e_slh1, e_ec0, e_ec1) != secfalse) {
      printf("FAIL: push gate ACCEPTED a rogue TLV (brick path still open)\n");
      fails++;
    } else {
      printf("push gate: rogue TLV rejected (fold alone accepted it): OK\n");
    }

    /* tampered signature record -> not this release's material */
    static uint8_t bad_sig[sizeof(PQ_IMAGE)];
    memcpy(bad_sig, PQ_IMAGE, PQ_IMAGE_LEN);
    bad_sig[PQ_IMAGE_LEN - 1] ^= 0xFF;
    if (nrf_image_verify_for_push(bad_sig, PQ_IMAGE_LEN, &root, e_slh0, e_slh1,
                                  e_ec0, e_ec1) != secfalse) {
      printf("FAIL: push gate ACCEPTED tampered PQ material\n");
      fails++;
    } else {
      printf("push gate: tampered PQ material rejected: OK\n");
    }

    /* a classic image is gated against its own scheme; shims_nrf.h links
     * ed25519-donna so the acceptance predicate runs for real */
    if (nrf_image_verify_for_push(NRF_IMAGE, NRF_IMAGE_LEN, &root, e_slh0,
                                  e_slh1, e_ec0, e_ec1) != sectrue) {
      printf("FAIL: push gate rejected a classic image (should be a no-op)\n");
      fails++;
    } else {
      printf("push gate: classic image accepted (own-scheme predicate): OK\n");
    }

    /* rogue TLV in a classic image: its signatures verify and the fold passes,
     * only the classic shape whitelist sees it */
    if (nrf_image_verify_for_push(NRF_IMAGE_ROGUE, NRF_IMAGE_ROGUE_LEN, &root,
                                  e_slh0, e_slh1, e_ec0, e_ec1) != secfalse) {
      printf("FAIL: push gate ACCEPTED a classic image with a rogue TLV\n");
      fails++;
    } else {
      printf("push gate: rogue TLV in a classic image rejected (shape): OK\n");
    }

    /* TLV 0x10 not matching the computed hash: the record is unprotected, so
     * only comparing its value sees it. Skipping that bricks: MCUboot rejects
     * after the STM has erased the nRF's only slot. Both schemes. */
    if (nrf_image_verify_for_push(PQ_IMAGE_BADHASH, PQ_IMAGE_BADHASH_LEN, &root,
                                  e_slh0, e_slh1, e_ec0, e_ec1) != secfalse) {
      printf("FAIL: push gate ACCEPTED a PQ image whose 0x10 is wrong\n");
      fails++;
    } else {
      printf("push gate: corrupt 0x10 in a PQ image rejected: OK\n");
    }
    if (nrf_image_verify_for_push(NRF_IMAGE_BADHASH, NRF_IMAGE_BADHASH_LEN,
                                  &root, e_slh0, e_slh1, e_ec0,
                                  e_ec1) != secfalse) {
      printf("FAIL: push gate ACCEPTED a classic image whose 0x10 is wrong\n");
      fails++;
    } else {
      printf("push gate: corrupt 0x10 in a classic image rejected: OK\n");
    }

    /* ---- bounds discipline on the unauthenticated lengths ----------------
     * it_tlv_tot and the unprotected record lengths are invisible to the fold
     * (the generator asserts it), so the parser's bounds checks are the only
     * defence. STM and nRF must agree, or a push erases the co-processor's
     * only slot for an image the nRF then rejects. */
    for (unsigned i = 0; i < PQ_BOUNDS_COUNT; i++) {
      const unsigned char *img = PQ_BOUNDS[i].img;
      const unsigned int len = PQ_BOUNDS[i].len;
      struct flat_image fi = {img, len};
      bool present = false;

      secbool stm = nrf_image_verify_for_push(img, len, &root, e_slh0, e_slh1,
                                              e_ec0, e_ec1);
      int nrf = pq_region_shape_ok(flat_read, &fi, len, &present);

      if (stm != secfalse) {
        printf("FAIL: STM push gate ACCEPTED: %s\n", PQ_BOUNDS[i].what);
        fails++;
      } else if (nrf == 0 && present) {
        printf("FAIL: nRF accepted what the STM refused (they must agree): %s\n",
               PQ_BOUNDS[i].what);
        fails++;
      } else {
        printf("bounds: %s rejected by both: OK\n", PQ_BOUNDS[i].what);
      }
    }

    /* ---- the classic acceptance predicate, end to end ---------------------
     * Real Ed25519 against the pool; each negative breaks exactly one thing
     * the fold cannot see. */
    struct {
      const unsigned char *img;
      unsigned int len;
      const char *what;
    } bad[] = {
        {NRF_IMAGE_BADSIG0, NRF_IMAGE_BADSIG0_LEN, "corrupt signature slot 0"},
        {NRF_IMAGE_BADSIG1, NRF_IMAGE_BADSIG1_LEN, "corrupt signature slot 1"},
        {NRF_IMAGE_SWAPPED, NRF_IMAGE_SWAPPED_LEN,
         "signatures swapped between slots"},
        {NRF_IMAGE_WRONGMASK, NRF_IMAGE_WRONGMASK_LEN,
         "sigmask names keys that did not sign"},
        {NRF_IMAGE_ILLEGALMASK, NRF_IMAGE_ILLEGALMASK_LEN,
         "illegal sigmask (not 2-of-3)"},
        {NRF_IMAGE_OUTOFPOOL, NRF_IMAGE_OUTOFPOOL_LEN,
         "sigmask names a key outside the pool"},
    };
    for (unsigned i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
      if (nrf_image_verify_for_push(bad[i].img, bad[i].len, &root, e_slh0,
                                    e_slh1, e_ec0, e_ec1) != secfalse) {
        printf("FAIL: predicate ACCEPTED a classic image with %s\n",
               bad[i].what);
        fails++;
      } else {
        printf("predicate: %s rejected: OK\n", bad[i].what);
      }
    }
  }

  /* ---- third implementation: the nRF's own (mcuboot image_pq.c) ------------
   * Its image hash, leaf and fold must agree with the STM's and Python's
   * byte-for-byte; a divergence is otherwise silent. */
  {
    struct {
      const uint8_t *buf;
      uint32_t len;
    } shapes[] = {
        {NRF_IMAGE, NRF_IMAGE_LEN}, /* classic   */
        {PQ_IMAGE, PQ_IMAGE_LEN},   /* PQ-native */
    };
    const unsigned char (*proofs[])[32] = {NRF_PROOF, PQ_PROOF};
    const unsigned int counts[] = {NRF_PROOF_COUNT, PQ_PROOF_COUNT};
    const char *names[] = {"classic", "PQ-native"};

    for (int i = 0; i < 2; i++) {
      struct flat_image src = {shapes[i].buf, shapes[i].len};

      /* 1. same image hash as Python/STM -- this is the leaf value */
      uint8_t nrf_hash[32];
      uint8_t stm_hash[32];
      if (pq_image_hash(flat_read, &src, shapes[i].len, nrf_hash) != 0) {
        printf("FAIL: nRF pq_image_hash(%s) failed\n", names[i]);
        fails++;
        continue;
      }
      if (nrf_image_hash(shapes[i].buf, shapes[i].len, stm_hash) != sectrue) {
        printf("FAIL: STM nrf_image_hash(%s) failed\n", names[i]);
        fails++;
        continue;
      }
      if (memcmp(nrf_hash, stm_hash, 32) != 0) {
        printf("FAIL: nRF image hash != STM image hash (%s)\n", names[i]);
        fails++;
        continue;
      }

      /* 2. same leaf: H(0x00 || coproc_slot). The slot is built once here and
       *    fed to both sides; what is checked is that both fold the same bytes
       *    to the root Python signed. */
      coproc_slot_t slot;
      memset(&slot, 0, sizeof(slot));
      memcpy(slot.tag, COPROC_SLOT_TAG, sizeof(slot.tag));
      memcpy(slot.model, DEVICE_MODEL_ID, sizeof(slot.model));
      slot.kind = (uint8_t)COPROC_KIND_NRF;
      slot.index = 0;
      memcpy(slot.digest, nrf_hash, sizeof(slot.digest));

      uint8_t nrf_leaf[32];
      merkle_proof_node_t stm_leaf;
      {
        SHA256_CTX c;
        const uint8_t p0 = 0x00;
        sha256_Init(&c);
        sha256_Update(&c, &p0, 1);
        sha256_Update(&c, (const uint8_t *)&slot, sizeof(slot));
        sha256_Final(&c, nrf_leaf);
      }
      merkle_leaf_hash((const uint8_t *)&slot, sizeof(slot), &stm_leaf);
      if (memcmp(nrf_leaf, stm_leaf.bytes, 32) != 0) {
        printf("FAIL: nRF leaf != STM leaf (%s)\n", names[i]);
        fails++;
        continue;
      }

      /* 2b. role binding: roots signed over slots differing only in kind/index
       *     must not fold, because the verifier builds those from its own build
       *     configuration; nothing else in the system catches them. */
      if (i == 0) {
        uint8_t r[32];
        merkle_proof_node_t l;
        merkle_leaf_hash((const uint8_t *)&slot, sizeof(slot), &l);
        pq_merkle_fold(l.bytes, (const uint8_t *)proofs[i], counts[i], r);
        if (memcmp(r, NRF_WRONG_INDEX_ROOT, 32) == 0) {
          printf("FAIL: slot folds to the wrong-INDEX root\n");
          fails++;
        }
        if (memcmp(r, NRF_WRONG_KIND_ROOT, 32) == 0) {
          printf("FAIL: slot folds to the wrong-KIND root\n");
          fails++;
        }
        if (memcmp(NRF_WRONG_INDEX_ROOT, NRF_MODEL_ROOT, 32) == 0 ||
            memcmp(NRF_WRONG_KIND_ROOT, NRF_MODEL_ROOT, 32) == 0) {
          printf("FAIL: role fields do not affect the root (binding absent)\n");
          fails++;
        } else {
          printf(
              "role binding: wrong index and wrong kind both give a DIFFERENT "
              "modelRoot: OK\n");
        }
      }

      /* 3. same fold result: nRF folds to the signed modelRoot */
      uint8_t nrf_root[32];
      pq_merkle_fold(nrf_leaf, (const uint8_t *)proofs[i], counts[i], nrf_root);
      if (memcmp(nrf_root, NRF_MODEL_ROOT, 32) != 0) {
        printf("FAIL: nRF fold != modelRoot (%s)\n", names[i]);
        fails++;
        continue;
      }
      printf("nRF impl (%s): image hash + leaf + fold == STM/Python: OK\n",
             names[i]);
    }

    /* the nRF must reject a malformed image too, not hash whatever is there */
    struct flat_image junk = {(const uint8_t *)"not-an-mcuboot-image", 20};
    uint8_t junk_hash[32];
    if (pq_image_hash(flat_read, &junk, 20, junk_hash) == 0) {
      printf("FAIL: nRF pq_image_hash accepted a malformed image\n");
      fails++;
    } else {
      printf("nRF impl: malformed image rejected: OK\n");
    }

    /* ---- legacy sigmask -> key slots, exhaustive against MCUboot's logic ----
     * The legacy map is a bespoke 2-of-3 (not "i-th lowest set bit"), so it is
     * mirrored independently here and compared over all 256 masks, illegal
     * ones included. */
    {
      int mismatches = 0;
      for (unsigned m = 0; m < 256; m++) {
        const uint8_t mask = (uint8_t)m;
        /* independent mirror of image_validate.c's !CONFIG_BOOT_PQ_SECURE_BOOT
         * path */
        int e0 = (mask & (1u << 0)) ? 0 : 1;
        int e1 = (mask & (1u << 2)) ? 2 : 1;
        bool expect_ok = (__builtin_popcount((unsigned)mask) == 2) &&
                         ((mask & (uint8_t)~((1u << 3) - 1u)) == 0) &&
                         (e0 != e1);

        int got[2] = {-1, -1};
        secbool ok = nrf_image_legacy_sig_slots(mask, 3, got);
        if ((ok == sectrue) != expect_ok ||
            (expect_ok && (got[0] != e0 || got[1] != e1))) {
          if (mismatches++ == 0) {
            printf("FAIL: legacy sig slots differ for mask 0x%02x "
                   "(ok=%d want=%d, got {%d,%d} want {%d,%d})\n",
                   mask, ok == sectrue, expect_ok, got[0], got[1], e0, e1);
            fails++;
          }
        }
      }
      if (mismatches == 0) {
        printf("legacy sigmask -> key slots: matches MCUboot for all 256 masks: OK\n");
      }
    }

    /* ---- shape check: the rogue-TLV gap the fold cannot see ----------------
     */
    bool present = false;
    struct flat_image good_pq = {PQ_IMAGE, PQ_IMAGE_LEN};
    if (pq_region_shape_ok(flat_read, &good_pq, PQ_IMAGE_LEN, &present) != 0 ||
        !present) {
      printf("FAIL: genuine founder region rejected by shape check\n");
      fails++;
    } else {
      printf("shape check: genuine founder region accepted (present): OK\n");
    }

    /* a classic image has no founder material -> present=false */
    struct flat_image classic = {NRF_IMAGE, NRF_IMAGE_LEN};
    present = true;
    if (pq_region_shape_ok(flat_read, &classic, NRF_IMAGE_LEN, &present) != 0 ||
        present) {
      printf("FAIL: classic image mishandled by shape check\n");
      fails++;
    } else {
      printf("shape check: classic image -> no founder material: OK\n");
    }

    /* the rogue image still folds (leaf untouched); the shape check must reject
     * it, as MCUboot would */
    if (harness_ota_gate(PQ_OTA_ROGUE, PQ_OTA_ROGUE_LEN, &root, DEVICE_MODEL_ID,
                         NULL, NULL) != sectrue) {
      printf("FAIL: rogue-TLV premise broken (it should still fold)\n");
      fails++;
    } else {
      printf("rogue TLV: still folds to modelRoot (fold alone is blind): OK\n");
    }
    struct flat_image rogue = {PQ_IMAGE_ROGUE, PQ_IMAGE_ROGUE_LEN};
    if (pq_region_shape_ok(flat_read, &rogue, PQ_IMAGE_ROGUE_LEN, NULL) == 0) {
      printf("FAIL: shape check ACCEPTED a rogue TLV (brick path open)\n");
      fails++;
    } else {
      printf("shape check: rogue TLV in founder region rejected: OK\n");
    }
  }

  /* a truncated / non-MCUboot image must be rejected outright, not hashed */
  if (nrf_image_verify_in_tree((const uint8_t *)"not-an-mcuboot-image", 20,
                               (const merkle_proof_node_t *)NRF_PROOF,
                               NRF_PROOF_COUNT, &root) != secfalse) {
    printf("FAIL: malformed image accepted\n");
    fails++;
  } else {
    printf("malformed image rejected (bad magic / signed-region parse): OK\n");
  }

  /* Another model's OTA, slotted under this model so that it folds (the
   * misissuance case): rejected on the model-id TLV alone. */
  if (harness_ota_gate(OTHER_OTA, OTHER_OTA_LEN, &root, DEVICE_MODEL_ID, NULL,
                       NULL) != secfalse) {
    printf("FAIL: other model's OTA accepted (cross-model!)\n");
    fails++;
  } else {
    printf("other model's OTA rejected on model id (it folds): OK\n");
  }
  /* Premise: the same artifact passes when compared against its own model id,
   * so the rejection above is the model-id comparison and nothing else. */
  if (harness_ota_gate(OTHER_OTA, OTHER_OTA_LEN, &root, OTHER_MODEL_ID, NULL,
                       NULL) != sectrue) {
    printf("FAIL: other model's OTA does not fold -- the model-id negative "
           "above is vacuous\n");
    fails++;
  } else {
    printf("other model's OTA folds under this tree (premise holds): OK\n");
  }

  /* Not tested here: an oversized proof_count. nrf_staging.c and wf_nrf_ota.c
   * bound it before the primitives see a co_path; boot_header_verify_slot
   * itself trusts the count. */

  printf("\nRESULT: %s\n",
         fails == 0 ? "C matches Python, all rejects OK" : "FAILURES");
  return fails ? 1 : 0;
}
