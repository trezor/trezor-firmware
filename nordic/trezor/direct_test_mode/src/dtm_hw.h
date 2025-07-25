/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef DTM_HW_H_
#define DTM_HW_H_

#include <stdbool.h>
#include <zephyr/types.h>

#include <hal/nrf_radio.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Number of PSEL_DFEGPIO[n] registers in the radio peripheral. */
#define DTM_HW_MAX_DFE_GPIO 8

/* Indicates that GPIO pin is not connected to the radio */
#define DTM_HW_DFE_PSEL_NOT_SET 0xFF

/* Disconnect pin from the RADIO DFGPIO register. */
#define DTM_HW_DFE_GPIO_PIN_DISCONNECT (RADIO_PSEL_DFEGPIO_CONNECT_Disconnected << \
					RADIO_PSEL_DFEGPIO_CONNECT_Pos)

/**@brief Function for validating tx power and radio mode settings.
 * @param[in] tx_power    TX power for transmission test in dBm.
 * @param[in] radio_mode  Radio mode value.
 *
 * @retval true  If validation was successful
 * @retval false Otherwise
 */
bool dtm_hw_radio_validate(int8_t tx_power,
			   nrf_radio_mode_t radio_mode);

/**@brief Function for checking if Radio operates in Long Range mode.
 * @param[in] radio_mode  Radio mode value.
 *
 * @retval true  If Long Range Radio mode is set
 * @retval false Otherwise
 */
bool dtm_hw_radio_lr_check(nrf_radio_mode_t radio_mode);

/**@brief Function for getting minimum tx power.
 *
 * @retval Minimum tx power value.
 */
uint32_t dtm_hw_radio_min_power_get(void);

/**@brief Function for getting maximum tx power.
 *
 * @retval Maximum tx power value.
 */
uint32_t dtm_hw_radio_max_power_get(void);

/**@brief Function for getting power array size. This array contains all
 *        possible tx power values for given divice sorted in ascending
 *        order.
 *
 * @reval Size of the tx power array.
 */
size_t dtm_hw_radio_power_array_size_get(void);

/**@brief Function for getting tx power array. This array contains all
 *        possible tx power values for given divice sorted in ascending
 *        order.
 *
 * @retval Size of the tx power array.
 */
const int8_t *dtm_hw_radio_power_array_get(void);

/**@brief Function for getting antenna pins array. This array contains
 *        all antenna pins data.
 *
 * @retval Pointer to the first element in antenna pins array.
 */
const uint8_t *dtm_hw_radio_antenna_pin_array_get(void);

/**@brief Function for getting available antenna number.
 *
 * @retval Maximum antenna number that DTM can use.
 */
size_t dtm_hw_radio_antenna_number_get(void);

/**@brief Function for getting the PDU antenna.
 *
 * @retval The PDU antenna.
 */
uint8_t dtm_hw_radio_pdu_antenna_get(void);

#ifdef __cplusplus
}
#endif

#endif /* DTM_HW_H_ */
