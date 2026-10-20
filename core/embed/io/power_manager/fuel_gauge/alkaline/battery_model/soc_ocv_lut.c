/**
 * @file soc_ocv_lut.c
 * @brief SoC from OCV and temperature with 20-point lookup tables (soc_ocv_lut.py).
 *
 * Per table: linear interpolation between evenly spaced points, exact in integer arithmetic;
 * OCV outside the table's range clamps to its end values (0 % / 100 %).
 */
#include "soc_ocv.h"
#include "soc_ocv_data.h"
#include "soc_ocv_internal.h"

#define HALF_PCT_TO_CPCT (50)   /* 0.5 % table units -> 0.01 % */

/* SoC of table k at ocv_mv, in 0.01 % units */
static int32_t lut_node(uint8_t k, uint16_t ocv_mv)
{
    const int32_t v_lo = (int32_t)soc_ocv_lut_vrange[k][0];
    const int32_t v_hi = (int32_t)soc_ocv_lut_vrange[k][1];
    const int32_t width = v_hi - v_lo;                       /* > 0, checked by the generator */
    const int32_t last = (int32_t)SOC_OCV_LUT_POINTS - 1;
    int32_t v = (int32_t)ocv_mv;
    int32_t pos;
    int32_t i;
    int32_t q_num;                                          /* SoC x width, 0.5 % units */

    if (v < v_lo)
    {
        v = v_lo;
    }
    else if (v > v_hi)
    {
        v = v_hi;
    }
    else
    {
        /* in range */
    }
    pos = (v - v_lo) * last;                                 /* position x width */
    i = pos / width;
    if (i >= last)
    {
        q_num = (int32_t)soc_ocv_lut_soc[k][last] * width;
    }
    else
    {
        const int32_t q0 = (int32_t)soc_ocv_lut_soc[k][i];
        const int32_t q1 = (int32_t)soc_ocv_lut_soc[k][i + 1];
        q_num = (q0 * width) + ((pos - (i * width)) * (q1 - q0));
    }
    return ((q_num * HALF_PCT_TO_CPCT) + (width / 2)) / width;
}

uint16_t soc_ocv_lut(uint16_t ocv_mv, int16_t temp_dc)
{
    soc_ocv_tw_t tw;
    int32_t soc;

    soc_ocv_temp_weights(soc_ocv_lut_span, (uint8_t)SOC_OCV_LUT_TEMPS, temp_dc, &tw);
    soc = lut_node(tw.a, ocv_mv);
    if (tw.num > 0)
    {
        soc = soc_ocv_blend(soc, lut_node(tw.b, ocv_mv), &tw);
    }
    return soc_ocv_to_permille(soc);
}
