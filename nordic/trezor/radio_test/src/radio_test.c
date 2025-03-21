/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include "radio_test.h"

#include <string.h>
#include <inttypes.h>

#if !(defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX))
#include <hal/nrf_power.h>
#endif /* !(defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX)) */

#ifdef NRF53_SERIES
#include <hal/nrf_vreqctrl.h>
#endif /* NRF53_SERIES */

#include <nrfx_timer.h>
#include <zephyr/kernel.h>
#include <zephyr/random/random.h>

#include <hal/nrf_egu.h>
#include <helpers/nrfx_gppi.h>

#if CONFIG_FEM
#include "fem_al/fem_al.h"
#endif /* CONFIG_FEM */

/* IEEE 802.15.4 default frequency. */
#define IEEE_DEFAULT_FREQ         (5)
/* Length on air of the LENGTH field. */
#define RADIO_LENGTH_LENGTH_FIELD (8UL)

#define RADIO_TEST_EGU_EVENT NRF_EGU_EVENT_TRIGGERED0
#define RADIO_TEST_EGU_TASK  NRF_EGU_TASK_TRIGGER0

/* Frequency calculation for a given channel in the IEEE 802.15.4 radio
 * mode.
 */
#define IEEE_FREQ_CALC(_channel) (IEEE_DEFAULT_FREQ + \
				 (IEEE_DEFAULT_FREQ * \
				 ((_channel) - IEEE_MIN_CHANNEL)))
/* Frequency calculation for a given channel. */
#define CHAN_TO_FREQ(_channel) (2400 + _channel)

#if defined(CONFIG_SOC_SERIES_NRF54HX)
	#define RADIO_TEST_EGU                     NRF_EGU020
	#define RADIO_TEST_TIMER_INSTANCE          020
	#define RADIO_TEST_TIMER_IRQn              TIMER020_IRQn
	#define RADIO_TEST_RADIO_IRQn              RADIO_0_IRQn
	#define RADIO_TEST_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_PHYEND_DISABLE_MASK
	#define RADIO_TEST_SHORT_END_START_MASK    NRF_RADIO_SHORT_PHYEND_START_MASK
#elif defined(CONFIG_SOC_SERIES_NRF54LX)
	#define RADIO_TEST_EGU                     NRF_EGU10
	#define RADIO_TEST_TIMER_INSTANCE          10
	#define RADIO_TEST_TIMER_IRQn              TIMER10_IRQn
	#define RADIO_TEST_RADIO_IRQn              RADIO_0_IRQn
	#define RADIO_TEST_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_PHYEND_DISABLE_MASK
	#define RADIO_TEST_SHORT_END_START_MASK    NRF_RADIO_SHORT_PHYEND_START_MASK
#else
	#define RADIO_TEST_EGU                     NRF_EGU0
	#define RADIO_TEST_TIMER_INSTANCE          0
	#define RADIO_TEST_TIMER_IRQn              TIMER0_IRQn
	#define RADIO_TEST_RADIO_IRQn              RADIO_IRQn
	#define RADIO_TEST_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_END_DISABLE_MASK
	#define RADIO_TEST_SHORT_END_START_MASK    NRF_RADIO_SHORT_END_START_MASK
#endif /* defined(CONFIG_SOC_SERIES_NRF54HX) */

#define RADIO_TEST_TIMER_IRQ_HANDLER  NRFX_CONCAT_3(nrfx_timer_,	    \
						 RADIO_TEST_TIMER_INSTANCE, \
						 _irq_handler)

#define ENDPOINT_EGU_RADIO_TX    BIT(1)
#define ENDPOINT_EGU_RADIO_RX    BIT(2)
#define ENDPOINT_TIMER_RADIO_TX  BIT(3)
#define ENDPOINT_FORK_EGU_TIMER  BIT(4)

/* RX timeout counted from the last packet received. */
#define RX_PACKET_TIMEOUT_MS 100

/* Buffer for the radio TX packet */
static uint8_t tx_packet[RADIO_MAX_PAYLOAD_LEN];
/* Buffer for the radio RX packet. */
static uint8_t rx_packet[RADIO_MAX_PAYLOAD_LEN];
/* Number of transmitted packets. */
static uint32_t tx_packet_cnt;
/* Number of received packets with valid CRC. */
static uint32_t rx_packet_cnt;

/* Radio current channel (frequency). */
static uint8_t current_channel;

/* Timer used for channel sweeps and tx with duty cycle. */
static const nrfx_timer_t timer = NRFX_TIMER_INSTANCE(RADIO_TEST_TIMER_INSTANCE);

static bool sweep_processing;

/* Total payload size */
static uint16_t total_payload_size;

/* PPI channel for starting radio */
static uint8_t ppi_radio_start;

/* PPI endpoint status.*/
static atomic_t endpoint_state;

/*  Work element used to handle the end of packet reception. */
static void rx_timeout_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(rx_timeout_work, rx_timeout_work_handler);

/* Pointer to rx timeout callback function. */
static void (**rx_timeout_cb)(void);

#if CONFIG_FEM
static struct radio_test_fem fem;
#endif /* CONFIG_FEM */

static uint16_t channel_to_frequency(nrf_radio_mode_t mode, uint8_t channel)
{
#if CONFIG_HAS_HW_NRF_RADIO_IEEE802154
	if (mode == NRF_RADIO_MODE_IEEE802154_250KBIT) {
		if ((channel >= IEEE_MIN_CHANNEL) &&
			(channel <= IEEE_MAX_CHANNEL)) {
			return CHAN_TO_FREQ(IEEE_FREQ_CALC(channel));
		} else {
			return CHAN_TO_FREQ(IEEE_DEFAULT_FREQ);
		}
	} else {
		return CHAN_TO_FREQ(channel);
	}
#else
	return CHAN_TO_FREQ(channel);
#endif /* CONFIG_HAS_HW_NRF_RADIO_IEEE802154 */
}

static nrf_radio_txpower_t dbm_to_nrf_radio_txpower(int8_t tx_power)
{
	switch (tx_power) {
#if defined(RADIO_TXPOWER_TXPOWER_Neg100dBm)
	case -100:
		return RADIO_TXPOWER_TXPOWER_Neg100dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg100dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg70dBm)
	case -70:
		return RADIO_TXPOWER_TXPOWER_Neg70dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg70dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg46dBm)
	case -46:
		return RADIO_TXPOWER_TXPOWER_Neg46dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg46dBm) */

	case -40:
		return RADIO_TXPOWER_TXPOWER_Neg40dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg30dBm)
	case -30:
		return RADIO_TXPOWER_TXPOWER_Neg30dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg30dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg28dBm)
	case -28:
		return RADIO_TXPOWER_TXPOWER_Neg28dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg28dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg22dBm)
	case -22:
		return RADIO_TXPOWER_TXPOWER_Neg22dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg22dBm) */

	case -20:
		return RADIO_TXPOWER_TXPOWER_Neg20dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg18dBm)
	case -18:
		return RADIO_TXPOWER_TXPOWER_Neg18dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg18dBm) */

	case -16:
		return RADIO_TXPOWER_TXPOWER_Neg16dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg14dBm)
	case -14:
		return RADIO_TXPOWER_TXPOWER_Neg14dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg14dBm) */

	case -12:
		return RADIO_TXPOWER_TXPOWER_Neg12dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg10dBm)
	case -10:
		return RADIO_TXPOWER_TXPOWER_Neg10dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg10dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg9dBm)
	case -9:
		return RADIO_TXPOWER_TXPOWER_Neg9dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg9dBm) */

	case -8:
		return RADIO_TXPOWER_TXPOWER_Neg8dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg7dBm)
	case -7:
		return RADIO_TXPOWER_TXPOWER_Neg7dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg7dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg6dBm)
	case -6:
		return RADIO_TXPOWER_TXPOWER_Neg6dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg6dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg5dBm)
	case -5:
		return RADIO_TXPOWER_TXPOWER_Neg5dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Neg5dBm) */

	case -4:
		return RADIO_TXPOWER_TXPOWER_Neg4dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Neg3dBm)
	case -3:
		return RADIO_TXPOWER_TXPOWER_Neg3dBm;
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg3dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg2dBm)
	case -2:
		return RADIO_TXPOWER_TXPOWER_Neg2dBm;
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg2dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Neg1dBm)
	case -1:
		return RADIO_TXPOWER_TXPOWER_Neg1dBm;
#endif /* defined (RADIO_TXPOWER_TXPOWER_Neg1dBm) */

	case 0:
		return RADIO_TXPOWER_TXPOWER_0dBm;

#if defined(RADIO_TXPOWER_TXPOWER_Pos1dBm)
	case 1:
		return RADIO_TXPOWER_TXPOWER_Pos1dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos1dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos2dBm)
	case 2:
		return RADIO_TXPOWER_TXPOWER_Pos2dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos2dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos3dBm)
	case 3:
		return RADIO_TXPOWER_TXPOWER_Pos3dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos3dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos4dBm)
	case 4:
		return RADIO_TXPOWER_TXPOWER_Pos4dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos4dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos5dBm)
	case 5:
		return RADIO_TXPOWER_TXPOWER_Pos5dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos5dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos6dBm)
	case 6:
		return RADIO_TXPOWER_TXPOWER_Pos6dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos6dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos7dBm)
	case 7:
		return RADIO_TXPOWER_TXPOWER_Pos7dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos7dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos8dBm)
	case 8:
		return RADIO_TXPOWER_TXPOWER_Pos8dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos8dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos9dBm)
	case 9:
		return RADIO_TXPOWER_TXPOWER_Pos9dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos9dBm) */

#if defined(RADIO_TXPOWER_TXPOWER_Pos10dBm)
	case 10:
		return RADIO_TXPOWER_TXPOWER_Pos10dBm;
#endif /* defined(RADIO_TXPOWER_TXPOWER_Pos10dBm) */

	default:
		printk("TX power to enumerator conversion failed, defaulting to 0 dBm\n");
		return RADIO_TXPOWER_TXPOWER_0dBm;
	}
}

static void radio_power_set(nrf_radio_mode_t mode, uint8_t channel, int8_t power)
{
	int8_t output_power = power;
	int8_t radio_power = power;

#if CONFIG_FEM
	uint16_t frequency;

	if (IS_ENABLED(CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC)) {
		frequency = channel_to_frequency(mode, channel);
		output_power = fem_tx_output_power_prepare(power, &radio_power, frequency);
	}
#else
	ARG_UNUSED(mode);
	ARG_UNUSED(channel);
#endif /* CONFIG_FEM */

#ifdef NRF53_SERIES
	bool high_voltage_enable = false;

	if (radio_power > 0) {
		high_voltage_enable = true;

		/* High voltage increases radio output power by 3 dBm. */
		radio_power -= 3;
	}

	nrf_vreqctrl_radio_high_voltage_set(NRF_VREQCTRL, high_voltage_enable);
#endif /* NRF53_SERIES */

	nrf_radio_txpower_set(NRF_RADIO, dbm_to_nrf_radio_txpower(radio_power));

	if (!sweep_processing) {
		printk("Requested tx output power: %" PRIi8 " dBm\n", power);
		printk("Tx output power set to: %" PRIi8 " dBm\n", output_power);
	}
}

static void endpoints_clear(void)
{
	if (atomic_test_and_clear_bit(&endpoint_state, ENDPOINT_FORK_EGU_TIMER)) {
		nrfx_gppi_fork_endpoint_clear(ppi_radio_start,
			nrf_timer_task_address_get(timer.p_reg, NRF_TIMER_TASK_START));
	}
	if (atomic_test_and_clear_bit(&endpoint_state, ENDPOINT_EGU_RADIO_TX)) {
		nrfx_gppi_channel_endpoints_clear(ppi_radio_start,
			nrf_egu_event_address_get(RADIO_TEST_EGU, RADIO_TEST_EGU_EVENT),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	}
	if (atomic_test_and_clear_bit(&endpoint_state, ENDPOINT_EGU_RADIO_RX)) {
		nrfx_gppi_channel_endpoints_clear(ppi_radio_start,
			nrf_egu_event_address_get(RADIO_TEST_EGU, RADIO_TEST_EGU_EVENT),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_RXEN));
	}
	if (atomic_test_and_clear_bit(&endpoint_state, ENDPOINT_TIMER_RADIO_TX)) {
		nrfx_gppi_channel_endpoints_clear(ppi_radio_start,
			nrf_timer_event_address_get(timer.p_reg, NRF_TIMER_EVENT_COMPARE0),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	}
}

static void radio_ppi_config(bool rx)
{
	endpoints_clear();

	nrfx_gppi_channel_endpoints_setup(ppi_radio_start,
			nrf_egu_event_address_get(RADIO_TEST_EGU, RADIO_TEST_EGU_EVENT),
			nrf_radio_task_address_get(NRF_RADIO,
						   rx ? NRF_RADIO_TASK_RXEN : NRF_RADIO_TASK_TXEN));
	atomic_set_bit(&endpoint_state, (rx ? ENDPOINT_EGU_RADIO_RX : ENDPOINT_EGU_RADIO_TX));

	nrfx_gppi_fork_endpoint_setup(ppi_radio_start,
			nrf_timer_task_address_get(timer.p_reg, NRF_TIMER_TASK_START));
	atomic_set_bit(&endpoint_state, ENDPOINT_FORK_EGU_TIMER);

	nrfx_gppi_channels_enable(BIT(ppi_radio_start));
}

static void radio_ppi_tx_reconfigure(void)
{
	if (nrfx_gppi_channel_check(ppi_radio_start)) {
		nrfx_gppi_channels_disable(BIT(ppi_radio_start));
	}

	endpoints_clear();

	nrfx_gppi_channel_endpoints_setup(ppi_radio_start,
		nrf_timer_event_address_get(timer.p_reg, NRF_TIMER_EVENT_COMPARE1),
		nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	atomic_set_bit(&endpoint_state, ENDPOINT_TIMER_RADIO_TX);

	nrfx_gppi_channels_enable(BIT(ppi_radio_start));
}

#if CONFIG_FEM
static int fem_configure(bool rx, nrf_radio_mode_t mode,
			 struct radio_test_fem *fem)
{
	int err;

	/* FEM is kept powered during sweeping */
	if (!sweep_processing) {
		err = fem_power_up();
		if (err) {
			return err;
		}
	}

	if (fem->ramp_up_time == 0) {
		fem->ramp_up_time =
			fem_default_ramp_up_time_get(false, mode);
	}

	if (!sweep_processing) {
		nrf_timer_shorts_enable(timer.p_reg,
			(NRF_TIMER_SHORT_COMPARE2_STOP_MASK | NRF_TIMER_SHORT_COMPARE2_CLEAR_MASK));
	}

	radio_ppi_config(rx);

	if (rx) {
		err = fem_rx_configure(fem->ramp_up_time);
		if (err) {
			printk("Failed to configure LNA.\n");
		}

		return err;
	}

	if ((!IS_ENABLED(CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC)) &&
	    (fem->tx_power_control != FEM_USE_DEFAULT_TX_POWER_CONTROL) &&
	    !sweep_processing) {
		err = fem_tx_power_control_set(fem->tx_power_control);
		if (err) {
			printk("%u: out of range FEM Tx power control value or setting Tx power control is not supported\n",
				fem->tx_power_control);
			return err;
		}
	}

	err = fem_tx_configure(fem->ramp_up_time);
	if (err) {
		printk("Failed to configure PA.\n");
	}

	fem_errata_25X(mode);

	return err;
}
#endif /* CONFIG_FEM */

static void radio_start(bool rx, bool force_egu)
{
	if (IS_ENABLED(CONFIG_FEM) || force_egu) {
		nrf_egu_task_trigger(RADIO_TEST_EGU, RADIO_TEST_EGU_TASK);
	} else {
		nrf_radio_task_trigger(NRF_RADIO, rx ? NRF_RADIO_TASK_RXEN : NRF_RADIO_TASK_TXEN);
	}
}

static void radio_channel_set(nrf_radio_mode_t mode, uint8_t channel)
{
	uint16_t frequency;

	frequency = channel_to_frequency(mode, channel);
	nrf_radio_frequency_set(NRF_RADIO, frequency);
}

static void radio_config(nrf_radio_mode_t mode, enum transmit_pattern pattern)
{
	nrf_radio_packet_conf_t packet_conf;

	/* Set fast ramp-up time. */
#if defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX)
	nrf_radio_fast_ramp_up_enable_set(NRF_RADIO, true);
#else
	nrf_radio_modecnf0_set(NRF_RADIO, true, RADIO_MODECNF0_DTX_Center);
#endif /* defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX) */

	/* Disable CRC. */
	nrf_radio_crc_configure(NRF_RADIO, RADIO_CRCCNF_LEN_Disabled,
				NRF_RADIO_CRC_ADDR_INCLUDE, 0);

	/* Set the device address 0 to use when transmitting. */
	nrf_radio_txaddress_set(NRF_RADIO, 0);
	/* Enable the device address 0 to use to select which addresses to
	 * receive
	 */
	nrf_radio_rxaddresses_set(NRF_RADIO, 1);

	/* Set the address according to the transmission pattern. */
	switch (pattern) {
	case TRANSMIT_PATTERN_RANDOM:
		nrf_radio_prefix0_set(NRF_RADIO, 0xAB);
		nrf_radio_base0_set(NRF_RADIO, 0xABABABAB);
		break;

	case TRANSMIT_PATTERN_11001100:
		nrf_radio_prefix0_set(NRF_RADIO, 0xCC);
		nrf_radio_base0_set(NRF_RADIO, 0xCCCCCCCC);
		break;

	case TRANSMIT_PATTERN_11110000:
		nrf_radio_prefix0_set(NRF_RADIO, 0x6A);
		nrf_radio_base0_set(NRF_RADIO, 0x58FE811B);
		break;

	default:
		return;
	}

	/* Packet configuration:
	 * payload length size = 8 bits,
	 * 0-byte static length, max 255-byte payload,
	 * 4-byte base address length (5-byte full address length),
	 * Bit 24: 1 Big endian,
	 * Bit 25: 1 Whitening enabled.
	 */
	memset(&packet_conf, 0, sizeof(packet_conf));
	packet_conf.lflen = RADIO_LENGTH_LENGTH_FIELD;
	packet_conf.maxlen = (sizeof(tx_packet) - 1);
	packet_conf.statlen = 0;
	packet_conf.balen = 4;
	packet_conf.big_endian = true;
	packet_conf.whiteen = true;

	switch (mode) {
#if CONFIG_HAS_HW_NRF_RADIO_IEEE802154
	case NRF_RADIO_MODE_IEEE802154_250KBIT:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 32-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_32BIT_ZERO;
		packet_conf.maxlen = IEEE_MAX_PAYLOAD_LEN;
		packet_conf.balen = 0;
		packet_conf.big_endian = false;
		packet_conf.whiteen = false;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 4 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#endif /* CONFIG_HAS_HW_NRF_RADIO_IEEE802154 */

#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	case NRF_RADIO_MODE_BLE_LR500KBIT:
	case NRF_RADIO_MODE_BLE_LR125KBIT:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 10 bytes preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_LONG_RANGE;
		packet_conf.cilen = 2;
		packet_conf.termlen = 3;
		packet_conf.big_endian = false;
		packet_conf.balen = 3;

		/* Set CRC length; CRC calculation does not include the address
		 * field.
		 */
		nrf_radio_crc_configure(NRF_RADIO, RADIO_CRCCNF_LEN_Three,
					NRF_RADIO_CRC_ADDR_SKIP, 0);

		/* preamble, address (BALEN + PREFIX), lflen, code indicator, TERM, payload, CRC */
		total_payload_size = 10 + (packet_conf.balen + 1) + 1 + packet_conf.cilen +
				  packet_conf.termlen + packet_conf.maxlen + RADIO_CRCCNF_LEN_Three;
		break;

#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */

	case NRF_RADIO_MODE_BLE_2MBIT:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 16-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 2 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#if defined(RADIO_MODE_MODE_Nrf_4Mbit0_5)
	case NRF_RADIO_MODE_NRF_4MBIT_H_0_5:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 16-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 2 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit0_5) */

#if defined(RADIO_MODE_MODE_Nrf_4Mbit0_25)
	case NRF_RADIO_MODE_NRF_4MBIT_H_0_25:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 16-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 2 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit0_25) */

#if defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT6)
	case NRF_RADIO_MODE_NRF_4MBIT_BT_0_6:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 16-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 2 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT6) */

#if defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT4)
	case NRF_RADIO_MODE_NRF_4MBIT_BT_0_4:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 16-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		/* preamble, address (BALEN + PREFIX), lflen and payload */
		total_payload_size = 2 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT4) */

	default:
		/* Packet configuration:
		 * S1 size = 0 bits,
		 * S0 size = 0 bytes,
		 * 8-bit preamble.
		 */
		packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_8BIT;

		/* preamble, address (BALEN + PREFIX), lflen, and payload */
		total_payload_size = 1 + (packet_conf.balen + 1) + 1 + packet_conf.maxlen;
		break;
	}

	nrf_radio_packet_configure(NRF_RADIO, &packet_conf);
}

static void generate_modulated_rf_packet(uint8_t mode,
					 enum transmit_pattern pattern)
{
	radio_config(mode, pattern);

	/* One byte used for size, actual size is SIZE-1 */
#if CONFIG_HAS_HW_NRF_RADIO_IEEE802154
	if (mode == NRF_RADIO_MODE_IEEE802154_250KBIT) {
		tx_packet[0] = IEEE_MAX_PAYLOAD_LEN - 1;
	} else {
		tx_packet[0] = sizeof(tx_packet) - 1;
	}
#else
	tx_packet[0] = sizeof(tx_packet) - 1;
#endif /* CONFIG_HAS_HW_NRF_RADIO_IEEE802154 */

	switch (pattern) {
	case TRANSMIT_PATTERN_RANDOM:
		sys_rand_get(tx_packet + 1, sizeof(tx_packet) - 1);
		break;
	case TRANSMIT_PATTERN_11001100:
		memset(tx_packet + 1, 0xCC, sizeof(tx_packet) - 1);
		break;
	case TRANSMIT_PATTERN_11110000:
		memset(tx_packet + 1, 0xF0, sizeof(tx_packet) - 1);
		break;
	default:
		/* Do nothing. */
		break;
	}

	nrf_radio_packetptr_set(NRF_RADIO, tx_packet);
}

static void radio_disable(void)
{
	nrf_radio_shorts_set(NRF_RADIO, 0);
	nrf_radio_int_disable(NRF_RADIO, ~0);
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);

	nrf_radio_task_trigger(NRF_RADIO, NRF_RADIO_TASK_DISABLE);
	while (!nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_DISABLED)) {
		/* Do nothing */
	}
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);

#if CONFIG_FEM
	fem_txrx_configuration_clear();
	fem_txrx_stop();

	/* Do not power-down front-end module (FEM) during sweeping. */
	if (!sweep_processing) {
		(void)fem_power_down();
	}
#endif /* CONFIG_FEM */
}

static void mltpan_6(nrf_radio_mode_t mode)
{
#if defined(NRF54L_SERIES)
	if (mode == NRF_RADIO_MODE_IEEE802154_250KBIT) {
		*((volatile uint32_t *)0x5008A810) = 2;
	}
#else
	ARG_UNUSED(mode);
#endif /* defined(NRF54L_SERIES) */
}

#if NRF53_ERRATA_117_PRESENT
static void errata_117(nrf_radio_mode_t mode)
{
	if (!nrf53_errata_117()) {
		return;
	}

	if ((mode == NRF_RADIO_MODE_NRF_2MBIT) ||
	    (mode == NRF_RADIO_MODE_BLE_2MBIT) ||
	    (mode == NRF_RADIO_MODE_IEEE802154_250KBIT)) {
		*((volatile uint32_t *)0x41008588) = *((volatile uint32_t *)0x01FF0084);
	} else {
		*((volatile uint32_t *)0x41008588) = *((volatile uint32_t *)0x01FF0080);
	}
}
#else
static void errata_117(nrf_radio_mode_t mode)
{
	ARG_UNUSED(mode);
}
#endif /* NRF53_ERRATA_117_PRESENT */

static void radio_mode_set(NRF_RADIO_Type *reg, nrf_radio_mode_t mode)
{
	errata_117(mode);
	nrf_radio_mode_set(reg, mode);
	mltpan_6(mode);
}

static void radio_unmodulated_tx_carrier(uint8_t mode, int8_t txpower, uint8_t channel)
{
	radio_disable();

	radio_mode_set(NRF_RADIO, mode);
	nrf_radio_shorts_enable(NRF_RADIO, NRF_RADIO_SHORT_READY_START_MASK);
	radio_power_set(mode, channel, txpower);

	radio_channel_set(mode, channel);

#if CONFIG_FEM
	(void)fem_configure(false, mode, &fem);
#else
	if (sweep_processing) {
		radio_ppi_config(false);
	}
#endif /* CONFIG_FEM */

	radio_start(false, sweep_processing);
}

static void radio_modulated_tx_carrier(uint8_t mode, int8_t txpower, uint8_t channel,
				       enum transmit_pattern pattern, uint32_t packets_num)
{
	radio_disable();
	generate_modulated_rf_packet(mode, pattern);

	switch (mode) {
#if CONFIG_HAS_HW_NRF_RADIO_IEEE802154 || CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	case NRF_RADIO_MODE_IEEE802154_250KBIT:
	case NRF_RADIO_MODE_BLE_LR125KBIT:
	case NRF_RADIO_MODE_BLE_LR500KBIT:
		nrf_radio_shorts_enable(NRF_RADIO,
					NRF_RADIO_SHORT_READY_START_MASK |
					NRF_RADIO_SHORT_PHYEND_START_MASK);
		break;

#endif /* CONFIG_HAS_HW_NRF_RADIO_IEEE802154 || CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */

	case NRF_RADIO_MODE_BLE_1MBIT:
	case NRF_RADIO_MODE_BLE_2MBIT:
	case NRF_RADIO_MODE_NRF_1MBIT:
	case NRF_RADIO_MODE_NRF_2MBIT:
	default:
#if defined(RADIO_MODE_MODE_Nrf_250Kbit)
	case NRF_RADIO_MODE_NRF_250KBIT:
#endif /* defined(RADIO_MODE_MODE_Nrf_250Kbit) */
#if defined(RADIO_MODE_MODE_Nrf_4Mbit0_5)
	case NRF_RADIO_MODE_NRF_4MBIT_H_0_5:
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit0_5) */
#if defined(RADIO_MODE_MODE_Nrf_4Mbit0_25)
	case NRF_RADIO_MODE_NRF_4MBIT_H_0_25:
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit0_25) */
#if defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT6)
	case NRF_RADIO_MODE_NRF_4MBIT_BT_0_6:
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT6) */
#if defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT4)
	case NRF_RADIO_MODE_NRF_4MBIT_BT_0_4:
#endif /* defined(RADIO_MODE_MODE_Nrf_4Mbit_0BT4) */
		nrf_radio_shorts_enable(NRF_RADIO,
					NRF_RADIO_SHORT_READY_START_MASK |
					RADIO_TEST_SHORT_END_START_MASK);
		break;
	}

	radio_mode_set(NRF_RADIO, mode);
	radio_power_set(mode, channel, txpower);

	radio_channel_set(mode, channel);

	tx_packet_cnt = 0;

	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_END);
	if (packets_num != 0U) {
		nrf_radio_int_enable(NRF_RADIO, NRF_RADIO_INT_END_MASK);
	}

#if CONFIG_FEM
	(void)fem_configure(false, mode, &fem);
#endif /* CONFIG_FEM */

	radio_start(false, false);
}

static void radio_rx(uint8_t mode, uint8_t channel, enum transmit_pattern pattern,
		     uint32_t rx_packet_num)
{
	radio_disable();

	radio_mode_set(NRF_RADIO, mode);

	nrf_radio_shorts_enable(NRF_RADIO,
				NRF_RADIO_SHORT_READY_START_MASK |
				NRF_RADIO_SHORT_END_START_MASK);
	nrf_radio_packetptr_set(NRF_RADIO, rx_packet);

	radio_config(mode, pattern);
	radio_channel_set(mode, channel);

	rx_packet_cnt = 0;

	nrf_radio_int_enable(NRF_RADIO, NRF_RADIO_INT_CRCOK_MASK);

#if CONFIG_FEM
	(void)fem_configure(true, mode, &fem);
#else
	if (sweep_processing) {
		radio_ppi_config(true);
	}
#endif /* CONFIG_FEM */

	radio_start(true, sweep_processing);

	if (rx_packet_num > 0) {
		k_work_reschedule(&rx_timeout_work, K_SECONDS(CONFIG_RADIO_TEST_RX_TIMEOUT));
	}
}

static void radio_sweep_start(uint8_t channel, uint32_t delay_ms)
{
	current_channel = channel;

#if CONFIG_FEM
	(void)fem_power_up();

	if ((!IS_ENABLED(CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC)) &&
	    fem.tx_power_control != FEM_USE_DEFAULT_TX_POWER_CONTROL) {
		(void)fem_tx_power_control_set(fem.tx_power_control);
	}
#endif /* CONFIG_FEM */

	nrfx_timer_disable(&timer);
	nrf_timer_shorts_disable(timer.p_reg, ~0);
	nrf_timer_int_disable(timer.p_reg, ~0);

	nrfx_timer_extended_compare(&timer,
		NRF_TIMER_CC_CHANNEL0,
		nrfx_timer_ms_to_ticks(&timer, delay_ms),
		(NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK |
		NRF_TIMER_SHORT_COMPARE0_STOP_MASK),
		true);

	nrfx_timer_enable(&timer);
}

static void radio_modulated_tx_carrier_duty_cycle(uint8_t mode, int8_t txpower,
						  uint8_t channel,
						  enum transmit_pattern pattern,
						  uint32_t duty_cycle)
{
	/* Lookup table with time per byte in each radio MODE
	 * Mapped per NRF_RADIO->MODE available on nRF5-series devices
	 */
	static const uint8_t time_in_us_per_byte[16] = {
		8, 4, 32, 8, 4, 64, 16, 0, 0, 2, 2, 0, 0, 0, 0, 32
	};

	radio_disable();
	generate_modulated_rf_packet(mode, pattern);

	radio_mode_set(NRF_RADIO, mode);
	nrf_radio_shorts_enable(NRF_RADIO,
				NRF_RADIO_SHORT_READY_START_MASK |
				RADIO_TEST_SHORT_END_DISABLE_MASK);
	radio_power_set(mode, channel, txpower);
	radio_channel_set(mode, channel);

	const uint32_t total_time_per_payload = time_in_us_per_byte[mode] * total_payload_size;

	/* Duty cycle = 100 * Time_on / (time_on + time_off),
	 * we need to calculate "time_off" for delay.
	 * In addition, the timer includes the "total_time_per_payload",
	 * so we need to add this to the total timer cycle.
	 */
	uint32_t delay_time = total_time_per_payload +
			   ((100 * total_time_per_payload - (total_time_per_payload * duty_cycle)) /
			   duty_cycle);

	/* We let the TIMER start the radio transmission again. */
	nrfx_timer_disable(&timer);

#if CONFIG_FEM
	(void)fem_configure(false, mode, &fem);
#else
	radio_ppi_config(false);
#endif /* CONFIG_FEM */

	nrf_timer_shorts_disable(timer.p_reg, ~0);
	nrf_timer_int_disable(timer.p_reg, ~0);

	nrfx_timer_extended_compare(&timer,
		NRF_TIMER_CC_CHANNEL1,
		nrfx_timer_us_to_ticks(&timer, delay_time),
		NRF_TIMER_SHORT_COMPARE1_CLEAR_MASK,
		false);

	unsigned int key = irq_lock();

	radio_start(false, true);

	radio_ppi_tx_reconfigure();
	irq_unlock(key);
}

void radio_test_start(const struct radio_test_config *config)
{
#if CONFIG_FEM
	fem = config->fem;
#endif /* CONFIG_FEM */

	switch (config->type) {
	case UNMODULATED_TX:
		radio_unmodulated_tx_carrier(config->mode,
			config->params.unmodulated_tx.txpower,
			config->params.unmodulated_tx.channel);
		break;
	case MODULATED_TX:
		radio_modulated_tx_carrier(config->mode,
			config->params.modulated_tx.txpower,
			config->params.modulated_tx.channel,
			config->params.modulated_tx.pattern,
			config->params.modulated_tx.packets_num);
		break;
	case RX:
		radio_rx(config->mode,
			config->params.rx.channel,
			config->params.rx.pattern,
			config->params.rx.packets_num);
		break;
	case TX_SWEEP:
		radio_sweep_start(config->params.tx_sweep.channel_start,
			config->params.tx_sweep.delay_ms);
		break;
	case RX_SWEEP:
		radio_sweep_start(config->params.rx_sweep.channel_start,
			config->params.rx_sweep.delay_ms);
		break;
	case MODULATED_TX_DUTY_CYCLE:
		radio_modulated_tx_carrier_duty_cycle(config->mode,
			config->params.modulated_tx_duty_cycle.txpower,
			config->params.modulated_tx_duty_cycle.channel,
			config->params.modulated_tx_duty_cycle.pattern,
			config->params.modulated_tx_duty_cycle.duty_cycle);
		break;
	}
}

void radio_test_cancel(void)
{
	nrfx_timer_disable(&timer);
	nrfx_timer_clear(&timer);

	sweep_processing = false;

	if (nrfx_gppi_channel_check(ppi_radio_start)) {
		nrfx_gppi_channels_disable(BIT(ppi_radio_start));
	}

	endpoints_clear();
	radio_disable();
}

void radio_rx_stats_get(struct radio_rx_stats *rx_stats)
{
	size_t size;

#if CONFIG_HAS_HW_NRF_RADIO_IEEE802154
	nrf_radio_mode_t radio_mode;

	radio_mode = nrf_radio_mode_get(NRF_RADIO);
	if (radio_mode == NRF_RADIO_MODE_IEEE802154_250KBIT) {
		size = IEEE_MAX_PAYLOAD_LEN;
	} else {
		size = sizeof(rx_packet);
	}
#else
	size = sizeof(rx_packet);
#endif /* CONFIG_HAS_HW_NRF_RADIO_IEEE802154 */

	rx_stats->last_packet.buf = rx_packet;
	rx_stats->last_packet.len = size;
	rx_stats->packet_cnt = rx_packet_cnt;
}

#if NRF_POWER_HAS_DCDCEN_VDDH || NRF_POWER_HAS_DCDCEN
void toggle_dcdc_state(uint8_t dcdc_state)
{
	bool is_enabled;

#if NRF_POWER_HAS_DCDCEN_VDDH
	if (dcdc_state == 0) {
		is_enabled = nrf_power_dcdcen_vddh_get(NRF_POWER);
		nrf_power_dcdcen_vddh_set(NRF_POWER, !is_enabled);
		return;
	}
#endif /* NRF_POWER_HAS_DCDCEN_VDDH */

#if NRF_POWER_HAS_DCDCEN
	if (dcdc_state <= 1) {
		is_enabled = nrf_power_dcdcen_get(NRF_POWER);
		nrf_power_dcdcen_set(NRF_POWER, !is_enabled);
		return;
	}
#endif /* NRF_POWER_HAS_DCDCEN */
}
#endif /* NRF_POWER_HAS_DCDCEN_VDDH || NRF_POWER_HAS_DCDCEN */

static void rx_timeout_work_handler(struct k_work *work)
{
	radio_disable();
	if (rx_timeout_cb != NULL && *rx_timeout_cb != NULL) {
		(*rx_timeout_cb)();
	}
}

static void timer_handler(nrf_timer_event_t event_type, void *context)
{
	const struct radio_test_config *config =
		(const struct radio_test_config *) context;

	if (event_type == NRF_TIMER_EVENT_COMPARE0) {
		uint8_t channel_start;
		uint8_t channel_end;

		if (config->type == TX_SWEEP) {
			sweep_processing = true;
			radio_unmodulated_tx_carrier(config->mode,
				config->params.tx_sweep.txpower,
				current_channel);

			channel_start = config->params.tx_sweep.channel_start;
			channel_end = config->params.tx_sweep.channel_end;
		} else if (config->type == RX_SWEEP) {
			sweep_processing = true;
			radio_rx(config->mode,
				current_channel,
				config->params.rx.pattern,
				0);

			channel_start = config->params.rx_sweep.channel_start;
			channel_end = config->params.rx_sweep.channel_end;
		} else {
			printk("Unexpected test type: %d\n", config->type);
			return;
		}

		sweep_processing = false;

		current_channel++;
		if (current_channel > channel_end) {
			current_channel = channel_start;
		}
	}
}

static void timer_init(const struct radio_test_config *config)
{
	nrfx_err_t          err;
	nrfx_timer_config_t timer_cfg = {
		.frequency = NRFX_MHZ_TO_HZ(1),
		.mode      = NRF_TIMER_MODE_TIMER,
		.bit_width = NRF_TIMER_BIT_WIDTH_24,
		.p_context = (void *) config,
	};

	err = nrfx_timer_init(&timer, &timer_cfg, timer_handler);
	if (err != NRFX_SUCCESS) {
		printk("nrfx_timer_init failed with: %d\n", err);
	}
}

void radio_handler(const void *context)
{
	const struct radio_test_config *config =
		(const struct radio_test_config *) context;

	if (nrf_radio_int_enable_check(NRF_RADIO, NRF_RADIO_INT_CRCOK_MASK) &&
	    nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_CRCOK)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_CRCOK);
		rx_packet_cnt++;
		if (config->params.rx.packets_num) {
			if (rx_packet_cnt == config->params.rx.packets_num) {
				k_work_reschedule(&rx_timeout_work, K_NO_WAIT);
			} else {
				k_work_reschedule(&rx_timeout_work, K_MSEC(RX_PACKET_TIMEOUT_MS));
			}
		}
	}

	if (nrf_radio_int_enable_check(NRF_RADIO, NRF_RADIO_INT_END_MASK) &&
	    nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_END)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_END);

		tx_packet_cnt++;
		if (tx_packet_cnt == config->params.modulated_tx.packets_num) {
			radio_disable();
			config->params.modulated_tx.cb();
		}
	}
}

int radio_test_init(struct radio_test_config *config)
{
	nrfx_err_t nrfx_err;

	timer_init(config);
	IRQ_CONNECT(RADIO_TEST_TIMER_IRQn, IRQ_PRIO_LOWEST,
		RADIO_TEST_TIMER_IRQ_HANDLER, NULL, 0);

	irq_connect_dynamic(RADIO_TEST_RADIO_IRQn, IRQ_PRIO_LOWEST, radio_handler, config, 0);
	irq_enable(RADIO_TEST_RADIO_IRQn);

	nrfx_err = nrfx_gppi_channel_alloc(&ppi_radio_start);
	if (nrfx_err != NRFX_SUCCESS) {
		printk("Failed to allocate gppi channel.\n");
		return -EFAULT;
	}

	rx_timeout_cb = &config->params.rx.cb;

#if CONFIG_FEM
	int err = fem_init(timer.p_reg,
			   (BIT(NRF_TIMER_CC_CHANNEL2) | BIT(NRF_TIMER_CC_CHANNEL3)));

	if (err) {
		return err;
	}
#endif /* CONFIG_FEM */

	return 0;
}
