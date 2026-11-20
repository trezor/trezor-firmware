/* Minimal STM32H5 image calling both estimators, for the footprint report only. */
#include "soc_ocv.h"

volatile uint16_t g_mv = 1300U;
volatile int16_t g_dc = 250;
volatile uint16_t g_out;

int main(void)
{
    g_out = (uint16_t)(soc_ocv_lut(g_mv, g_dc) + soc_ocv_poly(g_mv, g_dc));
    return 0;
}
