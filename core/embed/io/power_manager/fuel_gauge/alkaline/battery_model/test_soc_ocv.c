/**
 * @file test_soc_ocv.c
 * @brief Host tests of soc_ocv_lut() / soc_ocv_poly() against the Python (float) reference.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "soc_ocv.h"
#include "soc_ocv_data.h"
#include "test_vectors.h"

#define TOL_LUT_PCT  (0.31)   /* uint8 table rounding <= 0.25 % + result rounding 0.05 % */
#define TOL_POLY_PCT (0.12)   /* coefficient rounding + Q15 + result rounding */

static int g_fail = 0;

#define CHECK(cond, ...)                         \
    do                                           \
    {                                            \
        if (!(cond))                             \
        {                                        \
            g_fail++;                            \
            printf("  FAIL line %d: ", __LINE__); \
            printf(__VA_ARGS__);                 \
            printf("\n");                        \
        }                                        \
    } while (0)

typedef uint16_t (*estimator_t)(uint16_t, int16_t);

static void test_against_python(const char *name, estimator_t f, int which, double tol)
{
    double max_grid = 0.0, max_pts = 0.0, sum_c = 0.0, sum_py = 0.0;
    unsigned i;
    for (i = 0U; i < TV_NGRID; i++)
    {
        const double py = (which == 0) ? tv_grid[i].lut : tv_grid[i].poly;
        max_grid = fmax(max_grid, fabs(f(tv_grid[i].mv, tv_grid[i].dc) / 10.0 - py));
    }
    for (i = 0U; i < TV_NPOINTS; i++)
    {
        const double py = (which == 0) ? tv_points[i].lut : tv_points[i].poly;
        const double c = f(tv_points[i].mv, tv_points[i].dc) / 10.0;
        max_pts = fmax(max_pts, fabs(c - py));
        sum_c += fabs(c - tv_points[i].truth);
        sum_py += fabs(py - tv_points[i].truth);
    }
    printf("%-6s vs Python: max |diff| grid %.3f %%, lab points %.3f %% | SoC MAE vs truth on %u lab points: "
           "C %.3f %%, Python %.3f %%\n", name, max_grid, max_pts, TV_NPOINTS, sum_c / TV_NPOINTS, sum_py / TV_NPOINTS);
    CHECK(max_grid <= tol && max_pts <= tol, "%s differs from Python by more than %.2f %%", name, tol);
    CHECK(fabs(sum_c - sum_py) / TV_NPOINTS < 0.05, "%s MAE changed by the integer port", name);
}

static void test_properties(const char *name, estimator_t f)
{
    int t, mv, worst_step = 0, worst_t = 0, worst_mv = 0;
    unsigned long n = 0UL;
    /* SoC never decreases when OCV rises, at any temperature */
    for (t = -300; t <= 700; t += 5)
    {
        uint16_t prev = f(800U, (int16_t)t);
        for (mv = 801; mv <= 1800; mv++)
        {
            const uint16_t s = f((uint16_t)mv, (int16_t)t);
            CHECK(s >= prev, "%s not monotone at %d mV, %.1f degC", name, mv, t / 10.0);
            prev = s;
            n++;
        }
    }
    /* no jumps when the temperature changes by 0.1 degC */
    for (mv = 1050; mv <= 1700; mv += 5)
    {
        uint16_t prev = f((uint16_t)mv, -300);
        for (t = -299; t <= 700; t++)
        {
            const uint16_t s = f((uint16_t)mv, (int16_t)t);
            const int d = abs((int)s - (int)prev);
            if (d > worst_step)
            {
                worst_step = d;
                worst_t = t;
                worst_mv = mv;
            }
            prev = s;
        }
    }
    /* any input stays in range */
    {
        const uint16_t ext[4] = {f(0U, -32768), f(0U, 32767), f(65535U, -32768), f(65535U, 32767)};
        int k;
        for (k = 0; k < 4; k++)
        {
            CHECK(ext[k] <= SOC_OCV_FULL, "%s out of range for extreme input %d: %u", name, k, ext[k]);
        }
        printf("%-6s monotone in OCV over %lu evaluations; largest step per 0.1 degC %.1f %% (at %d mV, %.1f degC); "
               "extremes %u %u %u %u (0.1 %%)\n", name, n, worst_step / 10.0, worst_mv, worst_t / 10.0, ext[0], ext[1],
               ext[2], ext[3]);
    }
    CHECK(worst_step <= 10, "%s jumps by %.1f %% for a 0.1 degC step", name, worst_step / 10.0);
}

int main(void)
{
    printf("data in flash: lookup table %u bytes (spans %u + ranges %u + SoC %u), polynomial %u bytes "
           "(spans %u + ranges %u + coefficients %u)\n",
           (unsigned)(sizeof soc_ocv_lut_span + sizeof soc_ocv_lut_vrange + sizeof soc_ocv_lut_soc),
           (unsigned)sizeof soc_ocv_lut_span, (unsigned)sizeof soc_ocv_lut_vrange, (unsigned)sizeof soc_ocv_lut_soc,
           (unsigned)(sizeof soc_ocv_poly_span + sizeof soc_ocv_poly_vrange + sizeof soc_ocv_poly_coef),
           (unsigned)sizeof soc_ocv_poly_span, (unsigned)sizeof soc_ocv_poly_vrange, (unsigned)sizeof soc_ocv_poly_coef);
    test_against_python("lut", soc_ocv_lut, 0, TOL_LUT_PCT);
    test_against_python("poly", soc_ocv_poly, 1, TOL_POLY_PCT);
    test_properties("lut", soc_ocv_lut);
    test_properties("poly", soc_ocv_poly);
    printf("%s (%d failures)\n", g_fail == 0 ? "ALL TESTS PASS" : "TESTS FAIL", g_fail);
    return g_fail == 0 ? 0 : 1;
}
