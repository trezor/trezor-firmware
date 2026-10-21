/**
 * @file soc_ocv.h
 * @brief State of charge of a single alkaline AAA cell from its open-circuit
 * voltage (OCV) and temperature - C port of soc_ocv_lut.py and soc_ocv_poly.py,
 * tuned for 0-35 degC.
 *
 * Two interchangeable estimators; link only the one you call:
 *   soc_ocv_lut()   lookup table, 20 points per calibration temperature (104
 * bytes of data) soc_ocv_poly()  degree-4 polynomial per calibration
 * temperature    (64 bytes of data)
 *
 * Both are integer-only fixed point: no FPU instructions, no libm, no static
 * RAM, reentrant and safe to call from interrupts. Calibration data is const
 * and lives in flash.
 *
 * Temperature: each calibration curve applies fully over its temperature span
 * (the "25 degC" curve over 19-30 degC); between two spans the neighbouring
 * curves are blended linearly; colder or hotter than every span, the nearest
 * curve is used.
 *
 * OCV is the battery voltage at the end of a ~120 s rest (as in the calibration
 * logs).
 */
#ifndef SOC_OCV_H
#define SOC_OCV_H

#include <stdint.h>

/** Full scale of the result: 1000 = 100.0 % SoC. */
#define SOC_OCV_FULL (1000U)

/**
 * @brief SoC from OCV with the lookup tables.
 * @param ocv_mv  open-circuit voltage in mV (any value; clamped to each table's
 * range)
 * @param temp_dc temperature in 0.1 degC (any value)
 * @return SoC in 0.1 % units, 0..1000
 */
uint16_t soc_ocv_lut(uint16_t ocv_mv, int16_t temp_dc);

/**
 * @brief SoC from OCV with the polynomials (same inputs and result as
 * soc_ocv_lut()).
 */
uint16_t soc_ocv_poly(uint16_t ocv_mv, int16_t temp_dc);

#endif /* SOC_OCV_H */
