/**
 * @file soc_ocv_temp.c
 * @brief Temperature-span blending (ocv_common.blend_spans in the Python
 * reference).
 */
#include "soc_ocv.h"
#include "soc_ocv_internal.h"

#define SPAN_TO_DC (5) /* 0.5 degC span units -> 0.1 degC */

void soc_ocv_temp_weights(const int8_t span[][2], uint8_t n, int16_t temp_dc,
                          soc_ocv_tw_t *tw) {
  const int32_t t = (int32_t)temp_dc;
  const uint8_t last = (uint8_t)(n - 1U);
  uint8_t j = 0U;
  int32_t lo_j;
  int32_t hi_j;

  /* first span that ends at or above t (or the last one) */
  while ((j < last) && (t > ((int32_t)span[j][1] * SPAN_TO_DC))) {
    j++;
  }
  lo_j = (int32_t)span[j][0] * SPAN_TO_DC;
  hi_j = (int32_t)span[j][1] * SPAN_TO_DC;

  if ((t >= lo_j) || (j == 0U) || (t > hi_j)) {
    /* inside span j, colder than every span, or hotter than every span */
    tw->a = j;
    tw->b = j;
    tw->num = 0;
    tw->den = 1;
  } else {
    /* in the gap between span j-1 and span j */
    const uint8_t a = (uint8_t)(j - 1U);
    const int32_t hi_a = (int32_t)span[a][1] * SPAN_TO_DC;
    tw->a = a;
    tw->b = j;
    tw->num = t - hi_a;
    tw->den = lo_j - hi_a;
  }
}

int32_t soc_ocv_blend(int32_t soc_a, int32_t soc_b, const soc_ocv_tw_t *tw) {
  /* soc <= 10000 and den < 2^15, so every product fits in int32 */
  const int32_t sum = (soc_a * (tw->den - tw->num)) + (soc_b * tw->num);
  return (sum + (tw->den / 2)) / tw->den;
}

uint16_t soc_ocv_to_permille(int32_t soc_cpct) {
  int32_t s = soc_cpct;

  if (s < 0) {
    s = 0;
  } else if (s > SOC_OCV_CPCT_FULL) {
    s = SOC_OCV_CPCT_FULL;
  } else {
    /* in range */
  }
  s = (s + 5) / 10;
  return (uint16_t)s;
}
