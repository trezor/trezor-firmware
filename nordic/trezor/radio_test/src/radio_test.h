/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef RADIO_TEST_H_
#define RADIO_TEST_H_

#include <zephyr/types.h>
#include <hal/nrf_radio.h>
#include <fem_al/fem_al.h>

#ifdef NRF53_SERIES
#ifndef RADIO_TXPOWER_TXPOWER_Pos3dBm
	#define RADIO_TXPOWER_TXPOWER_Pos3dBm (0x03UL)
#endif /* RADIO_TXPOWER_TXPOWER_Pos3dBm */

#ifndef RADIO_TXPOWER_TXPOWER_Pos2dBm
	#define RADIO_TXPOWER_TXPOWER_Pos2dBm (0x02UL)
#endif /* RADIO_TXPOWER_TXPOWER_Pos2dBm */

#ifndef RADIO_TXPOWER_TXPOWER_Pos1dBm
	#define RADIO_TXPOWER_TXPOWER_Pos1dBm (0x01UL)
#endif /* RADIO_TXPOWER_TXPOWER_Pos1dBm */
#endif /* NRF53_SERIES */

/** Maximum radio RX or TX payload. */
#define RADIO_MAX_PAYLOAD_LEN	256
/** IEEE 802.15.4 maximum payload length. */
#define IEEE_MAX_PAYLOAD_LEN	127
/** IEEE 802.15.4 minimum channel. */
#define IEEE_MIN_CHANNEL	11
/** IEEE 802.15.4 maximum channel. */
#define IEEE_MAX_CHANNEL	26

#define FEM_USE_DEFAULT_TX_POWER_CONTROL 0xFF

/**@brief Radio transmit and address pattern. */
enum transmit_pattern {
	/** Random pattern. */
	TRANSMIT_PATTERN_RANDOM,

	/** Pattern 11110000(F0). */
	TRANSMIT_PATTERN_11110000,

	/** Pattern 11001100(CC). */
	TRANSMIT_PATTERN_11001100,
};

/**@brief Radio test mode. */
enum radio_test_mode {
	/** TX carrier. */
	UNMODULATED_TX,

	/** Modulated TX carrier. */
	MODULATED_TX,

	/** RX carrier. */
	RX,

	/** TX carrier sweep. */
	TX_SWEEP,

	/** RX carrier sweep. */
	RX_SWEEP,

	/** Duty-cycled modulated TX carrier. */
	MODULATED_TX_DUTY_CYCLE,
};

/**@brief Radio test front-end module (FEM) configuration */
struct radio_test_fem {
	/* Front-end module radio ramp-up time in microseconds. */
	uint32_t ramp_up_time;

	/* Front-end module TX power control specific to given front-end module.
	 * For nRF21540 GPIO/SPI, this is a register value.
	 * For nRF21540 GPIO, this is MODE pin value.
	 */
	fem_tx_power_control tx_power_control;
};

/**@brief Radio test configuration. */
struct radio_test_config {
	/** Radio test type. */
	enum radio_test_mode type;

	/** Radio mode. Data rate and modulation. */
	nrf_radio_mode_t mode;

	union {
		struct {
			/** Radio output power. */
			int8_t txpower;

			/** Radio channel. */
			uint8_t channel;
		} unmodulated_tx;

		struct {
			/** Radio output power. */
			int8_t txpower;

			/** Radio transmission pattern. */
			enum transmit_pattern pattern;

			/** Radio channel. */
			uint8_t channel;

			/**
			 * Number of packets to transmit.
			 * Set to zero for continuous TX.
			 */
			uint32_t packets_num;

			/** Callback to indicate that TX is finished. */
			void (*cb)(void);
		} modulated_tx;

		struct {
			/** Radio transmission pattern. */
			enum transmit_pattern pattern;

			/** Radio channel. */
			uint8_t channel;

			/**
			 * Number of packets to be received.
			 * Set to zero for continuous RX.
			 */
			uint32_t packets_num;

			/** Callback to indicate that RX is finished. */
			void (*cb)(void);
		} rx;

		struct {
			/** Radio output power. */
			int8_t txpower;

			/** Radio start channel (frequency). */
			uint8_t channel_start;

			/** Radio end channel (frequency). */
			uint8_t channel_end;

			/** Delay time in milliseconds. */
			uint32_t delay_ms;
		} tx_sweep;

		struct {
			/** Radio start channel (frequency). */
			uint8_t channel_start;

			/** Radio end channel (frequency). */
			uint8_t channel_end;

			/** Delay time in milliseconds. */
			uint32_t delay_ms;
		} rx_sweep;

		struct {
			/** Radio output power. */
			int8_t txpower;

			/** Radio transmission pattern. */
			enum transmit_pattern pattern;

			/** Radio channel. */
			uint8_t channel;

			/** Duty cycle. */
			uint32_t duty_cycle;
		} modulated_tx_duty_cycle;
	} params;

#if CONFIG_FEM
	/* Front-end module (FEM) configuration. */
	struct radio_test_fem fem;
#endif /* CONFIG_FEM */
};

/**@brief Radio RX statistics. */
struct radio_rx_stats {
	/** Content of the last packet. */
	struct {
		/** Content of the last packet. */
		uint8_t *buf;

		/** Length of the last packet. */
		size_t len;
	} last_packet;

	/** Number of received packets with valid CRC. */
	uint32_t packet_cnt;
};

/**
 * @brief Function for initializing the Radio Test module.
 *
 * @param[in] config  Radio test configuration.
 *
 * @retval 0 If the operation was successful.
 *           Otherwise, a (negative) error code is returned.
 */
int radio_test_init(struct radio_test_config *config);

/**
 * @brief Function for starting radio test.
 *
 * @param[in] config  Radio test configuration.
 */
void radio_test_start(const struct radio_test_config *config);

/**
 * @brief Function for stopping ongoing test (Radio and Timer operations).
 */
void radio_test_cancel(void);

/**
 * @brief Function for get RX statistics.
 *
 * @param[out] rx_stats RX statistics.
 */
void radio_rx_stats_get(struct radio_rx_stats *rx_stats);

/**
 * @brief Function for toggling the DC/DC converter state.
 *
 * @param[in] dcdc_state  DC/DC converter state.
 */
void toggle_dcdc_state(uint8_t dcdc_state);

#endif /* RADIO_TEST_H_ */
