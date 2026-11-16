/**
 * @file soc_ocv_poly.c
 * @brief SoC from OCV and temperature with degree-4 polynomials
 * (soc_ocv_poly.py).
 *
 * Per polynomial: x = (2 OCV - (min + max)) / (max - min) in Q15, Horner in
 * int32 with coefficients in 0.01 %; OCV clamped to the polynomial's range,
 * result clamped to 0..100 %. The generator checks sum|c| * 2^15 < 2^31, so no
 * intermediate overflows.
 */
#include "soc_ocv.h"
#include "soc_ocv_data.h"
#include "soc_ocv_internal.h"

#define Q15_ONE (32768)

/* SoC of polynomial k at ocv_mv, in 0.01 % units, clamped to 0..10000 */
static int32_t poly_node(uint8_t k, uint16_t ocv_mv) {
  const int32_t v_lo = (int32_t)soc_ocv_poly_vrange[k][0];
  const int32_t v_hi = (int32_t)soc_ocv_poly_vrange[k][1];
  int32_t v = (int32_t)ocv_mv;
  int32_t x_q15;
  int32_t acc;
  uint32_t c;

  if (v < v_lo) {
    v = v_lo;
  } else if (v > v_hi) {
    v = v_hi;
  } else {
    /* in range */
  }
  x_q15 =
      (((2 * v) - (v_lo + v_hi)) * Q15_ONE) / (v_hi - v_lo); /* -32768..32768 */
  acc = (int32_t)soc_ocv_poly_coef[k][SOC_OCV_POLY_COEFS - 1U];
  for (c = SOC_OCV_POLY_COEFS - 1U; c > 0U; c--) {
    acc = ((acc * x_q15) / Q15_ONE) + (int32_t)soc_ocv_poly_coef[k][c - 1U];
  }
  if (acc < 0) {
    acc = 0;
  } else if (acc > SOC_OCV_CPCT_FULL) {
    acc = SOC_OCV_CPCT_FULL;
  } else {
    /* in range */
  }
  return acc;
}

uint16_t soc_ocv_poly(uint16_t ocv_mv, int16_t temp_dc) {
  soc_ocv_tw_t tw;
  int32_t soc;

  soc_ocv_temp_weights(soc_ocv_poly_span, (uint8_t)SOC_OCV_POLY_TEMPS, temp_dc,
                       &tw);
  soc = poly_node(tw.a, ocv_mv);
  if (tw.num > 0) {
    soc = soc_ocv_blend(soc, poly_node(tw.b, ocv_mv), &tw);
  }
  return soc_ocv_to_permille(soc);
}
