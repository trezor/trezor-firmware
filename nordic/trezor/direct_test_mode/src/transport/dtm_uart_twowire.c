/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <errno.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
#include <zephyr/kernel.h>
#include <dtm.h>

#include "dtm_uart_wait.h"
#include "dtm_transport.h"

LOG_MODULE_REGISTER(dtm_tw_tr, CONFIG_DTM_TRANSPORT_LOG_LEVEL);

/* Mask of the CTE type in the CTEInfo. */
#define LE_CTE_TYPE_MASK 0x03

/* Position of the CTE type in the CTEInfo. */
#define LE_CTE_TYPE_POS 0x06

/* Mask of the CTE Time in the CTEInfo. */
#define LE_CTE_CTETIME_MASK 0x1F

/* DTM command parameter: Mask of the Antenna Number. */
#define LE_ANTENNA_NUMBER_MASK 0x7F

/* DTM command parameter: Position of the Antenna switch pattern. */
#define LE_ANTENNA_SWITCH_PATTERN_POS 0x07

/* DTM command parameter: Mask of the Antenna switch pattern. */
#define LE_ANTENNA_SWITCH_PATTERN_MASK 0x80

/* Position of power level in the DTM power level set response. */
#define LE_TRANSMIT_POWER_RESPONSE_LVL_POS (0x01)

/* Mask of the power level in the DTM power level set respose. */
#define LE_TRANSMIT_POWER_RESPONSE_LVL_MASK (0x1FE)

/* Maximum power level bit in the power level set response. */
#define LE_TRANSMIT_POWER_MAX_LVL_BIT BIT(0x0A)

/* Minimum power level bit in the power level set response. */
#define LE_TRANSMIT_POWER_MIN_LVL_BIT BIT(0x09)

/* Response event data shift. */
#define DTM_RESPONSE_EVENT_SHIFT 0x01

/* DTM command parameter: Upper bits mask. */
#define LE_UPPER_BITS_MASK 0xC0

/* DTM command parameter: Upper bits position. */
#define LE_UPPER_BITS_POS 0x04

/* Event status response bits for Read Supported variant of LE Test Setup
 * command.
 */
#define LE_TEST_SETUP_DLE_SUPPORTED         BIT(1)
#define LE_TEST_SETUP_2M_PHY_SUPPORTED      BIT(2)
#define LE_TEST_STABLE_MODULATION_SUPPORTED BIT(3)
#define LE_TEST_CODED_PHY_SUPPORTED         BIT(4)
#define LE_TEST_CTE_SUPPORTED               BIT(5)
#define DTM_LE_ANTENNA_SWITCH               BIT(6)
#define DTM_LE_AOD_1US_TANSMISSION          BIT(7)
#define DTM_LE_AOD_1US_RECEPTION            BIT(8)
#define DTM_LE_AOA_1US_RECEPTION            BIT(9)

/* The DTM maximum wait time in milliseconds for the UART command second byte. */
#define DTM_UART_SECOND_BYTE_MAX_DELAY 5

static const struct device *dtm_uart = DEVICE_DT_GET(DTM_UART);

/* DTM command codes */
enum dtm_cmd_code {
	/* Test Setup Command: Set PHY or modulation, configure upper two bits
	 * of length, request matrix of supported features or request max
	 * values of parameters.
	 */
	LE_TEST_SETUP = 0x0,

	/* Receive Command: Start receive test. */
	LE_RECEIVER_TEST = 0x1,

	/* Transmit Command: Start transmission test. */
	LE_TRANSMITTER_TEST = 0x2,

	/* Test End Command: End test and send packet report. */
	LE_TEST_END  = 0x3,
};

/* DTM Test Setup Control codes */
enum dtm_ctrl_code {
	/* Reset the packet length upper bits and set the PHY to 1Mbit. */
	LE_TEST_SETUP_RESET = 0x00,

	/* Set the upper two bits of the length field. */
	LE_TEST_SETUP_SET_UPPER = 0x01,

	/* Select the PHY to be used for packets. */
	LE_TEST_SETUP_SET_PHY = 0x02,

	/* Select standard or stable modulation index. Stable modulation index
	 * is not supported.
	 */
	LE_TEST_SETUP_SELECT_MODULATION = 0x03,

	/* Read the supported test case features. */
	LE_TEST_SETUP_READ_SUPPORTED = 0x04,

	/* Read the max supported time and length for packets. */
	LE_TEST_SETUP_READ_MAX = 0x05,

	/* Set the Constant Tone Extension info. */
	LE_TEST_SETUP_CONSTANT_TONE_EXTENSION = 0x06,

	/* Set the Constant Tone Extension slot. */
	LE_TEST_SETUP_CONSTANT_TONE_EXTENSION_SLOT = 0x07,

	/* Set the Antenna number and switch pattern. */
	LE_TEST_SETUP_ANTENNA_ARRAY = 0x08,

	/* Set the Transmit power. */
	LE_TEST_SETUP_TRANSMIT_POWER = 0x09
};

/* DTM Test Setup PHY codes */
enum dtm_phy_code {
	/* Set PHY for future packets to use 1MBit PHY.
	 * Minimum parameter value.
	 */
	LE_PHY_1M_MIN_RANGE = 0x04,

	/* Set PHY for future packets to use 1MBit PHY.
	 * Maximum parameter value.
	 */
	LE_PHY_1M_MAX_RANGE = 0x07,

	/* Set PHY for future packets to use 2MBit PHY.
	 * Minimum parameter value.
	 */
	LE_PHY_2M_MIN_RANGE = 0x08,

	/* Set PHY for future packets to use 2MBit PHY.
	 * Maximum parameter value.
	 */
	LE_PHY_2M_MAX_RANGE = 0x0B,

	/* Set PHY for future packets to use coded PHY with S=8.
	 * Minimum parameter value.
	 */
	LE_PHY_LE_CODED_S8_MIN_RANGE = 0x0C,

	/* Set PHY for future packets to use coded PHY with S=8.
	 * Maximum parameter value.
	 */
	LE_PHY_LE_CODED_S8_MAX_RANGE = 0x0F,

	/* Set PHY for future packets to use coded PHY with S=2.
	 * Minimum parameter value.
	 */
	LE_PHY_LE_CODED_S2_MIN_RANGE = 0x10,

	/* Set PHY for future packets to use coded PHY with S=2.
	 * Maximum parameter value.
	 */
	LE_PHY_LE_CODED_S2_MAX_RANGE = 0x13
};

/* DTM Test Setup Read supported parameters codes. */
enum dtm_read_supported_code {
	/* Read maximum supported Tx Octets. Minimum parameter value. */
	LE_TEST_SUPPORTED_TX_OCTETS_MIN_RANGE = 0x00,

	/* Read maximum supported Tx Octets. Maximum parameter value. */
	LE_TEST_SUPPORTED_TX_OCTETS_MAX_RANGE = 0x03,

	/* Read maximum supported Tx Time. Minimum parameter value. */
	LE_TEST_SUPPORTED_TX_TIME_MIN_RANGE = 0x04,

	/* Read maximum supported Tx Time. Maximum parameter value. */
	LE_TEST_SUPPORTED_TX_TIME_MAX_RANGE = 0x07,

	/* Read maximum supported Rx Octets. Minimum parameter value. */
	LE_TEST_SUPPORTED_RX_OCTETS_MIN_RANGE = 0x08,

	/* Read maximum supported Rx Octets. Maximum parameter value. */
	LE_TEST_SUPPORTED_RX_OCTETS_MAX_RANGE = 0x0B,

	/* Read maximum supported Rx Time. Minimum parameter value. */
	LE_TEST_SUPPORTED_RX_TIME_MIN_RANGE = 0x0C,

	/* Read maximum supported Rx Time. Maximum parameter value. */
	LE_TEST_SUPPORTED_RX_TIME_MAX_RANGE = 0x0F,

	/* Read maximum length of the Constant Tone Extension supported. */
	LE_TEST_SUPPORTED_CTE_LENGTH = 0x10
};

/* DTM Test Setup reset code. */
enum dtm_reset_code {
	/* Reset. Minimum parameter value. */
	LE_RESET_MIN_RANGE = 0x00,

	/* Reset. Maximum parameter value. */
	LE_RESET_MAX_RANGE = 0x03
};

/* DTM Test Setup upper bits code. */
enum dtm_set_upper_bits_code {
	/* Set upper bits. Minimum parameter value. */
	LE_SET_UPPER_BITS_MIN_RANGE = 0x00,

	/* Set upper bits. Maximum parameter value. */
	LE_SET_UPPER_BITS_MAX_RANGE = 0x0F
};

/* DTM Test Setup modulation code. */
enum dtm_modulation_code {
	/* Set Modulation index to standard. Minimum parameter value. */
	LE_MODULATION_INDEX_STANDARD_MIN_RANGE = 0x00,

	/* Set Modulation index to standard. Maximum parameter value. */
	LE_MODULATION_INDEX_STANDARD_MAX_RANGE = 0x03,

	/* Set Modulation index to stable. Minimum parameter value. */
	LE_MODULATION_INDEX_STABLE_MIN_RANGE = 0x04,

	/* Set Modulation index to stable. Maximum parameter value. */
	LE_MODULATION_INDEX_STABLE_MAX_RANGE = 0x07
};

/* DTM Test Setup feature read code. */
enum dtm_feature_read_code {
	/* Read test case supported feature. Minimum parameter value. */
	LE_TEST_FEATURE_READ_MIN_RANGE = 0x00,

	/* Read test case supported feature. Maximum parameter value. */
	LE_TEST_FEATURE_READ_MAX_RANGE = 0x03
};

/* DTM Test Setup transmit power code. */
enum dtm_transmit_power_code {
	/* Minimum supported transmit power level. */
	LE_TRANSMIT_POWER_LVL_MIN = -127,

	/* Maximum supported transmit power level. */
	LE_TRANSMIT_POWER_LVL_MAX = 20,

	/* Set minimum transmit power level. */
	LE_TRANSMIT_POWER_LVL_SET_MIN = 0x7E,

	/* Set maximum transmit power level. */
	LE_TRANSMIT_POWER_LVL_SET_MAX = 0x7F
};

/* DTM Test Setup antenna number max values. */
enum dtm_antenna_number {
	/* Minimum antenna number. */
	LE_TEST_ANTENNA_NUMBER_MIN = 0x01,

	/* Maximum antenna number. */
	LE_TEST_ANTENNA_NUMBER_MAX = 0x4B
};

enum dtm_antenna_pattern {
	/* Constant Tone Extension: Antenna switch pattern 1, 2, 3 ...N. */
	DTM_ANTENNA_PATTERN_123N123N = 0x00,

	/* Constant Tone Extension: Antenna switch pattern
	 * 1, 2, 3 ...N, N - 1, N - 2, ..., 1, ...
	 */
	DTM_ANTENNA_PATTERN_123N2123 = 0x01
};

/* DTM Test Setup CTE type code */
enum dtm_cte_type_code {
	/* CTE Type Angle of Arrival. */
	LE_CTE_TYPE_AOA = 0x00,

	/* CTE Type Angle of Departure with 1 us slot. */
	LE_CTE_TYPE_AOD_1US = 0x01,

	/* CTE Type Angle of Departure with 2 us slot.*/
	LE_CTE_TYPE_AOD_2US = 0x02
};

enum dtm_cte_slot_code {
	/* CTE 1 us slot duration. */
	LE_CTE_SLOT_1US = 0x01,

	/* CTE 2 us slot duration. */
	LE_CTE_SLOT_2US = 0x02
};

/* DTM Packet Type field */
enum dtm_pkt_type {
	/* PRBS9 bit pattern */
	DTM_PKT_PRBS9 = 0x00,

	/* 11110000 bit pattern (LSB is the leftmost bit). */
	DTM_PKT_0X0F = 0x01,

	/* 10101010 bit pattern (LSB is the leftmost bit). */
	DTM_PKT_0X55 = 0x02,

	/* 11111111 bit pattern for Coded PHY.
	 * Vendor specific command for Non-Coded PHY.
	 */
	DTM_PKT_0XFF_OR_VS = 0x03,
};

/* DTM Test End control code. */
enum dtm_test_end_code {
	/* Test End. Minimum parameter value. */
	LE_TEST_END_MIN_RANGE = 0x00,

	/* Test End. Maximum parameter value. */
	LE_TEST_END_MAX_RANGE = 0x03
};

/* DTM events */
enum dtm_evt {
	/* Status event, indicating success. */
	LE_TEST_STATUS_EVENT_SUCCESS = 0x0000,

	/* Status event, indicating an error. */
	LE_TEST_STATUS_EVENT_ERROR = 0x0001,

	/* Packet reporting event, returned by the device to the tester. */
	LE_PACKET_REPORTING_EVENT = 0x8000,
};

/** Upper bits of packet length */
static uint8_t upper_len;

static int reset_dtm(uint8_t parameter)
{
	if (parameter > LE_RESET_MAX_RANGE) {
		return -EINVAL;
	}

	upper_len = 0;
	return dtm_setup_reset();
}

static int upper_set(uint8_t parameter)
{
	if (parameter > LE_SET_UPPER_BITS_MAX_RANGE) {
		return -EINVAL;
	}

	upper_len = (parameter << LE_UPPER_BITS_POS) & LE_UPPER_BITS_MASK;
	return 0;
}

static int phy_set(uint8_t parameter)
{
	switch (parameter) {
	case LE_PHY_1M_MIN_RANGE ... LE_PHY_1M_MAX_RANGE:
		return dtm_setup_set_phy(DTM_PHY_1M);

	case LE_PHY_2M_MIN_RANGE ... LE_PHY_2M_MAX_RANGE:
		return dtm_setup_set_phy(DTM_PHY_2M);

	case LE_PHY_LE_CODED_S8_MIN_RANGE ... LE_PHY_LE_CODED_S8_MAX_RANGE:
		return dtm_setup_set_phy(DTM_PHY_CODED_S8);

	case LE_PHY_LE_CODED_S2_MIN_RANGE ... LE_PHY_LE_CODED_S2_MAX_RANGE:
		return dtm_setup_set_phy(DTM_PHY_CODED_S2);

	default:
		return -EINVAL;
	}
}

static int mod_set(uint8_t parameter)
{
	switch (parameter) {
	case LE_MODULATION_INDEX_STANDARD_MIN_RANGE ... LE_MODULATION_INDEX_STANDARD_MAX_RANGE:
		return dtm_setup_set_modulation(DTM_MODULATION_STANDARD);

	case LE_MODULATION_INDEX_STABLE_MIN_RANGE ... LE_MODULATION_INDEX_STABLE_MAX_RANGE:
		return dtm_setup_set_modulation(DTM_MODULATION_STABLE);

	default:
		return -EINVAL;
	}
}

static int features_read(uint8_t parameter, uint16_t *ret)
{
	struct dtm_supp_features features;

	if (parameter > LE_TEST_FEATURE_READ_MAX_RANGE) {
		return -EINVAL;
	}

	features = dtm_setup_read_features();

	*ret = 0;
	*ret |= (features.data_len_ext ? LE_TEST_SETUP_DLE_SUPPORTED : 0);
	*ret |= (features.phy_2m ? LE_TEST_SETUP_2M_PHY_SUPPORTED : 0);
	*ret |= (features.stable_mod ? LE_TEST_STABLE_MODULATION_SUPPORTED : 0);
	*ret |= (features.coded_phy ? LE_TEST_CODED_PHY_SUPPORTED : 0);
	*ret |= (features.cte ? LE_TEST_CTE_SUPPORTED : 0);
	*ret |= (features.ant_switching ? DTM_LE_ANTENNA_SWITCH : 0);
	*ret |= (features.aod_1us_tx ? DTM_LE_AOD_1US_TANSMISSION : 0);
	*ret |= (features.aod_1us_rx ? DTM_LE_AOD_1US_RECEPTION : 0);
	*ret |= (features.aoa_1us_rx ? DTM_LE_AOA_1US_RECEPTION : 0);

	return 0;
}

static int read_max(uint8_t parameter, uint16_t *ret)
{
	int err;

	switch (parameter) {
	case LE_TEST_SUPPORTED_TX_OCTETS_MIN_RANGE ... LE_TEST_SUPPORTED_TX_OCTETS_MAX_RANGE:
		err = dtm_setup_read_max_supported_value(DTM_MAX_SUPPORTED_TX_OCTETS, ret);
		break;

	case LE_TEST_SUPPORTED_TX_TIME_MIN_RANGE ... LE_TEST_SUPPORTED_TX_TIME_MAX_RANGE:
		err = dtm_setup_read_max_supported_value(DTM_MAX_SUPPORTED_TX_TIME, ret);
		break;

	case LE_TEST_SUPPORTED_RX_OCTETS_MIN_RANGE ... LE_TEST_SUPPORTED_RX_OCTETS_MAX_RANGE:
		err = dtm_setup_read_max_supported_value(DTM_MAX_SUPPORTED_RX_OCTETS, ret);
		break;

	case LE_TEST_SUPPORTED_RX_TIME_MIN_RANGE ... LE_TEST_SUPPORTED_RX_TIME_MAX_RANGE:
		err = dtm_setup_read_max_supported_value(DTM_MAX_SUPPORTED_RX_TIME, ret);
		break;

	case LE_TEST_SUPPORTED_CTE_LENGTH:
		err = dtm_setup_read_max_supported_value(DTM_MAX_SUPPORTED_CTE_LENGTH, ret);
		break;

	default:
		return -EINVAL;
	}

	*ret = *ret << DTM_RESPONSE_EVENT_SHIFT;
	return err;
}

static int cte_set(uint8_t parameter)
{
	enum dtm_cte_type_code type = (parameter & LE_CTE_TYPE_MASK) >> LE_CTE_TYPE_POS;
	uint8_t time = parameter & LE_CTE_CTETIME_MASK;

	if (!parameter) {
		return dtm_setup_set_cte_mode(DTM_CTE_TYPE_NONE, 0);
	}

	switch (type) {
	case LE_CTE_TYPE_AOA:
		return dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOA, time);

	case LE_CTE_TYPE_AOD_1US:
		return dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOD_1US, time);

	case LE_CTE_TYPE_AOD_2US:
		return dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOD_2US, time);

	default:
		return -EINVAL;
	}
}

static int cte_slot_set(uint8_t parameter)
{
	enum dtm_cte_type_code type = (parameter & LE_CTE_TYPE_MASK) >> LE_CTE_TYPE_POS;

	switch (type) {
	case LE_CTE_SLOT_1US:
		return dtm_setup_set_cte_slot(DTM_CTE_SLOT_DURATION_1US);

	case LE_CTE_SLOT_2US:
		return dtm_setup_set_cte_slot(DTM_CTE_SLOT_DURATION_2US);

	default:
		return -EINVAL;
	}
}

static int antenna_set(uint8_t parameter)
{
	static uint8_t pattern[LE_TEST_ANTENNA_NUMBER_MAX * 2];
	enum dtm_antenna_pattern type =
		(parameter & LE_ANTENNA_SWITCH_PATTERN_MASK) >> LE_ANTENNA_SWITCH_PATTERN_POS;
	uint8_t ant_count = (parameter & LE_ANTENNA_NUMBER_MASK);
	uint8_t length;
	size_t i;

	if ((ant_count < LE_TEST_ANTENNA_NUMBER_MIN) || (ant_count > LE_TEST_ANTENNA_NUMBER_MAX)) {
		return -EINVAL;
	}

	length = ant_count;

	switch (type) {
	case DTM_ANTENNA_PATTERN_123N123N:
		for (i = 1; i <= length; i++) {
			pattern[i - 1] = i;
		}
		break;

	case DTM_ANTENNA_PATTERN_123N2123:
		for (i = 1; i <= length; i++) {
			pattern[i - 1] = i;
		}
		for (i = 1; i < length; i++) {
			pattern[i + length - 1] = length - i;
		}

		length = (length * 2) - 1;
		break;

	default:
		return -EINVAL;
	}

	return dtm_setup_set_antenna_params(ant_count, pattern, length);
}

static int tx_power_set(int8_t parameter, uint16_t *ret)
{
	struct dtm_tx_power power;

	switch (parameter) {
	case LE_TRANSMIT_POWER_LVL_SET_MIN:
		power = dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_MIN, 0, 0);
		break;

	case LE_TRANSMIT_POWER_LVL_SET_MAX:
		power = dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_MAX, 0, 0);
		break;

	case LE_TRANSMIT_POWER_LVL_MIN ... LE_TRANSMIT_POWER_LVL_MAX:
		power = dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_VAL, parameter, 0);
		break;

	default:
		return -EINVAL;
	}

	*ret = (power.power << LE_TRANSMIT_POWER_RESPONSE_LVL_POS) &
								LE_TRANSMIT_POWER_RESPONSE_LVL_MASK;
	if (power.max) {
		*ret |= LE_TRANSMIT_POWER_MAX_LVL_BIT;
	}
	if (power.min) {
		*ret |= LE_TRANSMIT_POWER_MIN_LVL_BIT;
	}

	return 0;
}

static uint16_t on_test_setup_cmd(enum dtm_ctrl_code control, uint8_t parameter)
{
	uint16_t ret = 0;
	int err;

	dtm_setup_prepare();

	switch (control) {
	case LE_TEST_SETUP_RESET:
		err = reset_dtm(parameter);
		break;

	case LE_TEST_SETUP_SET_UPPER:
		err = upper_set(parameter);
		break;

	case LE_TEST_SETUP_SET_PHY:
		err = phy_set(parameter);
		break;

	case LE_TEST_SETUP_SELECT_MODULATION:
		err = mod_set(parameter);
		break;

	case LE_TEST_SETUP_READ_SUPPORTED:
		err = features_read(parameter, &ret);
		break;

	case LE_TEST_SETUP_READ_MAX:
		err = read_max(parameter, &ret);
		break;

	case LE_TEST_SETUP_CONSTANT_TONE_EXTENSION:
		err = cte_set(parameter);
		break;

	case LE_TEST_SETUP_CONSTANT_TONE_EXTENSION_SLOT:
		err = cte_slot_set(parameter);
		break;

	case LE_TEST_SETUP_ANTENNA_ARRAY:
		err = antenna_set(parameter);
		break;

	case LE_TEST_SETUP_TRANSMIT_POWER:
		err = tx_power_set(parameter, &ret);
		break;

	default:
		err = -EINVAL;
		break;
	}

	return (err ? LE_TEST_STATUS_EVENT_ERROR : (LE_TEST_STATUS_EVENT_SUCCESS | ret));
}

static uint16_t on_test_end_cmd(enum dtm_ctrl_code control, uint8_t parameter)
{
	uint16_t cnt;
	int err;

	if (control) {
		return LE_TEST_STATUS_EVENT_ERROR;
	}

	if (parameter > LE_TEST_END_MAX_RANGE) {
		return LE_TEST_STATUS_EVENT_ERROR;
	}

	err = dtm_test_end(&cnt);

	return err ? LE_TEST_STATUS_EVENT_ERROR : (LE_PACKET_REPORTING_EVENT | cnt);
}

static uint16_t on_test_rx_cmd(uint8_t chan)
{
	int err;

	err = dtm_test_receive(chan);

	return err ? LE_TEST_STATUS_EVENT_ERROR : LE_TEST_STATUS_EVENT_SUCCESS;
}

static uint16_t on_test_tx_cmd(uint8_t chan, uint8_t length, enum dtm_pkt_type type)
{
	enum dtm_packet pkt;
	int err;

	switch (type) {
	case DTM_PKT_PRBS9:
		pkt = DTM_PACKET_PRBS9;
		break;

	case DTM_PKT_0X0F:
		pkt = DTM_PACKET_0F;
		break;

	case DTM_PKT_0X55:
		pkt = DTM_PACKET_55;
		break;

	case DTM_PKT_0XFF_OR_VS:
		pkt = DTM_PACKET_FF_OR_VENDOR;
		break;

	default:
		return LE_TEST_STATUS_EVENT_ERROR;
	}

	length = (length & ~LE_UPPER_BITS_MASK) | upper_len;

	err = dtm_test_transmit(chan, length, pkt);

	return err ? LE_TEST_STATUS_EVENT_ERROR : LE_TEST_STATUS_EVENT_SUCCESS;
}

static uint16_t dtm_cmd_put(uint16_t cmd)
{
	enum dtm_cmd_code cmd_code = (cmd >> 14) & 0x03;

	/* RX and TX test commands */
	uint8_t chan = (cmd >> 8) & 0x3F;
	uint8_t length = (cmd >> 2) & 0x3F;
	enum dtm_pkt_type type = (enum dtm_pkt_type)(cmd & 0x03);

	/* Setup and End commands */
	enum dtm_ctrl_code control = (cmd >> 8) & 0x3F;
	uint8_t parameter = (uint8_t)cmd;

	switch (cmd_code) {
	case LE_TEST_SETUP:
		LOG_DBG("Executing test setup command. Control: %d Parameter: %d", control,
											parameter);
		return on_test_setup_cmd(control, parameter);

	case LE_TEST_END:
		LOG_DBG("Executing test end command. Control: %d Parameter: %d", control,
											parameter);
		return on_test_end_cmd(control, parameter);

	case LE_RECEIVER_TEST:
		LOG_DBG("Executing reception test command. Channel: %d", chan);
		return on_test_rx_cmd(chan);

	case LE_TRANSMITTER_TEST:
		LOG_DBG("Executing transmission test command. Channel: %d Length: %d Type: %d",
										chan, length, type);
		return on_test_tx_cmd(chan, length, type);

	default:
		LOG_ERR("Received unknown command code %d", cmd_code);
		return LE_TEST_STATUS_EVENT_ERROR;
	}
}

int dtm_tr_init(void)
{
	int err;

	if (!device_is_ready(dtm_uart)) {
		LOG_ERR("UART device not ready");
		return -EIO;
	}

	err = dtm_init(NULL);
	if (err) {
		LOG_ERR("Error during DTM initialization: %d", err);
		return err;
	}

	err = dtm_uart_wait_init();
	if (err) {
		return err;
	}

	return 0;
}

union dtm_tr_packet dtm_tr_get(void)
{
	bool is_msb_read = false;
	union dtm_tr_packet tmp;
	uint8_t rx_byte;
	uint16_t dtm_cmd = 0;
	int64_t msb_time = 0;
	int err;

	for (;;) {
		dtm_uart_wait();

		err = uart_poll_in(dtm_uart, &rx_byte);
		if (err) {
			if (err != -1) {
				LOG_ERR("UART polling error: %d", err);
			}

			/* Nothing read from the UART */
			continue;
		}

		if (!is_msb_read) {
			/* This is first byte of two-byte command. */
			is_msb_read = true;
			dtm_cmd = rx_byte << 8;
			msb_time = k_uptime_get();

			/* Go back and wait for 2nd byte of command word. */
			continue;
		}

		/* This is the second byte read; combine it with the first and
		 * process command.
		 */
		if ((k_uptime_get() - msb_time) >
		    DTM_UART_SECOND_BYTE_MAX_DELAY) {
			/* More than ~5mS after msb: Drop old byte, take the
			 * new byte as MSB. The variable is_msb_read will
			 * remain true.
			 */
			dtm_cmd = rx_byte << 8;
			msb_time = k_uptime_get();
			/* Go back and wait for 2nd byte of command word. */
			LOG_DBG("Received byte discarded");
			continue;
		} else {
			dtm_cmd |= rx_byte;
			LOG_INF("Received 0x%04x command", dtm_cmd);
			tmp.twowire = dtm_cmd;
			return tmp;
		}
	}
}

int dtm_tr_process(union dtm_tr_packet cmd)
{
	uint16_t tmp = cmd.twowire;
	uint16_t ret;

	LOG_INF("Processing 0x%04x command", tmp);

	ret = dtm_cmd_put(tmp);
	LOG_INF("Sending 0x%04x response", ret);

	uart_poll_out(dtm_uart, (ret >> 8) & 0xFF);
	uart_poll_out(dtm_uart, ret & 0xFF);

	return 0;
}
