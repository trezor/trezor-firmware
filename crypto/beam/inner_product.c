#include "inner_product.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

void inner_product_modifier_init(inner_product_modifier_t *mod) {
  memset(mod->multiplier, 0, sizeof(mod->multiplier));
}

void inner_product_get_dot(secp256k1_scalar *out, const secp256k1_scalar *a,
                           const secp256k1_scalar *b) {
  *out = a[0];
  secp256k1_scalar_mul(out, out, &b[0]);

  secp256k1_scalar tmp;
  for (size_t i = 1; i < INNER_PRODUCT_N_DIM; i++) {
    tmp = a[i];
    secp256k1_scalar_mul(&tmp, &tmp, &b[i]);
    secp256k1_scalar_add(out, out, &tmp);
  }
}

void calculator_aggregator_init(_calculator_aggregator_t *ag, multi_mac_t *mm,
                                const _challenge_set_xset_t *x,
                                const _challenge_set_xset_t *x_inv,
                                const _calculator_modifier_expanded_t *mod,
                                int j, unsigned int i_cycle_trg) {
  ag->mm = mm;
  ag->mod = mod;
  ag->calc = NULL;
  ag->j = j;
  ag->i_cycle_trg = i_cycle_trg;
  ag->x[0] = x;
  ag->x[1] = x_inv;
}

void calculator_modifier_expanded_init(_calculator_modifier_expanded_t *mod_ex,
                                       const inner_product_modifier_t *mod) {
  const size_t count = sizeof(mod->multiplier) / sizeof(mod->multiplier[0]);
  for (size_t j = 0; j < count; j++) {
    mod_ex->use[j] = (NULL != mod->multiplier[j]);
    if (mod_ex->use[j]) {
      secp256k1_scalar_set_int(&mod_ex->pwr[j][0], 1U);
      for (size_t i = 1; i < INNER_PRODUCT_N_DIM; i++)
        secp256k1_scalar_mul(&mod_ex->pwr[j][i], &mod_ex->pwr[j][i - 1],
                             mod->multiplier[j]);
    }
  }
}

void calculator_modifier_expanded_set(
    const _calculator_modifier_expanded_t *mod_ex, secp256k1_scalar *dst,
    const secp256k1_scalar *src, int i, int j) {
  if (mod_ex->use[j])
    secp256k1_scalar_mul(dst, src, &mod_ex->pwr[j][i]);
  else
    *dst = *src;
}

void calculator_aggregator_proceed_rec(_calculator_aggregator_t *ag,
                                       uint32_t i_pos, uint32_t i_cycle,
                                       const secp256k1_scalar *k, uint32_t j) {
  if (ag->x[j]) {
    secp256k1_scalar k0 = *k;
    secp256k1_scalar_mul(&k0, &k0,
                         &ag->x[j]->val[INNER_PRODUCT_N_CYCLES - i_cycle]);

    calculator_aggregator_proceed(ag, i_pos, i_cycle - 1, &k0);
  } else
    calculator_aggregator_proceed(
        ag, i_pos, i_cycle - 1,
        k);  // in batch mode all inverses are already multiplied
}

void calculator_aggregator_proceed(_calculator_aggregator_t *ag, uint32_t i_pos,
                                   uint32_t i_cycle,
                                   const secp256k1_scalar *k) {
  if (i_cycle != ag->i_cycle_trg) {
    calculator_aggregator_proceed_rec(ag, i_pos, i_cycle, k, !ag->j);
    uint32_t n_step = 1 << (i_cycle - 1);
    calculator_aggregator_proceed_rec(ag, i_pos + n_step, i_cycle, k, ag->j);
  } else {
    if (ag->calc) {
      multi_mac_casual_init(&ag->mm->casual[ag->mm->n_casual++],
                            &ag->calc->gen[ag->j][i_pos], k);
    } else {
      // if (ag->batch_ctx) {...} else
      calculator_modifier_expanded_set(
          ag->mod, &ag->mm->k_prepared[ag->mm->n_prepared], k, i_pos, ag->j);
      ag->mm->prepared[ag->mm->n_prepared++] =
          (multi_mac_prepared_t *)get_generator_ipp(i_pos, ag->j, 0);
    }
  }
}

void inner_product_calculator_extract_LR(inner_product_calculator_t *calc,
                                         int j) {
  multi_mac_reset(&calc->mm);

  // Cross-term
  secp256k1_scalar *cross_trm = &calc->mm.k_prepared[calc->mm.n_prepared];
  calc->mm.prepared[calc->mm.n_prepared++] =
      (multi_mac_prepared_t *)get_generator_dot_ipp();

  secp256k1_scalar_clear(cross_trm);

  for (uint32_t i = 0; i < calc->n; i++) {
    const secp256k1_scalar *a = &calc->src[j][i];
    const secp256k1_scalar *b = &calc->src[!j][calc->n + i];
    secp256k1_scalar r;
    secp256k1_scalar_mul(&r, a, b);
    secp256k1_scalar_add(cross_trm, cross_trm, &r);
  }

  secp256k1_scalar_mul(cross_trm, cross_trm, &calc->cs.dot_multiplier);

  // other
  for (int jSrc = 0; jSrc < 2; jSrc++) {
    uint32_t off0 = (jSrc == j) ? 0 : calc->n;
    uint32_t off1 = (jSrc == j) ? calc->n : 0;

    for (uint32_t i = 0; i < calc->n; i++) {
      const secp256k1_scalar *v = &calc->src[jSrc][i + off0];

      _calculator_aggregator_t aggr;
      calculator_aggregator_init(&aggr, &calc->mm, &calc->cs.x[0],
                                 &calc->cs.x[1], &calc->mod, jSrc,
                                 INNER_PRODUCT_N_CYCLES - calc->i_cycle);

      if (calc->i_cycle > INNER_PRODUCT_I_CYCLE_0) aggr.calc = calc;

      calculator_aggregator_proceed(&aggr, i + off1, calc->gen_order, v);
    }
  }
}

void inner_product_calculator_condense(inner_product_calculator_t *calc) {
  // Vectors
  for (int j = 0; j < 2; j++)
    for (uint32_t i = 0; i < calc->n; i++) {
      // dst and src need not to be distinct
      secp256k1_scalar r;
      secp256k1_scalar_mul(&calc->val[j][i], &calc->src[j][i],
                           &calc->cs.x[j].val[calc->i_cycle]);
      secp256k1_scalar_mul(&r, &calc->src[j][calc->n + i],
                           &calc->cs.x[!j].val[calc->i_cycle]);
      secp256k1_scalar_add(&calc->val[j][i], &calc->val[j][i], &r);
    }

  // Points
  switch (calc->i_cycle) {
    case INNER_PRODUCT_I_CYCLE_0:
      // further compression points (casual)
      // Currently according to benchmarks - not necessary
      break;
    case INNER_PRODUCT_N_CYCLES -
        1:  // last iteration - no need to condense points
    default:
      return;
  }

  for (int j = 0; j < 2; j++)
    for (uint32_t i = 0; i < calc->n; i++) {
      multi_mac_reset(&calc->mm);

      secp256k1_gej *g0 = &calc->gen[j][i];
      _calculator_aggregator_t aggr;
      calculator_aggregator_init(&aggr, &calc->mm, &calc->cs.x[0],
                                 &calc->cs.x[1], &calc->mod, j,
                                 INNER_PRODUCT_N_CYCLES - calc->i_cycle - 1);

      if (calc->i_cycle > INNER_PRODUCT_I_CYCLE_0) aggr.calc = calc;

      secp256k1_scalar k;
      secp256k1_scalar_set_int(&k, 1U);
      calculator_aggregator_proceed(&aggr, i, calc->gen_order, &k);
      multi_mac_calculate(&calc->mm, g0);
    }

  calc->gen_order = INNER_PRODUCT_N_CYCLES - calc->i_cycle - 1;
}

void inner_product_create(inner_product_t *in, SHA256_CTX *oracle,
                          secp256k1_gej *ab, const secp256k1_scalar *dot_ab,
                          const secp256k1_scalar *a, const secp256k1_scalar *b,
                          inner_product_modifier_t *mod) {
  inner_product_calculator_t calc;
  calculator_modifier_expanded_init(&calc.mod, mod);
  multi_mac_with_bufs_alloc(&calc.mm, 8, 128);
  calc.gen_order = INNER_PRODUCT_N_CYCLES;
  calc.src[0] = a;
  calc.src[1] = b;

  if (ab) {
    for (uint32_t j = 0; j < 2; j++) {
      for (uint32_t i = 0; i < INNER_PRODUCT_N_DIM; i++, calc.mm.n_prepared++) {
        calc.mm.prepared[calc.mm.n_prepared] =
            (multi_mac_prepared_t *)get_generator_ipp(i, j, 0);
        calculator_modifier_expanded_set(
            &calc.mod, &calc.mm.k_prepared[calc.mm.n_prepared], &calc.src[j][i],
            i, j);
      }
    }
    multi_mac_calculate(&calc.mm, ab);
    sha256_oracle_update_gej(oracle, ab);
  }

  sha256_oracle_update_sk(oracle, dot_ab);
  scalar_create_nnz(oracle, &calc.cs.dot_multiplier);

  secp256k1_gej comm;

  for (calc.i_cycle = 0; calc.i_cycle < INNER_PRODUCT_N_CYCLES;
       calc.i_cycle++) {
    calc.n = INNER_PRODUCT_N_DIM >> (calc.i_cycle + 1);

    scalar_create_nnz(oracle, &calc.cs.x[0].val[calc.i_cycle]);
    secp256k1_scalar_inverse(&calc.cs.x[1].val[calc.i_cycle],
                             &calc.cs.x[0].val[calc.i_cycle]);

    for (int j = 0; j < 2; j++) {
      inner_product_calculator_extract_LR(&calc, j);
      multi_mac_calculate(&calc.mm, &comm);

      point_t *pt = &in->LR[calc.i_cycle][j];
      export_gej_to_point(&comm, pt);
      sha256_oracle_update_pt(oracle, pt);
    }

    inner_product_calculator_condense(&calc);

    if (!calc.i_cycle)
      for (int j = 0; j < 2; j++) calc.src[j] = calc.val[j];
  }

  for (int i = 0; i < 2; i++) in->condensed[i] = calc.val[i][0];

  multi_mac_with_bufs_free(&calc.mm);
}
