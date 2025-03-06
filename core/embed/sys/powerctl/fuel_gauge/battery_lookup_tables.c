/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * Battery SoC Lookup Tables Implementation
 * Auto-generated from Python battery characterization script
 */

#include "battery_lookup_tables.h"

// Helper function for linear interpolation
static float linear_interpolate(float x, float x1, float y1, float x2, float y2) {
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1);
}

float battery_get_internal_resistance(float temperature) {
    // Handle out-of-bounds temperatures
    if (temperature <= BATTERY_TEMP_POINTS[0]) {
        return BATTERY_R_INT[0];
    }
    if (temperature >= BATTERY_TEMP_POINTS[NUM_TEMPERATURE_POINTS - 1]) {
        return BATTERY_R_INT[NUM_TEMPERATURE_POINTS - 1];
    }

    // Find temperature bracket
    for (int i = 0; i < NUM_TEMPERATURE_POINTS - 1; i++) {
        if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
            return linear_interpolate(temperature,
                                      BATTERY_TEMP_POINTS[i], BATTERY_R_INT[i],
                                      BATTERY_TEMP_POINTS[i + 1], BATTERY_R_INT[i + 1]);
        }
    }

    // Should never reach here
    return BATTERY_R_INT[0];
}

float battery_get_capacity(float temperature) {
    // Handle out-of-bounds temperatures
    if (temperature <= BATTERY_TEMP_POINTS[0]) {
        return BATTERY_CAPACITY[0];
    }
    if (temperature >= BATTERY_TEMP_POINTS[NUM_TEMPERATURE_POINTS - 1]) {
        return BATTERY_CAPACITY[NUM_TEMPERATURE_POINTS - 1];
    }

    // Find temperature bracket
    for (int i = 0; i < NUM_TEMPERATURE_POINTS - 1; i++) {
        if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
            return linear_interpolate(temperature,
                                      BATTERY_TEMP_POINTS[i], BATTERY_CAPACITY[i],
                                      BATTERY_TEMP_POINTS[i + 1], BATTERY_CAPACITY[i + 1]);
        }
    }

    // Should never reach here
    return BATTERY_CAPACITY[0];
}

// Helper function to get VOC at a specific temperature
static float get_voc_at_temp(float soc, int temp_idx) {
    // Clip SoC to valid range
    if (soc <= BATTERY_SOC_POINTS[0]) {
        return BATTERY_VOC_ARRAYS[temp_idx][0];
    }
    if (soc >= BATTERY_SOC_POINTS[NUM_SOC_POINTS - 1]) {
        return BATTERY_VOC_ARRAYS[temp_idx][NUM_SOC_POINTS - 1];
    }

    // Find SoC bracket
    for (int i = 0; i < NUM_SOC_POINTS - 1; i++) {
        if (soc < BATTERY_SOC_POINTS[i + 1]) {
            return linear_interpolate(soc,
                                     BATTERY_SOC_POINTS[i], BATTERY_VOC_ARRAYS[temp_idx][i],
                                     BATTERY_SOC_POINTS[i + 1], BATTERY_VOC_ARRAYS[temp_idx][i + 1]);
        }
    }

    // Should never reach here
    return BATTERY_VOC_ARRAYS[temp_idx][0];
}

float battery_get_voc(float soc, float temperature) {
    // Handle out-of-bounds temperatures
    if (temperature <= BATTERY_TEMP_POINTS[0]) {
        return get_voc_at_temp(soc, 0);
    }
    if (temperature >= BATTERY_TEMP_POINTS[NUM_TEMPERATURE_POINTS - 1]) {
        return get_voc_at_temp(soc, NUM_TEMPERATURE_POINTS - 1);
    }

    // Find temperature bracket
    for (int i = 0; i < NUM_TEMPERATURE_POINTS - 1; i++) {
        if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
            float voc_low = get_voc_at_temp(soc, i);
            float voc_high = get_voc_at_temp(soc, i + 1);

            return linear_interpolate(temperature,
                                     BATTERY_TEMP_POINTS[i], voc_low,
                                     BATTERY_TEMP_POINTS[i + 1], voc_high);
        }
    }

    // Should never reach here
    return get_voc_at_temp(soc, 0);
}

// Helper function to get SoC at a specific temperature
static float get_soc_at_temp(float voc, int temp_idx) {
    // Clip VOC to valid range
    if (voc <= BATTERY_VOC_ARRAYS[temp_idx][0]) {
        return BATTERY_SOC_POINTS[0];
    }
    if (voc >= BATTERY_VOC_ARRAYS[temp_idx][NUM_SOC_POINTS - 1]) {
        return BATTERY_SOC_POINTS[NUM_SOC_POINTS - 1];
    }

    // Find VOC bracket
    for (int i = 0; i < NUM_SOC_POINTS - 1; i++) {
        if (voc < BATTERY_VOC_ARRAYS[temp_idx][i + 1]) {
            return linear_interpolate(voc,
                                     BATTERY_VOC_ARRAYS[temp_idx][i], BATTERY_SOC_POINTS[i],
                                     BATTERY_VOC_ARRAYS[temp_idx][i + 1], BATTERY_SOC_POINTS[i + 1]);
        }
    }

    // Should never reach here
    return BATTERY_SOC_POINTS[0];
}

float battery_get_soc(float voc, float temperature) {
    // Handle out-of-bounds temperatures
    if (temperature <= BATTERY_TEMP_POINTS[0]) {
        return get_soc_at_temp(voc, 0);
    }
    if (temperature >= BATTERY_TEMP_POINTS[NUM_TEMPERATURE_POINTS - 1]) {
        return get_soc_at_temp(voc, NUM_TEMPERATURE_POINTS - 1);
    }

    // Find temperature bracket
    for (int i = 0; i < NUM_TEMPERATURE_POINTS - 1; i++) {
        if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
            float soc_low = get_soc_at_temp(voc, i);
            float soc_high = get_soc_at_temp(voc, i + 1);

            return linear_interpolate(temperature,
                                     BATTERY_TEMP_POINTS[i], soc_low,
                                     BATTERY_TEMP_POINTS[i + 1], soc_high);
        }
    }

    // Should never reach here
    return get_soc_at_temp(voc, 0);
}