/**
 * @file soc_ocv_internal.h
 * @brief Temperature-span blending shared by the lookup-table and polynomial estimators.
 */
#ifndef SOC_OCV_INTERNAL_H
#define SOC_OCV_INTERNAL_H

#include <stdint.h>

#include "soc_ocv.h"

/** 100 % SoC in the 0.01 % units used inside the estimators. */
#define SOC_OCV_CPCT_FULL ((int32_t)SOC_OCV_FULL * 10)

/** Result of the temperature step: SoC = curve a, or a blend of curves a and b. */
typedef struct
{
    uint8_t a;   /**< first curve */
    uint8_t b;   /**< second curve (== a when no blend) */
    int32_t num; /**< weight of curve b = num / den, 0 <= num < den */
    int32_t den;
} soc_ocv_tw_t;

/** Curves and weight for temp_dc (0.1 degC) from n spans [k][0..1] in 0.5 degC units. */
void soc_ocv_temp_weights(const int8_t span[][2], uint8_t n, int16_t temp_dc, soc_ocv_tw_t *tw);

/** Blend two SoC values (0.01 % units, >= 0) with the weight in tw; rounded. */
int32_t soc_ocv_blend(int32_t soc_a, int32_t soc_b, const soc_ocv_tw_t *tw);

/** 0.01 % units -> 0.1 % units, rounded and clamped to 0..SOC_OCV_FULL. */
uint16_t soc_ocv_to_permille(int32_t soc_cpct);

#endif /* SOC_OCV_INTERNAL_H */
