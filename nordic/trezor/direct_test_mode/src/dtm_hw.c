/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include "nrf.h"

#include "dtm_hw.h"
#include "dtm_hw_config.h"

/* All valid power levels (in dBm) supported by the SoC. */
const int8_t nrf_power_value[] = {
#if defined(RADIO_TXPOWER_TXPOWER_Neg100dBm)
	-100,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg100dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg70dBm)
	-70,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg70dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg46dBm)
	-46,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg46dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg40dBm)
	-40,
#endif /* RADIO_TXPOWER_TXPOWER_Neg40dBm */
#if defined(RADIO_TXPOWER_TXPOWER_Neg30dBm)
	-30,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg30dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg28dBm)
	-28,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg28dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg22dBm)
	-22,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg22dBm) */
	-20,
#if defined(RADIO_TXPOWER_TXPOWER_Neg18dBm)
	-18,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg18dBm) */
	-16,
#if defined(RADIO_TXPOWER_TXPOWER_Neg14dBm)
	-14,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg14dBm) */
	-12,
#if defined(RADIO_TXPOWER_TXPOWER_Neg10dBm)
	-10,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg10dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg9dBm)
	-9,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg9dBm) */
	-8,
#if defined(RADIO_TXPOWER_TXPOWER_Neg7dBm)
	-7,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg7dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg6dBm)
	-6,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg6dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg5dBm)
	-5,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg5dBm) */
	-4,
#if defined(RADIO_TXPOWER_TXPOWER_Neg3dBm)
	-3,
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg3dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg2dBm)
	-2,
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg2dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Neg1dBm)
	-1,
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg1dBm) */
	0,
#if defined(RADIO_TXPOWER_TXPOWER_Pos1dBm)
	1,
#endif /* RADIO_TXPOWER_TXPOWER_Pos1dBm */
#if defined(RADIO_TXPOWER_TXPOWER_Pos2dBm)
	2,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos2dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos3dBm)
	3,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos3dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos4dBm)
	4,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos4dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos5dBm)
	5,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos5dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos6dBm)
	6,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos6dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos7dBm)
	7,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos7dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos8dBm)
	8,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos8dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos9dBm)
	9,
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos9dBm) */
#if defined(RADIO_TXPOWER_TXPOWER_Pos10dBm)
	10
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos10dBm) */
};

#if DIRECTION_FINDING_SUPPORTED

#define DTM_MAX_ANTENNA_NUMBER 19

#define DFE_GPIO_PIN_DISCONNECT (RADIO_PSEL_DFEGPIO_CONNECT_Disconnected << \
				 RADIO_PSEL_DFEGPIO_CONNECT_Pos)

#define HAS_DFE_GPIO(idx) DT_NODE_HAS_PROP(RADIO_NODE, dfegpio##idx##_gpios)

/* Run a macro 'fn' on each available DFE GPIO index, from 0 to
 * MAX_DFE_GPIO-1, with the given parenthesized separator.
 */
#define FOR_EACH_DFE_GPIO(fn, sep) \
	FOR_EACH(fn, sep, 0, 1, 2, 3, 4, 5, 6, 7)

/* The number of dfegpio[n]-gpios properties which are set. */
#define DFE_GPIO_NUM (FOR_EACH_DFE_GPIO(HAS_DFE_GPIO, (+)))

#define PDU_ANTENNA DT_PROP(RADIO_NODE, dfe_pdu_antenna)

/* The minimum number of antennas required to enable antenna switching. */
#define MIN_ANTENNA_NUM 1

/* The maximum number of antennas supported by the number of
 * dfegpio[n]-gpios properties which are set.
 */
#if (DFE_GPIO_NUM > 0)
#define MAX_ANTENNA_NUM BIT(DFE_GPIO_NUM)
#else
#define MAX_ANTENNA_NUM 0
#endif

/*
 * Check that the number of antennas has been set, and that enough
 * pins are configured to represent each pattern for the given number
 * of antennas.
 */
#define HAS_ANTENNA_NUM DT_NODE_HAS_PROP(RADIO_NODE, dfe_antenna_num)

BUILD_ASSERT(HAS_ANTENNA_NUM,
	     "You must set the dfe-antenna-num property in the radio node "
	     "to enable antenna switching.");

#define ANTENNA_NUM DT_PROP_OR(RADIO_NODE, dfe_antenna_num, 0)


BUILD_ASSERT(!HAS_ANTENNA_NUM || (ANTENNA_NUM <= MAX_ANTENNA_NUM),
	     "Insufficient number of GPIO pins configured. "
	     "Set more dfegpio[n]-gpios properties.");
BUILD_ASSERT(!HAS_ANTENNA_NUM || (ANTENNA_NUM >= MIN_ANTENNA_NUM),
	     "Insufficient number of antennas provided. "
	     "Increase the dfe-antenna-num property.");

#define HAS_PDU_ANTENNA DT_NODE_HAS_PROP(RADIO_NODE, dfe_pdu_antenna)

BUILD_ASSERT(HAS_PDU_ANTENNA,
	     "Missing antenna pattern used to select antenna for PDU Tx "
	     "during the CTE Idle state. "
	     "Set the dfe-pdu-antenna devicetree property.");

/*
 * Check that each dfegpio[n]-gpios property has a zero flags cell.
 */
#define ASSERT_DFE_GPIO_FLAGS_ARE_ZERO(idx)				   \
	BUILD_ASSERT(DT_GPIO_FLAGS(RADIO_NODE, dfegpio##idx##_gpios) == 0, \
		     "The flags cell in each dfegpio[n]-gpios "		   \
		     "property must be zero.")

FOR_EACH_DFE_GPIO(ASSERT_DFE_GPIO_FLAGS_ARE_ZERO, (;));

#define DFE_GPIO_PSEL(idx)					  \
	NRF_DT_GPIOS_TO_PSEL_OR(RADIO_NODE, dfegpio##idx##_gpios, \
				DTM_HW_DFE_PSEL_NOT_SET)

static const struct dtm_ant_cfg {
	uint8_t ant_num;
	/* Selection of GPIOs to be used to switch antennas by Radio */
	uint8_t dfe_gpio[DTM_HW_MAX_DFE_GPIO];
} ant_cfg = {
	.ant_num = (ANTENNA_NUM > DTM_MAX_ANTENNA_NUMBER) ? DTM_MAX_ANTENNA_NUMBER : ANTENNA_NUM,
	.dfe_gpio = { FOR_EACH_DFE_GPIO(DFE_GPIO_PSEL, (,)) }
};
#endif /* DIRECTION_FINDING_SUPPORTED */

bool dtm_hw_radio_validate(int8_t tx_power,
			   nrf_radio_mode_t radio_mode)
{
	/* Initializing code below is quite generic - for BLE, the values are
	 * fixed, and expressions are constant. Non-constant values are
	 * essentially set in radio_prepare().
	 */

	if (!(
#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
		radio_mode == NRF_RADIO_MODE_BLE_LR125KBIT  ||
		radio_mode == NRF_RADIO_MODE_BLE_LR500KBIT  ||
#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */
		radio_mode == NRF_RADIO_MODE_BLE_1MBIT      ||
		radio_mode == NRF_RADIO_MODE_BLE_2MBIT
		)
	) {
		return false;
	}

	for (size_t i = 0; i < ARRAY_SIZE(nrf_power_value); i++) {
		if (tx_power == nrf_power_value[i]) {
			return true;
		}
	}

	return false;
}

bool dtm_hw_radio_lr_check(nrf_radio_mode_t radio_mode)
{
#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	if (radio_mode == NRF_RADIO_MODE_BLE_LR125KBIT) {
		return true;
	}

	if (radio_mode == NRF_RADIO_MODE_BLE_LR500KBIT) {
		return true;
	}
#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */

	return false;
}

uint32_t dtm_hw_radio_min_power_get(void)
{
	return nrf_power_value[0];
}

uint32_t dtm_hw_radio_max_power_get(void)
{
	return nrf_power_value[ARRAY_SIZE(nrf_power_value) - 1];
}

size_t dtm_hw_radio_power_array_size_get(void)
{
	return ARRAY_SIZE(nrf_power_value);
}

const int8_t *dtm_hw_radio_power_array_get(void)
{
	return nrf_power_value;
}

#if DIRECTION_FINDING_SUPPORTED
size_t dtm_hw_radio_antenna_number_get(void)
{
	return ant_cfg.ant_num;
}

const uint8_t *dtm_hw_radio_antenna_pin_array_get(void)
{
	return ant_cfg.dfe_gpio;
}

uint8_t dtm_hw_radio_pdu_antenna_get(void)
{
	return PDU_ANTENNA;
}
#endif /* DIRECTION_FINDING_SUPPORTED */
