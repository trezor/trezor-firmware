/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <string.h>
#include <stdlib.h>

#include "dtm.h"
#include "dtm_hw.h"
#include "dtm_hw_config.h"

#if CONFIG_FEM
#include <fem_al/fem_al.h>
#endif /* CONFIG_FEM */

#include <zephyr/kernel.h>
#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>
#include <zephyr/sys/__assert.h>
#if !(defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX))
#include <hal/nrf_nvmc.h>
#endif /* !defined(CONFIG_SOC_SERIES_NRF54HX) || defined(CONFIG_SOC_SERIES_NRF54LX) */

#include <hal/nrf_egu.h>
#include <hal/nrf_radio.h>

#if defined(CONFIG_CLOCK_CONTROL_NRF2)
#include <hal/nrf_lrcconf.h>
#endif

#ifdef NRF53_SERIES
#include <hal/nrf_vreqctrl.h>
#endif /* NRF53_SERIES */

#include <helpers/nrfx_gppi.h>
#include <nrfx_timer.h>
#include <nrf_erratas.h>

#if defined(CONFIG_SOC_SERIES_NRF54HX)
	#define DEFAULT_TIMER_INSTANCE            020
	#define RADIO_IRQn                        RADIO_0_IRQn
	#define DTM_EGU                           NRF_EGU020
	#define DTM_RADIO_SHORT_READY_START_MASK  NRF_RADIO_SHORT_READY_START_MASK
	#define DTM_RADIO_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_PHYEND_DISABLE_MASK
#elif defined(CONFIG_SOC_SERIES_NRF54LX)
	#define DEFAULT_TIMER_INSTANCE            10
	#define RADIO_IRQn                        RADIO_0_IRQn
	#define DTM_EGU                           NRF_EGU10
	#define DTM_RADIO_SHORT_READY_START_MASK  NRF_RADIO_SHORT_READY_START_MASK
	#define DTM_RADIO_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_PHYEND_DISABLE_MASK
#else
	#define DEFAULT_TIMER_INSTANCE            0
	#define RADIO_IRQn                        RADIO_IRQn
	#define DTM_EGU                           NRF_EGU0
	#define DTM_RADIO_SHORT_READY_START_MASK  NRF_RADIO_SHORT_READY_START_MASK
	#define DTM_RADIO_SHORT_END_DISABLE_MASK  NRF_RADIO_SHORT_END_DISABLE_MASK
#endif /* defined(CONFIG_SOC_SERIES_NRF54HX) */

/* Default timer used for timing. */
#define DEFAULT_TIMER_IRQ          NRFX_CONCAT_3(TIMER,			 \
						 DEFAULT_TIMER_INSTANCE, \
						 _IRQn)
#define DEFAULT_TIMER_IRQ_HANDLER  NRFX_CONCAT_3(nrfx_timer_,		 \
						 DEFAULT_TIMER_INSTANCE, \
						 _irq_handler)

/* Note that the timer instance 1 can be used in the communication module. */

/* Note that the timer instance 2 is used in the FEM driver. */

#if NRF52_ERRATA_172_PRESENT
/* Timer used for the workaround for errata 172 on affected nRF5 devices. */
#define ANOMALY_172_TIMER_INSTANCE     3
#define ANOMALY_172_TIMER_IRQ          NRFX_CONCAT_3(TIMER,		    \
						ANOMALY_172_TIMER_INSTANCE, \
						_IRQn)
#define ANOMALY_172_TIMER_IRQ_HANDLER  NRFX_CONCAT_3(nrfx_timer_,	    \
						ANOMALY_172_TIMER_INSTANCE, \
						_irq_handler)
#endif /* NRF52_ERRATA_172_PRESENT */

/* Helper macro for labeling timer instances. */
#define NRFX_TIMER_CONFIG_LABEL(_num) NRFX_CONCAT_3(CONFIG_, NRFX_TIMER, _num)

BUILD_ASSERT(NRFX_TIMER_CONFIG_LABEL(DEFAULT_TIMER_INSTANCE) == 1,
	     "Core DTM timer needs additional KConfig configuration");
#if NRF52_ERRATA_172_PRESENT
BUILD_ASSERT(NRFX_TIMER_CONFIG_LABEL(ANOMALY_172_TIMER_INSTANCE) == 1,
	     "Anomaly DTM timer needs additional KConfig configuration");
#endif /* NRF52_ERRATA_172_PRESENT */

#define DTM_EGU_EVENT NRF_EGU_EVENT_TRIGGERED0
#define DTM_EGU_TASK  NRF_EGU_TASK_TRIGGER0

#define ENDPOINT_EGU_RADIO_TX    BIT(1)
#define ENDPOINT_EGU_RADIO_RX    BIT(2)
#define ENDPOINT_TIMER_RADIO_TX  BIT(3)
#define ENDPOINT_FORK_EGU_TIMER  BIT(4)

/* Values that for now are "constants" - they could be configured by a function
 * setting them, but most of these are set by the BLE DTM standard, so changing
 * them is not relevant.
 * RF-PHY test packet patterns, for the repeated octet packets.
 */
#define RFPHY_TEST_0X0F_REF_PATTERN  0x0F
#define RFPHY_TEST_0X55_REF_PATTERN  0x55
#define RFPHY_TEST_0XFF_REF_PATTERN  0xFF
#define RFPHY_TEST_0X00_REF_PATTERN  0x00
#define RFPHY_TEST_0XF0_REF_PATTERN  0xF0
#define RFPHY_TEST_0XAA_REF_PATTERN  0xAA

/* Time between start of TX packets (in us). */
#define TX_INTERVAL 625
/* The RSSI threshold at which to toggle strict mode. */
#define BLOCKER_FIX_RSSI_THRESHOLD 95
/* Timeout of Anomaly timer (in ms). */
#define BLOCKER_FIX_WAIT_DEFAULT 10
/* Timeout of Anomaly timer (in us) */
#define BLOCKER_FIX_WAIT_END 500
/* Threshold used to determine necessary strict mode status changes. */
#define BLOCKER_FIX_CNTDETECTTHR 15
/* Threshold used to determine necessary strict mode status changes. */
#define BLOCKER_FIX_CNTADDRTHR 2

/* DTM Radio address. */
#define DTM_RADIO_ADDRESS 0x71764129

/* Index where the header of the pdu is located. */
#define DTM_HEADER_OFFSET 0
/* Size of PDU header. */
#define DTM_HEADER_SIZE 2
/* Size of PDU header with CTEInfo field. */
#define DTM_HEADER_WITH_CTE_SIZE 3
/* CTEInfo field offset in payload. */
#define DTM_HEADER_CTEINFO_OFFSET 2
/* CTE Reference period sample count. */
#define DTM_CTE_REF_SAMPLE_CNT 8
/* CTEInfo Preset bit. Indicates whether
 * the CTEInfo field is present in the packet.
 */
#define DTM_PKT_CP_BIT 0x20
/* Maximum payload size allowed during DTM execution. */
#define DTM_PAYLOAD_MAX_SIZE     255
/* Index where the length of the payload is encoded. */
#define DTM_LENGTH_OFFSET        (DTM_HEADER_OFFSET + 1)
/* Maximum PDU size allowed during DTM execution. */
#define DTM_PDU_MAX_MEMORY_SIZE \
	(DTM_HEADER_WITH_CTE_SIZE + DTM_PAYLOAD_MAX_SIZE)
/* Size of the packet on air without the payload
 * (preamble + sync word + type + RFU + length + CRC).
 */
#define DTM_ON_AIR_OVERHEAD_SIZE  10
/**< CRC polynomial. */
#define CRC_POLY                  (0x0000065B)
/* Initial value for CRC calculation. */
#define CRC_INIT                  (0x00555555)
/* Length of S0 field in packet Header (in bytes). */
#define PACKET_HEADER_S0_LEN      1
/* Length of S1 field in packet Header (in bits). */
#define PACKET_HEADER_S1_LEN      0
/* Length of length field in packet Header (in bits). */
#define PACKET_HEADER_LF_LEN      8
/* Number of bytes sent in addition to the variable payload length. */
#define PACKET_STATIC_LEN         0
/* Base address length in bytes. */
#define PACKET_BA_LEN             3
/* CTE IQ sample data size. */
#define DTM_CTE_SAMPLE_DATA_SIZE  0x52
/* Vendor specific packet type for internal use. */
#define DTM_PKT_TYPE_VENDORSPECIFIC  0xFE
/* 1111111 bit pattern packet type for internal use. */
#define DTM_PKT_TYPE_0xFF            0xFF

/* Maximum number of payload octets that the local Controller supports for
 * transmission of a single Link Layer Data Physical Channel PDU.
 */
#define NRF_MAX_PAYLOAD_OCTETS   0x00FF

/* Maximum length of the Constant Tone Extension that the local Controller
 * supports for transmission in a Link Layer packet, in 8 us units.
 */
#define NRF_CTE_MAX_LENGTH 0x14
/* CTE time unit in us. CTE length is expressed in 8us unit. */
#define NRF_CTE_TIME_IN_US 0x08

/* Constant defining RX mode for radio during DTM test. */
#define RX_MODE  true
/* Constant defining TX mode for radio during DTM test. */
#define TX_MODE  false

/* Maximum number of valid channels in BLE. */
#define PHYS_CH_MAX 39

#define FEM_USE_DEFAULT_TX_POWER_CONTROL 0xFF

/* Minimum supported CTE length in 8 us units. */
#define CTE_LENGTH_MIN 0x02

/* Maximum supported CTE length in 8 us units. */
#define CTE_LENGTH_MAX 0x14

/* Mask of the Type in the CTEInfo. */
#define CTEINFO_TYPE_MASK 0x03

/* Position of the Type in the CTEInfo. */
#define CTEINFO_TYPE_POS 0x06

/* Mask of the Time in the CTEInfo. */
#define CTEINFO_TIME_MASK 0x1F

/* Maximimum channel number */
#define DTM_MAX_CHAN_NR 0x27

/* States used for the DTM test implementation */
enum dtm_state {
	/* DTM is uninitialized */
	STATE_UNINITIALIZED,

	/* DTM initialized, or current test has completed */
	STATE_IDLE,

	/* DTM Transmission test is running */
	STATE_TRANSMITTER_TEST,

	/* DTM Carrier test is running (Vendor specific test) */
	STATE_CARRIER_TEST,

	/* DTM Receive test is running */
	STATE_RECEIVER_TEST,
};

/* Constant Tone Extension mode. */
enum dtm_cte_mode {
	/* Do not use the Constant Tone Extension. */
	DTM_CTE_MODE_OFF = 0x00,

	/* Constant Tone Extension: Use Angle-of-Departure. */
	DTM_CTE_MODE_AOD = 0x02,

	/* Constant Tone Extension: Use Angle-of-Arrival. */
	DTM_CTE_MODE_AOA = 0x03
};

/* Constatnt Tone Extension slot. */
enum dtm_cte_slot {
	/* Constant Tone Extension: Sample with 1 us slot. */
	DTM_CTE_SLOT_2US = 0x01,

	/* Constant Tone Extension: Sample with 2 us slot. */
	DTM_CTE_SLOT_1US = 0x02,
};

/* The PDU payload type for each bit pattern. Identical to the PKT value
 * except pattern 0xFF which is 0x04.
 */
enum dtm_pdu_type {
	/* PRBS9 bit pattern */
	DTM_PDU_TYPE_PRBS9 = 0x00,

	/* 11110000 bit pattern  (LSB is the leftmost bit). */
	DTM_PDU_TYPE_0X0F = 0x01,

	/* 10101010 bit pattern (LSB is the leftmost bit). */
	DTM_PDU_TYPE_0X55 = 0x02,

	/* PRBS15 bit pattern */
	DTM_PDU_TYPE_PRBS15 = 0x03,

	/* 11111111 bit pattern */
	DTM_PDU_TYPE_0XFF = 0x04,

	/* 00000000 bit pattern */
	DTM_PDU_TYPE_0X00 = 0x05,

	/* 00001111 bit pattern  (LSB is the leftmost bit). */
	DTM_PDU_TYPE_0XF0 = 0x06,

	/* 01010101 bit pattern (LSB is the leftmost bit). */
	DTM_PDU_TYPE_0XAA = 0x07
};

/* Vendor Specific DTM subcommand for Transmitter Test command.
 * It replaces Frequency field and must be combined with DTM_PKT_0XFF_OR_VS
 * packet type.
 */
enum dtm_vs_subcmd {
	/* Length=0 indicates a constant, unmodulated carrier until LE_TEST_END
	 * or LE_RESET
	 */
	CARRIER_TEST = 0,

	/* nRFgo Studio uses value 1 in length field, to indicate a constant,
	 * unmodulated carrier until LE_TEST_END or LE_RESET
	 */
	CARRIER_TEST_STUDIO = 1,

	/* Set transmission power, value -40..+4 dBm in steps of 4 */
	SET_TX_POWER = 2,

	/* Switch front-end module (FEM) antenna. */
	FEM_ANTENNA_SELECT = 3,

	/* Set front-end module (FEM) tx power control value. */
	FEM_TX_POWER_CONTROL_SET = 4,

	/* Set FEM ramp-up time. */
	FEM_RAMP_UP_SET = 5,

	/* Restore front-end module (FEM) default parameters (antenna, gain, delay). */
	FEM_DEFAULT_PARAMS_SET = 6
};

/* Structure holding the PDU used for transmitting/receiving a PDU. */
struct dtm_pdu {
	/* PDU packet content. */
	uint8_t content[DTM_PDU_MAX_MEMORY_SIZE];
};

struct dtm_cte_info {
	/* Constant Tone Extension mode. */
	enum dtm_cte_mode mode;

	/* Constant Tone Extension sample slot */
	enum dtm_cte_slot slot;

	/* Antenna switch pattern. */
	uint8_t *antenna_pattern;

	/* Antenna switch pattern length. */
	uint8_t antenna_pattern_len;

	/* Received CTE IQ sample data. */
	uint32_t data[DTM_CTE_SAMPLE_DATA_SIZE];

	/* Constant Tone Extension length in 8us unit. */
	uint8_t time;

	/* Number of antenna in the antenna array. */
	uint8_t antenna_number;

	/* CTEInfo. */
	uint8_t info;

	/* IQ Report callback */
	dtm_iq_report_callback_t iq_rep_cb;
};

#if CONFIG_FEM
struct fem_parameters {
	/* Front-end module ramp-up time in microseconds. */
	uint32_t ramp_up_time;

	/* Front-end module vendor ramp-up time in microseconds. */
	uint32_t vendor_ramp_up_time;

	/* Front-end module Tx power control in unit specific for used FEM.
	 * For nRF21540 GPIO/SPI, this is a register value.
	 * For nRF21540 GPIO, this is MODE pin value.
	 */
	fem_tx_power_control tx_power_control;
};
#endif /* CONFIG_FEM */

/* DTM instance definition */
static struct dtm_instance {
	/* Current machine state. */
	enum dtm_state state;

	/* Number of valid packets received. */
	uint16_t rx_pkt_count;

	/* RX/TX PDU. */
	struct dtm_pdu pdu[2];

	/* Current RX/TX PDU buffer. */
	struct dtm_pdu *current_pdu;

	/* Payload length of TX PDU, bits 2:7 of 16-bit dtm command. */
	uint32_t packet_len;

	/* Type of test packet. */
	enum dtm_packet packet_type;

	/* 0..39 physical channel number (base 2402 MHz, Interval 2 MHz) */
	uint32_t phys_ch;

	/* Length of the preamble. */
	nrf_radio_preamble_length_t packet_hdr_plen;

	/* Address. */
	uint32_t address;

	/* Timer to be used for scheduling TX packets. */
	const nrfx_timer_t timer;

#if NRF52_ERRATA_172_PRESENT
	/* Timer to be used to handle Anomaly 172. */
	const nrfx_timer_t anomaly_timer;

	/* Enable or disable the workaround for Errata 172. */
	bool anomaly_172_wa_enabled;
#endif /* NRF52_ERRATA_172_PRESENT */

	/* Enable or disable strict mode to workaround Errata 172. */
	bool strict_mode;

	/* Radio PHY mode. */
	nrf_radio_mode_t radio_mode;

	/* Radio output power. */
	int8_t txpower;

	/* Constant Tone Extension configuration. */
	struct dtm_cte_info cte_info;

#if CONFIG_FEM
	/* Front-end module (FEM) parameters. */
	struct fem_parameters fem;
#endif

	/* Radio Enable PPI channel. */
	uint8_t ppi_radio_start;

	/* PPI endpoint status.*/
	atomic_t endpoint_state;
} dtm_inst = {
	.state = STATE_UNINITIALIZED,
	.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_8BIT,
	.address = DTM_RADIO_ADDRESS,
	.timer = NRFX_TIMER_INSTANCE(DEFAULT_TIMER_INSTANCE),
#if NRF52_ERRATA_172_PRESENT
	.anomaly_timer = NRFX_TIMER_INSTANCE(ANOMALY_172_TIMER_INSTANCE),
#endif /* NRF52_ERRATA_172_PRESENT */
	.radio_mode = NRF_RADIO_MODE_BLE_1MBIT,
	.txpower = 0,
#if CONFIG_FEM
	.fem.tx_power_control = FEM_USE_DEFAULT_TX_POWER_CONTROL,
#endif
};

/* The PRBS9 sequence used as packet payload.
 * The bytes in the sequence is in the right order, but the bits of each byte
 * in the array is reverse of that found by running the PRBS9 algorithm.
 * This is because of the endianness of the nRF5 radio.
 */
static uint8_t const dtm_prbs9_content[] = {
	0xFF, 0xC1, 0xFB, 0xE8, 0x4C, 0x90, 0x72, 0x8B,
	0xE7, 0xB3, 0x51, 0x89, 0x63, 0xAB, 0x23, 0x23,
	0x02, 0x84, 0x18, 0x72, 0xAA, 0x61, 0x2F, 0x3B,
	0x51, 0xA8, 0xE5, 0x37, 0x49, 0xFB, 0xC9, 0xCA,
	0x0C, 0x18, 0x53, 0x2C, 0xFD, 0x45, 0xE3, 0x9A,
	0xE6, 0xF1, 0x5D, 0xB0, 0xB6, 0x1B, 0xB4, 0xBE,
	0x2A, 0x50, 0xEA, 0xE9, 0x0E, 0x9C, 0x4B, 0x5E,
	0x57, 0x24, 0xCC, 0xA1, 0xB7, 0x59, 0xB8, 0x87,
	0xFF, 0xE0, 0x7D, 0x74, 0x26, 0x48, 0xB9, 0xC5,
	0xF3, 0xD9, 0xA8, 0xC4, 0xB1, 0xD5, 0x91, 0x11,
	0x01, 0x42, 0x0C, 0x39, 0xD5, 0xB0, 0x97, 0x9D,
	0x28, 0xD4, 0xF2, 0x9B, 0xA4, 0xFD, 0x64, 0x65,
	0x06, 0x8C, 0x29, 0x96, 0xFE, 0xA2, 0x71, 0x4D,
	0xF3, 0xF8, 0x2E, 0x58, 0xDB, 0x0D, 0x5A, 0x5F,
	0x15, 0x28, 0xF5, 0x74, 0x07, 0xCE, 0x25, 0xAF,
	0x2B, 0x12, 0xE6, 0xD0, 0xDB, 0x2C, 0xDC, 0xC3,
	0x7F, 0xF0, 0x3E, 0x3A, 0x13, 0xA4, 0xDC, 0xE2,
	0xF9, 0x6C, 0x54, 0xE2, 0xD8, 0xEA, 0xC8, 0x88,
	0x00, 0x21, 0x86, 0x9C, 0x6A, 0xD8, 0xCB, 0x4E,
	0x14, 0x6A, 0xF9, 0x4D, 0xD2, 0x7E, 0xB2, 0x32,
	0x03, 0xC6, 0x14, 0x4B, 0x7F, 0xD1, 0xB8, 0xA6,
	0x79, 0x7C, 0x17, 0xAC, 0xED, 0x06, 0xAD, 0xAF,
	0x0A, 0x94, 0x7A, 0xBA, 0x03, 0xE7, 0x92, 0xD7,
	0x15, 0x09, 0x73, 0xE8, 0x6D, 0x16, 0xEE, 0xE1,
	0x3F, 0x78, 0x1F, 0x9D, 0x09, 0x52, 0x6E, 0xF1,
	0x7C, 0x36, 0x2A, 0x71, 0x6C, 0x75, 0x64, 0x44,
	0x80, 0x10, 0x43, 0x4E, 0x35, 0xEC, 0x65, 0x27,
	0x0A, 0xB5, 0xFC, 0x26, 0x69, 0x3F, 0x59, 0x99,
	0x01, 0x63, 0x8A, 0xA5, 0xBF, 0x68, 0x5C, 0xD3,
	0x3C, 0xBE, 0x0B, 0xD6, 0x76, 0x83, 0xD6, 0x57,
	0x05, 0x4A, 0x3D, 0xDD, 0x81, 0x73, 0xC9, 0xEB,
	0x8A, 0x84, 0x39, 0xF4, 0x36, 0x0B, 0xF7
};

static uint8_t const dtm_prbs15_content[] = {
	0xFF, 0x7F, 0x00, 0x20, 0x00, 0x18, 0x00, 0x0A,
	0x80, 0x07, 0x20, 0x02, 0x98, 0x01, 0xAA, 0x80,
	0x7F, 0x20, 0x20, 0x18, 0x18, 0x0A, 0x8A, 0x87,
	0x27, 0x22, 0x9A, 0x99, 0xAB, 0x2A, 0xFF, 0x5F,
	0x00, 0x38, 0x00, 0x12, 0x80, 0x0D, 0xA0, 0x05,
	0xB8, 0x03, 0x32, 0x81, 0xD5, 0xA0, 0x5F, 0x38,
	0x38, 0x12, 0x92, 0x8D, 0xAD, 0xA5, 0xBD, 0xBB,
	0x31, 0xB3, 0x54, 0x75, 0xFF, 0x67, 0x00, 0x2A,
	0x80, 0x1F, 0x20, 0x08, 0x18, 0x06, 0x8A, 0x82,
	0xE7, 0x21, 0x8A, 0x98, 0x67, 0x2A, 0xAA, 0x9F,
	0x3F, 0x28, 0x10, 0x1E, 0x8C, 0x08, 0x65, 0xC6,
	0xAB, 0x12, 0xFF, 0x4D, 0x80, 0x35, 0xA0, 0x17,
	0x38, 0x0E, 0x92, 0x84, 0x6D, 0xA3, 0x6D, 0xB9,
	0xED, 0xB2, 0xCD, 0xB5, 0x95, 0xB7, 0x2F, 0x36,
	0x9C, 0x16, 0xE9, 0xCE, 0xCE, 0xD4, 0x54, 0x5F,
	0x7F, 0x78, 0x20, 0x22, 0x98, 0x19, 0xAA, 0x8A,
	0xFF, 0x27, 0x00, 0x1A, 0x80, 0x0B, 0x20, 0x07,
	0x58, 0x02, 0xBA, 0x81, 0xB3, 0x20, 0x75, 0xD8,
	0x27, 0x1A, 0x9A, 0x8B, 0x2B, 0x27, 0x5F, 0x5A,
	0xB8, 0x3B, 0x32, 0x93, 0x55, 0xAD, 0xFF, 0x3D,
	0x80, 0x11, 0xA0, 0x0C, 0x78, 0x05, 0xE2, 0x83,
	0x09, 0xA1, 0xC6, 0xF8, 0x52, 0xC2, 0xBD, 0x91,
	0xB1, 0xAC, 0x74, 0x7D, 0xE7, 0x61, 0x8A, 0xA8,
	0x67, 0x3E, 0xAA, 0x90, 0x7F, 0x2C, 0x20, 0x1D,
	0xD8, 0x09, 0x9A, 0x86, 0xEB, 0x22, 0xCF, 0x59,
	0x94, 0x3A, 0xEF, 0x53, 0x0C, 0x3D, 0xC5, 0xD1,
	0x93, 0x1C, 0x6D, 0xC9, 0xED, 0x96, 0xCD, 0xAE,
	0xD5, 0xBC, 0x5F, 0x31, 0xF8, 0x14, 0x42, 0x8F,
	0x71, 0xA4, 0x24, 0x7B, 0x5B, 0x63, 0x7B, 0x69,
	0xE3, 0x6E, 0xC9, 0xEC, 0x56, 0xCD, 0xFE, 0xD5,
	0x80, 0x5F, 0x20, 0x38, 0x18, 0x12, 0x8A, 0x8D,
	0xA7, 0x25, 0xBA, 0x9B, 0x33, 0x2B, 0x55
};

static const struct dtm_supp_features supported_features = {
	.data_len_ext = true,
	.phy_2m = true,
	.stable_mod = false,
	.coded_phy = IS_ENABLED(CONFIG_HAS_HW_NRF_RADIO_BLE_CODED),
#if DIRECTION_FINDING_SUPPORTED
	.cte = true,
	.ant_switching = true,
	.aod_1us_tx = true,
	.aod_1us_rx = true,
	.aoa_1us_rx = true,
#else
	.cte = false,
	.ant_switching = false,
	.aod_1us_tx = false,
	.aod_1us_rx = false,
	.aoa_1us_rx = false,
#endif /* DIRECTION_FINDING_SUPPORTED */
};

#if DIRECTION_FINDING_SUPPORTED

static void radio_gpio_pattern_clear(void)
{
	nrf_radio_dfe_pattern_clear(NRF_RADIO);
}

static void antenna_radio_pin_config(void)
{
	const uint8_t *pin = dtm_hw_radio_antenna_pin_array_get();

	for (size_t i = 0; i < DTM_HW_MAX_DFE_GPIO; i++) {
		uint32_t pin_value = (pin[i] == DTM_HW_DFE_PSEL_NOT_SET) ?
				     DTM_HW_DFE_GPIO_PIN_DISCONNECT : pin[i];

		nrf_radio_dfe_pattern_pin_set(NRF_RADIO,
					      pin_value,
					      i);
	}
}

static void switch_pattern_set(void)
{
	uint8_t pdu_antenna = dtm_hw_radio_pdu_antenna_get();
	/* Set antenna for the PDU, guard period and for the reference period.
	 * The same antenna is used for guard and reference period as for the PDU.
	 */
	NRF_RADIO->SWITCHPATTERN = pdu_antenna;
	NRF_RADIO->SWITCHPATTERN = pdu_antenna;

	for (size_t i = 0; i <= dtm_inst.cte_info.antenna_pattern_len; i++) {
		NRF_RADIO->SWITCHPATTERN = dtm_inst.cte_info.antenna_pattern[i];
	}
}

static void radio_cte_reset(void)
{
	NRF_RADIO->DFEMODE &= ~RADIO_DFEMODE_DFEOPMODE_Msk;
	NRF_RADIO->DFEMODE |= ((RADIO_DFEMODE_DFEOPMODE_Disabled << RADIO_DFEMODE_DFEOPMODE_Pos)
			       & RADIO_DFEMODE_DFEOPMODE_Msk);

	NRF_RADIO->CTEINLINECONF &= ~RADIO_CTEINLINECONF_CTEINLINECTRLEN_Msk;
	NRF_RADIO->CTEINLINECONF |= ((RADIO_CTEINLINECONF_CTEINLINECTRLEN_Disabled <<
				      RADIO_CTEINLINECONF_CTEINLINECTRLEN_Pos)
				     & RADIO_CTEINLINECONF_CTEINLINECTRLEN_Msk);

	radio_gpio_pattern_clear();
}

static void radio_cte_prepare(bool rx)
{
	if ((rx && (dtm_inst.cte_info.mode ==  DTM_CTE_MODE_AOA)) ||
	    ((!rx) && (dtm_inst.cte_info.mode == DTM_CTE_MODE_AOD))) {
		antenna_radio_pin_config();
		switch_pattern_set();

		/* Set antenna switch spacing. */
		NRF_RADIO->DFECTRL1 &= ~RADIO_DFECTRL1_TSWITCHSPACING_Msk;
		NRF_RADIO->DFECTRL1 |= (dtm_inst.cte_info.slot <<
					RADIO_DFECTRL1_TSWITCHSPACING_Pos);
	}

	NRF_RADIO->DFEMODE = dtm_inst.cte_info.mode;
	NRF_RADIO->PCNF0 |= (8 << RADIO_PCNF0_S1LEN_Pos);

	if (rx) {
		/* Enable parsing CTEInfo from received packet. */
		NRF_RADIO->CTEINLINECONF |=
				RADIO_CTEINLINECONF_CTEINLINECTRLEN_Enabled;
		NRF_RADIO->CTEINLINECONF |=
			(RADIO_CTEINLINECONF_CTEINFOINS1_InS1 <<
			 RADIO_CTEINLINECONF_CTEINFOINS1_Pos);

		/* Set S0 Mask and Configuration to check if CP bit is set
		 * in received PDU.
		 */
		NRF_RADIO->CTEINLINECONF |=
				(0x20 << RADIO_CTEINLINECONF_S0CONF_Pos) |
				(0x20 << RADIO_CTEINLINECONF_S0MASK_Pos);

		NRF_RADIO->DFEPACKET.PTR = (uint32_t)dtm_inst.cte_info.data;
		NRF_RADIO->DFEPACKET.MAXCNT =
				(uint16_t)sizeof(dtm_inst.cte_info.data);
	} else {
		/* Disable parsing CTEInfo from received packet. */
		NRF_RADIO->CTEINLINECONF &=
				~RADIO_CTEINLINECONF_CTEINLINECTRLEN_Enabled;

		NRF_RADIO->DFECTRL1 &= ~RADIO_DFECTRL1_NUMBEROF8US_Msk;
		NRF_RADIO->DFECTRL1 |= dtm_inst.cte_info.time;
	}
}
#endif /* DIRECTION_FINDING_SUPPORTED */

#if NRF52_ERRATA_172_PRESENT
static void anomaly_timer_handler(nrf_timer_event_t event_type, void *context);
#endif /* NRF52_ERRATA_172_PRESENT */

static void dtm_timer_handler(nrf_timer_event_t event_type, void *context);
static void radio_handler(const void *context);

#if defined(CONFIG_CLOCK_CONTROL_NRF)
static int clock_init(void)
{
	int err;
	int res;
	struct onoff_manager *clk_mgr;
	struct onoff_client clk_cli;

	clk_mgr = z_nrf_clock_control_get_onoff(CLOCK_CONTROL_NRF_SUBSYS_HF);
	if (!clk_mgr) {
		printk("Unable to get the Clock manager\n");
		return -ENXIO;
	}

	sys_notify_init_spinwait(&clk_cli.notify);

	err = onoff_request(clk_mgr, &clk_cli);
	if (err < 0) {
		printk("Clock request failed: %d\n", err);
		return err;
	}

	do {
		err = sys_notify_fetch_result(&clk_cli.notify, &res);
		if (!err && res) {
			printk("Clock could not be started: %d\n", res);
			return res;
		}
	} while (err);

#if defined(NRF54L15_XXAA)
	/* MLTPAN-20 */
	nrf_clock_task_trigger(NRF_CLOCK, NRF_CLOCK_TASK_PLLSTART);
#endif /* defined(NRF54L15_XXAA) */

	return err;
}

#elif defined(CONFIG_CLOCK_CONTROL_NRF2)

int clock_init(void)
{
	int err;
	int res;
	const struct device *radio_clk_dev =
		DEVICE_DT_GET_OR_NULL(DT_CLOCKS_CTLR(DT_NODELABEL(radio)));
	struct onoff_client radio_cli;

	/** Keep radio domain powered all the time to reduce latency. */
	nrf_lrcconf_poweron_force_set(NRF_LRCCONF010, NRF_LRCCONF_POWER_DOMAIN_1, true);

	sys_notify_init_spinwait(&radio_cli.notify);

	err = nrf_clock_control_request(radio_clk_dev, NULL, &radio_cli);

	do {
		err = sys_notify_fetch_result(&radio_cli.notify, &res);
		if (!err && res) {
			printk("Clock could not be started: %d\n", res);
			return res;
		}
	} while (err == -EAGAIN);

#if defined(NRF54L15_XXAA)
	/* MLTPAN-20 */
	nrf_clock_task_trigger(NRF_CLOCK, NRF_CLOCK_TASK_PLLSTART);
#endif /* defined(NRF54L15_XXAA) */

	return 0;
}

#else
BUILD_ASSERT(false, "No Clock Control driver");
#endif /* defined(CONFIG_CLOCK_CONTROL_NRF2) */

static int timer_init(void)
{
	nrfx_err_t err;
	nrfx_timer_config_t timer_cfg = {
		.frequency = NRFX_MHZ_TO_HZ(1),
		.mode      = NRF_TIMER_MODE_TIMER,
		.bit_width = NRF_TIMER_BIT_WIDTH_16,
	};

	err = nrfx_timer_init(&dtm_inst.timer, &timer_cfg, dtm_timer_handler);
	if (err != NRFX_SUCCESS) {
		printk("nrfx_timer_init failed with: %d\n", err);
		return -EAGAIN;
	}

	IRQ_CONNECT(DEFAULT_TIMER_IRQ, CONFIG_DTM_TIMER_IRQ_PRIORITY,
		    DEFAULT_TIMER_IRQ_HANDLER, NULL, 0);

	return 0;
}

#if NRF52_ERRATA_172_PRESENT
static int anomaly_timer_init(void)
{
	nrfx_err_t err;
	nrfx_timer_config_t timer_cfg = {
		.frequency = NRFX_KHZ_TO_HZ(125),
		.mode      = NRF_TIMER_MODE_TIMER,
		.bit_width = NRF_TIMER_BIT_WIDTH_16,
	};

	err = nrfx_timer_init(&dtm_inst.anomaly_timer, &timer_cfg,
			      anomaly_timer_handler);
	if (err != NRFX_SUCCESS) {
		printk("nrfx_timer_init failed with: %d\n", err);
		return -EAGAIN;
	}

	IRQ_CONNECT(ANOMALY_172_TIMER_IRQ,
		    CONFIG_ANOMALY_172_TIMER_IRQ_PRIORITY,
		    ANOMALY_172_TIMER_IRQ_HANDLER,
		    NULL, 0);

	nrfx_timer_compare(&dtm_inst.anomaly_timer,
		NRF_TIMER_CC_CHANNEL0,
		nrfx_timer_ms_to_ticks(&dtm_inst.anomaly_timer,
				       BLOCKER_FIX_WAIT_DEFAULT),
		true);

	return 0;
}
#endif /* NRF52_ERRATA_172_PRESENT */

static int gppi_init(void)
{
	nrfx_err_t err;

	err = nrfx_gppi_channel_alloc(&dtm_inst.ppi_radio_start);
	if (err != NRFX_SUCCESS) {
		printk("nrfx_gppi_channel_alloc failed with: %d\n", err);
		return -EAGAIN;
	}

	return 0;
}

static nrf_radio_txpower_t dbm_to_nrf_radio_txpower(int8_t tx_power)
{

	/* The tx_power is in dBm units and is converted
	 * to the appropriate radio register enumerator.
	 */
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

#if defined(RADIO_TXPOWER_TXPOWER_Neg40dBm)
	case -40:
		return RADIO_TXPOWER_TXPOWER_Neg40dBm;
#endif /* RADIO_TXPOWER_TXPOWER_Neg40dBm */

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
#endif /* RADIO_TXPOWER_TXPOWER_Pos1dBm */

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
		__ASSERT_NO_MSG(0);
	}
}

#if CONFIG_DTM_POWER_CONTROL_AUTOMATIC
static int8_t dtm_radio_min_power_get(uint16_t frequency)
{
	return fem_tx_output_power_min_get(frequency);
}

static int8_t dtm_radio_max_power_get(uint16_t frequency)
{
	return fem_tx_output_power_max_get(frequency);
}

static int8_t dtm_radio_nearest_power_get(int8_t tx_power, uint16_t frequency)
{
	int8_t tx_power_floor = fem_tx_output_power_check(tx_power, frequency, false);
	int8_t tx_power_ceiling = fem_tx_output_power_check(tx_power, frequency, true);
	int8_t output_power;

	output_power = (abs(tx_power_floor - tx_power) > abs(tx_power_ceiling - tx_power)) ?
		       tx_power_ceiling : tx_power_floor;

	return output_power;
}

#else
static int8_t dtm_radio_min_power_get(uint16_t frequency)
{
	ARG_UNUSED(frequency);

	return dtm_hw_radio_min_power_get();
}

static int8_t dtm_radio_max_power_get(uint16_t frequency)
{
	ARG_UNUSED(frequency);

	return dtm_hw_radio_max_power_get();
}

static int8_t dtm_radio_nearest_power_get(int8_t tx_power, uint16_t frequency)
{
	int8_t output_power = INT8_MAX;
	const size_t size = dtm_hw_radio_power_array_size_get();
	const int8_t *power = dtm_hw_radio_power_array_get();

	ARG_UNUSED(frequency);

	for (size_t i = 1; i < size; i++) {
		if (((int8_t) power[i]) > tx_power) {
			int8_t diff = abs((int8_t) power[i] - tx_power);

			if (diff <  abs((int8_t) power[i - 1] - tx_power)) {
				output_power = power[i];
			} else {
				output_power = power[i - 1];
			}

			break;
		}
	}

	__ASSERT_NO_MSG(output_power != INT8_MAX);

	return output_power;
}
#endif /* CONFIG_DTM_POWER_CONTROL_AUTOMATIC */

static uint16_t radio_frequency_get(uint8_t channel)
{
	static const uint16_t base_frequency = 2402;

	__ASSERT_NO_MSG(channel <= PHYS_CH_MAX);

	/* Actual frequency (MHz): 2402 + 2N */
	return (channel << 1) + base_frequency;
}

static void radio_tx_power_set(uint8_t channel, int8_t tx_power)
{
	int8_t radio_power = tx_power;

#if CONFIG_FEM
	uint16_t frequency;

	if (IS_ENABLED(CONFIG_DTM_POWER_CONTROL_AUTOMATIC)) {
		frequency = radio_frequency_get(channel);

		/* Adjust output power to nearest possible value for the given frequency.
		 * Due to limitations of the DTM specification output power level set command check
		 * Tx output power level for channel 0. That is why output Tx power needs to be
		 * aligned for final transmission channel.
		 */
		tx_power = dtm_radio_nearest_power_get(tx_power, frequency);
		(void)fem_tx_output_power_prepare(tx_power, &radio_power, frequency);
	}
#else
	ARG_UNUSED(channel);
#endif /* CONFIG_FEM */

#ifdef NRF53_SERIES
	bool high_voltage_enable = false;

	if (radio_power > 0) {
		high_voltage_enable = true;
		radio_power -= RADIO_TXPOWER_TXPOWER_Pos3dBm;
	}

	nrf_vreqctrl_radio_high_voltage_set(NRF_VREQCTRL, high_voltage_enable);
#endif /* NRF53_SERIES */

	nrf_radio_txpower_set(NRF_RADIO, dbm_to_nrf_radio_txpower(radio_power));
}

static void radio_reset(void)
{
	if (nrfx_gppi_channel_check(dtm_inst.ppi_radio_start)) {
		nrfx_gppi_channels_disable(BIT(dtm_inst.ppi_radio_start));
	}

	nrf_radio_shorts_set(NRF_RADIO, 0);
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);

	nrf_radio_task_trigger(NRF_RADIO, NRF_RADIO_TASK_DISABLE);
	while (!nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_DISABLED)) {
		/* Do nothing */
	}
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);

	irq_disable(RADIO_IRQn);
	nrf_radio_int_disable(NRF_RADIO,
			NRF_RADIO_INT_READY_MASK |
			NRF_RADIO_INT_ADDRESS_MASK |
			NRF_RADIO_INT_END_MASK);

	dtm_inst.rx_pkt_count = 0;
}

static int radio_init(void)
{
	nrf_radio_packet_conf_t packet_conf;

	if ((!dtm_hw_radio_validate(dtm_inst.txpower, dtm_inst.radio_mode)) &&
	    (!IS_ENABLED(CONFIG_DTM_POWER_CONTROL_AUTOMATIC))) {
		printk("Incorrect settings for radio mode and TX power\n");
		return -EINVAL;
	}

	/* Turn off radio before configuring it */
	radio_reset();

	radio_tx_power_set(dtm_inst.phys_ch, dtm_inst.txpower);
	nrf_radio_mode_set(NRF_RADIO, dtm_inst.radio_mode);
	nrf_radio_fast_ramp_up_enable_set(NRF_RADIO, IS_ENABLED(CONFIG_DTM_FAST_RAMP_UP));

	/* Set the access address, address0/prefix0 used for both Rx and Tx
	 * address.
	 */
	nrf_radio_prefix0_set(NRF_RADIO, dtm_inst.address >> 24);
	nrf_radio_base0_set(NRF_RADIO, dtm_inst.address << 8);
	nrf_radio_rxaddresses_set(NRF_RADIO, RADIO_RXADDRESSES_ADDR0_Enabled);
	nrf_radio_txaddress_set(NRF_RADIO, 0x00);

	/* Configure CRC calculation. */
	nrf_radio_crcinit_set(NRF_RADIO, CRC_INIT);
	nrf_radio_crc_configure(NRF_RADIO, RADIO_CRCCNF_LEN_Three,
				NRF_RADIO_CRC_ADDR_SKIP, CRC_POLY);

	memset(&packet_conf, 0, sizeof(packet_conf));
	packet_conf.s0len = PACKET_HEADER_S0_LEN;
	packet_conf.s1len = PACKET_HEADER_S1_LEN;
	packet_conf.lflen = PACKET_HEADER_LF_LEN;
	packet_conf.plen = dtm_inst.packet_hdr_plen;
	packet_conf.whiteen = false;
	packet_conf.big_endian = false;
	packet_conf.balen = PACKET_BA_LEN;
	packet_conf.statlen = PACKET_STATIC_LEN;
	packet_conf.maxlen = DTM_PAYLOAD_MAX_SIZE;

	if (dtm_inst.radio_mode != NRF_RADIO_MODE_BLE_1MBIT &&
	    dtm_inst.radio_mode != NRF_RADIO_MODE_BLE_2MBIT) {
		/* Coded PHY (Long range) */
#if defined(RADIO_PCNF0_TERMLEN_Msk)
		packet_conf.termlen = 3;
#endif /* defined(RADIO_PCNF0_TERMLEN_Msk) */

#if defined(RADIO_PCNF0_CILEN_Msk)
		packet_conf.cilen = 2;
#endif /* defined(RADIO_PCNF0_CILEN_Msk) */
	}

	nrf_radio_packet_configure(NRF_RADIO, &packet_conf);

	return 0;
}

int dtm_init(dtm_iq_report_callback_t callback)
{
	int err;

	err = clock_init();
	if (err) {
		return err;
	}

#if defined(CONFIG_SOC_SERIES_NRF54HX)
	/* Apply HMPAN-102 workaround for nRF54H series */
	*(volatile uint32_t *)0x5302C7E4 =
				(((*((volatile uint32_t *)0x5302C7E4)) & 0xFF000FFF) | 0x0012C000);
#endif

	err = timer_init();
	if (err) {
		return err;
	}

#if NRF52_ERRATA_172_PRESENT
	/* Enable the timer used by nRF52840 anomaly 172 if running on an
	 * affected device.
	 */
	err = anomaly_timer_init();
	if (err) {
		return err;
	}
#endif /* NRF52_ERRATA_172_PRESENT */

	err = gppi_init();
	if (err) {
		return err;
	}

#if CONFIG_FEM
	err = fem_init(dtm_inst.timer.p_reg,
		       (BIT(NRF_TIMER_CC_CHANNEL1) | BIT(NRF_TIMER_CC_CHANNEL2)));
	if (err) {
		return err;
	}
#endif /* CONFIG_FEM */

#if CONFIG_DTM_POWER_CONTROL_AUTOMATIC
	/* When front-end module is used, set output power to the front-end module
	 * default output power.
	 */
	dtm_inst.txpower = fem_default_tx_output_power_get();
#endif /* CONFIG_DTM_POWER_CONTROL_AUTOMATIC */

	/** Connect radio interrupts. */
	IRQ_CONNECT(RADIO_IRQn, CONFIG_DTM_RADIO_IRQ_PRIORITY, radio_handler,
		    NULL, 0);
	irq_enable(RADIO_IRQn);


	err = radio_init();
	if (err) {
		return err;
	}

	dtm_inst.state = STATE_IDLE;
	dtm_inst.packet_len = 0;
	dtm_inst.cte_info.iq_rep_cb = callback;

	return 0;
}

#if DIRECTION_FINDING_SUPPORTED
static void report_iq(void)
{
	struct dtm_iq_data iq_data;

	iq_data.channel = dtm_inst.phys_ch;
	iq_data.rssi = -nrf_radio_rssi_sample_get(NRF_RADIO);

#if defined(RADIO_EVENTS_RSSIEND_EVENTS_RSSIEND_Msk)
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_RSSIEND);
#endif

	iq_data.rssi_ant = dtm_hw_radio_pdu_antenna_get();

	if (dtm_inst.cte_info.mode == DTM_CTE_MODE_AOD) {
		if (dtm_inst.cte_info.slot == DTM_CTE_SLOT_1US) {
			iq_data.type = DTM_CTE_TYPE_AOD_1US;
		} else if (dtm_inst.cte_info.slot == DTM_CTE_SLOT_2US) {
			iq_data.type = DTM_CTE_TYPE_AOD_2US;
		} else {
			/* Not possible - invalid value */
			__ASSERT_NO_MSG(false);
		}
	} else if (dtm_inst.cte_info.mode == DTM_CTE_MODE_AOA) {
		iq_data.type = DTM_CTE_TYPE_AOA;
	} else {
		/* Not possible - invalid value */
		__ASSERT_NO_MSG(false);
	}

	if (dtm_inst.cte_info.slot == DTM_CTE_SLOT_1US) {
		iq_data.slot = DTM_CTE_SLOT_DURATION_1US;
	} else if (dtm_inst.cte_info.slot == DTM_CTE_SLOT_2US) {
		iq_data.slot = DTM_CTE_SLOT_DURATION_2US;
	} else {
		/* Not possible - invalid value */
		__ASSERT_NO_MSG(false);
	}

	/* There is no requirement to report iq samples with invalid CRC */
	iq_data.status = DTM_PACKET_STATUS_CRC_OK;
	iq_data.sample_cnt = nrf_radio_dfe_amount_get(NRF_RADIO);
	iq_data.samples = (struct dtm_iq_sample *)dtm_inst.cte_info.data;

	dtm_inst.cte_info.iq_rep_cb(&iq_data);
}
#endif /* DIRECTION_FINDING_SUPPORTED */

/* Function for verifying that a received PDU has the expected structure and
 * content.
 */
static bool check_pdu(const struct dtm_pdu *pdu)
{
	/* Repeating octet value in payload */
	uint8_t pattern;
	/* PDU packet type is a 4-bit field in HCI, but 2 bits in BLE DTM */
	uint32_t pdu_packet_type;
	uint32_t length = 0;
	uint8_t header_len;
	const uint8_t *payload;

	pdu_packet_type = (uint32_t)
			  (pdu->content[DTM_HEADER_OFFSET] & 0x0F);
	length = pdu->content[DTM_LENGTH_OFFSET];

	header_len = (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) ?
		     DTM_HEADER_WITH_CTE_SIZE : DTM_HEADER_SIZE;

	payload = pdu->content + header_len;

	/* Check that the length is valid. */
	if (length > DTM_PAYLOAD_MAX_SIZE) {
		return false;
	}

	/* If the 1Mbit or 2Mbit radio mode is active, check that one of the
	 * three valid uncoded DTM packet types are selected.
	 */
	if ((dtm_inst.radio_mode == NRF_RADIO_MODE_BLE_1MBIT ||
	     dtm_inst.radio_mode == NRF_RADIO_MODE_BLE_2MBIT) &&
	    (pdu_packet_type > (uint32_t) DTM_PDU_TYPE_0X55)) {
		return false;
	}

	/* If a long range radio mode is active, check that one of the four
	 * valid coded DTM packet types are selected.
	 */
	if (dtm_hw_radio_lr_check(dtm_inst.radio_mode) &&
	    (pdu_packet_type > (uint32_t) DTM_PDU_TYPE_0XFF)) {
		return false;
	}

	switch (pdu_packet_type) {
	case DTM_PDU_TYPE_PRBS9:
		return (memcmp(payload, dtm_prbs9_content, length) == 0);

	case DTM_PDU_TYPE_0X0F:
		pattern = RFPHY_TEST_0X0F_REF_PATTERN;
		break;

	case DTM_PDU_TYPE_0X55:
		pattern = RFPHY_TEST_0X55_REF_PATTERN;
		break;

	case DTM_PDU_TYPE_PRBS15:
		return (memcmp(payload, dtm_prbs15_content, length) == 0);

	case DTM_PDU_TYPE_0XFF:
		pattern = RFPHY_TEST_0XFF_REF_PATTERN;
		break;

	case DTM_PDU_TYPE_0X00:
		pattern = RFPHY_TEST_0X00_REF_PATTERN;
		break;

	case DTM_PDU_TYPE_0XF0:
		pattern = RFPHY_TEST_0XF0_REF_PATTERN;
		break;

	case DTM_PDU_TYPE_0XAA:
		pattern = RFPHY_TEST_0XAA_REF_PATTERN;
		break;

	default:
		/* No valid packet type set. */
		return false;
	}

	for (uint8_t k = 0; k < length; k++) {
		/* Check repeated pattern filling the PDU payload */
		if (pdu->content[k + 2] != pattern) {
			return false;
		}
	}

#if DIRECTION_FINDING_SUPPORTED
	/* Check CTEInfo and IQ sample cnt */
	if (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) {
		uint8_t cte_info;
		uint8_t cte_sample_cnt;
		uint8_t expected_sample_cnt;

		cte_info = pdu->content[DTM_HEADER_CTEINFO_OFFSET];

		expected_sample_cnt =
			DTM_CTE_REF_SAMPLE_CNT +
			((dtm_inst.cte_info.time * 8)) /
			((dtm_inst.cte_info.slot == DTM_CTE_SLOT_1US) ? 2 : 4);
		cte_sample_cnt = NRF_RADIO->DFEPACKET.AMOUNT;

		if (dtm_inst.cte_info.iq_rep_cb) {
			report_iq();
		}

		memset(dtm_inst.cte_info.data, 0,
		       sizeof(dtm_inst.cte_info.data));

		if ((cte_info != dtm_inst.cte_info.mode) ||
		    (expected_sample_cnt != cte_sample_cnt)) {
			return false;
		}
	}
#endif /* DIRECTION_FINDING_SUPPORTED */

	return true;
}

#if NRF52_ERRATA_172_PRESENT
/* Radio configuration used as a workaround for nRF52840 anomaly 172 */
static void anomaly_172_radio_operation(void)
{
	*(volatile uint32_t *) 0x40001040 = 1;
	*(volatile uint32_t *) 0x40001038 = 1;
}

/* Function to gather RSSI data and set strict mode accordingly.
 * Used as part of the workaround for nRF52840 anomaly 172
 */
static uint8_t anomaly_172_rssi_check(void)
{
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_RSSIEND);

	nrf_radio_task_trigger(NRF_RADIO, NRF_RADIO_TASK_RSSISTART);
	while (!nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_RSSIEND)) {
	}

	return nrf_radio_rssi_sample_get(NRF_RADIO);
}

/* Strict mode setting will be used only by devices affected by nRF52840
 * anomaly 172
 */
static void anomaly_172_strict_mode_set(bool enable)
{
	uint8_t dbcCorrTh;
	uint8_t dsssMinPeakCount;

	if (enable == true) {
		dbcCorrTh = 0x7d;
		dsssMinPeakCount = 6;

		*(volatile uint32_t *) 0x4000173c =
			((*((volatile uint32_t *) 0x4000173c)) & 0x7FFFFF00) |
			0x80000000 |
			(((uint32_t)(dbcCorrTh)) << 0);
		*(volatile uint32_t *) 0x4000177c =
			((*((volatile uint32_t *) 0x4000177c)) & 0x7FFFFF8F) |
			0x80000000 |
			((((uint32_t)dsssMinPeakCount) & 0x00000007) << 4);
	} else {
		*(volatile uint32_t *) 0x4000173c = 0x40003034;
		/* Unset override of dsssMinPeakCount */
		*(volatile uint32_t *) 0x4000177c =
			((*((volatile uint32_t *) 0x4000177c)) & 0x7FFFFFFF);
	}

	dtm_inst.strict_mode = enable;
}

static void errata_172_handle(bool enable)
{
	if (!nrf52_errata_172()) {
		return;
	}

	if (enable) {
		if ((*(volatile uint32_t *)0x40001788) == 0) {
			dtm_inst.anomaly_172_wa_enabled = true;
		}
	} else {
		anomaly_172_strict_mode_set(false);
		nrfx_timer_disable(&dtm_inst.anomaly_timer);
		dtm_inst.anomaly_172_wa_enabled = false;
	}
}
#else
static void errata_172_handle(bool enable)
{
	ARG_UNUSED(enable);
}
#endif /* NRF52_ERRATA_172_PRESENT */

static void errata_117_handle(bool enable)
{
	if (!nrf52_errata_117()) {
		return;
	}

	if (enable) {
		*((volatile uint32_t *)0x41008588) = *((volatile uint32_t *)0x01FF0084);
	} else {
		*((volatile uint32_t *)0x41008588) = *((volatile uint32_t *)0x01FF0080);
	}
}

static void errata_191_handle(bool enable)
{
	if (!nrf52_errata_191()) {
		return;
	}

	if (enable) {
		*(volatile uint32_t *)0x40001740 =
			((*((volatile uint32_t *)0x40001740)) & 0x7FFF00FF) |
			0x80000000 | (((uint32_t)(196)) << 8);
	} else {
		*(volatile uint32_t *)0x40001740 =
			((*((volatile uint32_t *)0x40001740)) & 0x7FFFFFFF);
	}
}

static void endpoints_clear(void)
{
	if (atomic_test_and_clear_bit(&dtm_inst.endpoint_state, ENDPOINT_FORK_EGU_TIMER)) {
		nrfx_gppi_fork_endpoint_clear(dtm_inst.ppi_radio_start,
			nrf_timer_task_address_get(dtm_inst.timer.p_reg, NRF_TIMER_TASK_START));
	}
	if (atomic_test_and_clear_bit(&dtm_inst.endpoint_state, ENDPOINT_EGU_RADIO_TX)) {
		nrfx_gppi_channel_endpoints_clear(
			dtm_inst.ppi_radio_start,
			nrf_egu_event_address_get(DTM_EGU, DTM_EGU_EVENT),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	}
	if (atomic_test_and_clear_bit(&dtm_inst.endpoint_state, ENDPOINT_EGU_RADIO_RX)) {
		nrfx_gppi_channel_endpoints_clear(
			dtm_inst.ppi_radio_start,
			nrf_egu_event_address_get(DTM_EGU, DTM_EGU_EVENT),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_RXEN));
	}
	if (atomic_test_and_clear_bit(&dtm_inst.endpoint_state, ENDPOINT_TIMER_RADIO_TX)) {
		nrfx_gppi_channel_endpoints_clear(
			dtm_inst.ppi_radio_start,
			nrf_timer_event_address_get(dtm_inst.timer.p_reg, NRF_TIMER_EVENT_COMPARE0),
			nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	}
}

static void radio_ppi_clear(void)
{
	if (nrfx_gppi_channel_check(dtm_inst.ppi_radio_start)) {
		nrfx_gppi_channels_disable(BIT(dtm_inst.ppi_radio_start));
	}

	nrf_egu_event_clear(DTM_EGU, DTM_EGU_EVENT);

	/* Break connection from timer to radio to stop transmit loop */
	endpoints_clear();
}

static void radio_ppi_configure(bool rx, uint32_t timer_short_mask)
{
	nrfx_gppi_channel_endpoints_setup(
		dtm_inst.ppi_radio_start,
		nrf_egu_event_address_get(DTM_EGU, DTM_EGU_EVENT),
		nrf_radio_task_address_get(NRF_RADIO,
					   rx ? NRF_RADIO_TASK_RXEN : NRF_RADIO_TASK_TXEN));
	atomic_set_bit(&dtm_inst.endpoint_state,
		       (rx ? ENDPOINT_EGU_RADIO_RX : ENDPOINT_EGU_RADIO_TX));

	nrfx_gppi_fork_endpoint_setup(dtm_inst.ppi_radio_start,
		nrf_timer_task_address_get(dtm_inst.timer.p_reg, NRF_TIMER_TASK_START));
	atomic_set_bit(&dtm_inst.endpoint_state, ENDPOINT_FORK_EGU_TIMER);

	nrfx_gppi_channels_enable(BIT(dtm_inst.ppi_radio_start));

	if (timer_short_mask) {
		nrf_timer_shorts_set(dtm_inst.timer.p_reg, timer_short_mask);
	}
}

static void radio_tx_ppi_reconfigure(void)
{
	if (nrfx_gppi_channel_check(dtm_inst.ppi_radio_start)) {
		nrfx_gppi_channels_disable(BIT(dtm_inst.ppi_radio_start));
	}

	endpoints_clear();

	nrfx_gppi_channel_endpoints_setup(
		dtm_inst.ppi_radio_start,
		nrf_timer_event_address_get(dtm_inst.timer.p_reg, NRF_TIMER_EVENT_COMPARE0),
		nrf_radio_task_address_get(NRF_RADIO, NRF_RADIO_TASK_TXEN));
	atomic_set_bit(&dtm_inst.endpoint_state, ENDPOINT_TIMER_RADIO_TX);
	nrfx_gppi_channels_enable(BIT(dtm_inst.ppi_radio_start));
}

static void dtm_test_done(void)
{
	nrfx_timer_disable(&dtm_inst.timer);

	radio_ppi_clear();

	/* Disable all timer shorts and interrupts. */
	nrf_timer_shorts_set(dtm_inst.timer.p_reg, 0);
	nrf_timer_int_disable(dtm_inst.timer.p_reg, ~((uint32_t)0));

	nrfx_timer_clear(&dtm_inst.timer);

#if NRF52_ERRATA_172_PRESENT
	nrfx_timer_disable(&dtm_inst.anomaly_timer);
#endif /* NRF52_ERRATA_172_PRESENT */

	radio_reset();

#if CONFIG_FEM
	fem_txrx_configuration_clear();
	fem_txrx_stop();
	(void)fem_power_down();
#endif /* CONFIG_FEM */

	dtm_inst.state = STATE_IDLE;
}

static void radio_start(bool rx, bool force_egu)
{
	if (IS_ENABLED(CONFIG_FEM) || force_egu) {
		nrf_egu_event_clear(DTM_EGU, DTM_EGU_EVENT);
		nrf_egu_task_trigger(DTM_EGU, DTM_EGU_TASK);
	} else {
		/* Shorts will start radio in RX mode when it is ready */
		nrf_radio_task_trigger(NRF_RADIO, rx ? NRF_RADIO_TASK_RXEN : NRF_RADIO_TASK_TXEN);
	}
}

static void radio_prepare(bool rx)
{
#if DIRECTION_FINDING_SUPPORTED
	if (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) {
		radio_cte_prepare(rx);
	} else {
		radio_cte_reset();
	}
#endif /* DIRECTION_FINDING_SUPPORTED */

	/* Actual frequency (MHz): 2402 + 2N */
	nrf_radio_frequency_set(NRF_RADIO, radio_frequency_get(dtm_inst.phys_ch));

	/* Setting packet pointer will start the radio */
	nrf_radio_packetptr_set(NRF_RADIO, dtm_inst.current_pdu);
	nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_READY);

	/* Set shortcuts:
	 * between READY event and START task and
	 * between END event and DISABLE task
	 */
#if DIRECTION_FINDING_SUPPORTED
	nrf_radio_shorts_set(NRF_RADIO,
		NRF_RADIO_SHORT_READY_START_MASK |
		(dtm_inst.cte_info.iq_rep_cb ?
		 NRF_RADIO_SHORT_ADDRESS_RSSISTART_MASK : 0) |
		(dtm_inst.cte_info.mode == DTM_CTE_MODE_OFF ?
		 DTM_RADIO_SHORT_END_DISABLE_MASK :
		 NRF_RADIO_SHORT_PHYEND_DISABLE_MASK));
#else
	nrf_radio_shorts_set(NRF_RADIO,
			     DTM_RADIO_SHORT_READY_START_MASK |
			     DTM_RADIO_SHORT_END_DISABLE_MASK);
#endif /* DIRECTION_FINDING_SUPPORTED */



#if CONFIG_FEM
	if (dtm_inst.fem.vendor_ramp_up_time == 0) {
		dtm_inst.fem.ramp_up_time =
			fem_default_ramp_up_time_get(rx, dtm_inst.radio_mode);
	} else {
		dtm_inst.fem.ramp_up_time =
				dtm_inst.fem.vendor_ramp_up_time;
	}
#endif /* CONFIG_FEM */

	NVIC_ClearPendingIRQ(RADIO_IRQn);
	irq_enable(RADIO_IRQn);
	nrf_radio_int_enable(NRF_RADIO,
			NRF_RADIO_INT_READY_MASK |
			NRF_RADIO_INT_ADDRESS_MASK |
#if defined(RADIO_EVENTS_RSSIEND_EVENTS_RSSIEND_Msk)
			NRF_RADIO_INT_RSSIEND_MASK |
#endif
			NRF_RADIO_INT_END_MASK);

	if (rx) {
#if NRF52_ERRATA_172_PRESENT
		/* Enable strict mode for anomaly 172 */
		if (dtm_inst.anomaly_172_wa_enabled) {
			anomaly_172_strict_mode_set(true);
		}
#endif /* NRF52_ERRATA_172_PRESENT */

		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_END);

#if CONFIG_FEM
		radio_ppi_configure(rx,
			(NRF_TIMER_SHORT_COMPARE1_STOP_MASK | NRF_TIMER_SHORT_COMPARE1_CLEAR_MASK));

		(void)fem_power_up();
		(void)fem_rx_configure(dtm_inst.fem.ramp_up_time);
#endif /* CONFIG_FEM */

		radio_start(rx, false);
	} else { /* tx */
		radio_tx_power_set(dtm_inst.phys_ch, dtm_inst.txpower);

#if NRF52_ERRATA_172_PRESENT
		/* Stop the timer used by anomaly 172 */
		if (dtm_inst.anomaly_172_wa_enabled) {
			nrfx_timer_disable(&dtm_inst.anomaly_timer);
			nrfx_timer_clear(&dtm_inst.anomaly_timer);

			nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
					      NRF_TIMER_EVENT_COMPARE0);
			nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
					      NRF_TIMER_EVENT_COMPARE1);
		}
#endif /* NRF52_ERRATA_172_PRESENT */
	}
}

#if !CONFIG_DTM_POWER_CONTROL_AUTOMATIC
static bool dtm_set_txpower(uint32_t new_tx_power)
{
	/* radio->TXPOWER register is 32 bits, low octet a tx power value,
	 * upper 24 bits zeroed.
	 */
	int8_t new_power8 = (int8_t)(new_tx_power & 0xFF);

	/* The two most significant bits are not sent in the 6 bit field of
	 * the DTM command. These two bits are 1's if and only if the tx_power
	 * is a negative number. All valid negative values have a non zero bit
	 * in among the two most significant of the 6-bit value. By checking
	 * these bits, the two most significant bits can be determined.
	 */
	new_power8 = (new_power8 & 0x30) != 0 ?
		     (new_power8 | 0xC0) : new_power8;

	if (dtm_inst.state > STATE_IDLE) {
		/* Radio must be idle to change the TX power */
		return false;
	}

	if (!dtm_hw_radio_validate(new_power8, dtm_inst.radio_mode)) {
		return false;
	}

	dtm_inst.txpower = new_power8;

	return true;
}
#endif /* !CONFIG_DTM_POWER_CONTROL_AUTOMATIC */

static int dtm_vendor_specific_pkt(uint32_t vendor_cmd, uint32_t vendor_option)
{
	switch (vendor_cmd) {
	/* nRFgo Studio uses CARRIER_TEST_STUDIO to indicate a continuous
	 * carrier without a modulated signal.
	 */
	case CARRIER_TEST:
	case CARRIER_TEST_STUDIO:
		/* Not a packet type, but used to indicate that a continuous
		 * carrier signal should be transmitted by the radio.
		 */
		radio_prepare(TX_MODE);
		nrf_radio_fast_ramp_up_enable_set(NRF_RADIO, IS_ENABLED(CONFIG_DTM_FAST_RAMP_UP));

		/* Shortcut between READY event and START task */
		nrf_radio_shorts_set(NRF_RADIO,
				     NRF_RADIO_SHORT_READY_START_MASK);

#if CONFIG_FEM
		if ((dtm_inst.fem.tx_power_control != FEM_USE_DEFAULT_TX_POWER_CONTROL) &&
		    (!IS_ENABLED(CONFIG_DTM_POWER_CONTROL_AUTOMATIC))) {
			if (fem_tx_power_control_set(dtm_inst.fem.tx_power_control) != 0) {
				return -EINVAL;
			}
		}

		radio_ppi_configure(false,
			(NRF_TIMER_SHORT_COMPARE1_STOP_MASK | NRF_TIMER_SHORT_COMPARE1_CLEAR_MASK));
		(void)fem_power_up();
		(void)fem_tx_configure(dtm_inst.fem.ramp_up_time);
#endif /* CONFIG_FEM */

		radio_start(false, false);
		dtm_inst.state = STATE_CARRIER_TEST;
		break;

#if !CONFIG_DTM_POWER_CONTROL_AUTOMATIC
	case SET_TX_POWER:
		if (!dtm_set_txpower(vendor_option)) {
			return -EINVAL;
		}
		break;
#endif /* !CONFIG_DTM_POWER_CONTROL_AUTOMATIC */

#if CONFIG_FEM
	case FEM_ANTENNA_SELECT:
		if (fem_antenna_select(vendor_option) != 0) {
			return -EINVAL;
		}

		break;

#if !CONFIG_DTM_POWER_CONTROL_AUTOMATIC
	case FEM_TX_POWER_CONTROL_SET:
		dtm_inst.fem.tx_power_control = vendor_option;

		break;
#endif /* !CONFIG_DTM_POWER_CONTROL_AUTOMATIC */

	case FEM_RAMP_UP_SET:
		dtm_inst.fem.vendor_ramp_up_time = vendor_option;

		break;

	case FEM_DEFAULT_PARAMS_SET:
		dtm_inst.fem.tx_power_control = FEM_USE_DEFAULT_TX_POWER_CONTROL;
		dtm_inst.fem.vendor_ramp_up_time = 0;

		if (fem_antenna_select(FEM_ANTENNA_1) != 0) {
			return -EINVAL;
		}

		break;
#endif /* CONFIG_FEM */
	default:
		return -EINVAL;
	}

	return 0;
}

static uint32_t dtm_packet_interval_calculate(uint32_t test_payload_length,
					      nrf_radio_mode_t mode)
{
	/* [us] NOTE: bits are us at 1Mbit */
	uint32_t test_packet_length = 0;
	/* us */
	uint32_t packet_interval = 0;
	/* bits */
	uint32_t overhead_bits = 0;

	/* Packet overhead
	 * see Bluetooth Core Specification [Vol 6, Part F]
	 * Section 4.1 LE TEST PACKET FORMAT
	 */
	if (mode == NRF_RADIO_MODE_BLE_2MBIT) {
		/* 16 preamble
		 * 32 sync word
		 *  8 PDU header, actually packetHeaderS0len * 8
		 *  8 PDU length, actually packetHeaderLFlen
		 * 24 CRC
		 */
		overhead_bits = 88; /* 11 bytes */
	} else if (mode == NRF_RADIO_MODE_NRF_1MBIT) {
		/*  8 preamble
		 * 32 sync word
		 *  8 PDU header, actually packetHeaderS0len * 8
		 *  8 PDU length, actually packetHeaderLFlen
		 * 24 CRC
		 */
		overhead_bits = 80; /* 10 bytes */
#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	} else if (mode == NRF_RADIO_MODE_BLE_LR125KBIT) {
		/* 80     preamble
		 * 32 * 8 sync word coding=8
		 *  2 * 8 Coding indicator, coding=8
		 *  3 * 8 TERM1 coding=8
		 *  8 * 8 PDU header, actually packetHeaderS0len * 8 coding=8
		 *  8 * 8 PDU length, actually packetHeaderLFlen coding=8
		 * 24 * 8 CRC coding=8
		 *  3 * 8 TERM2 coding=8
		 */
		overhead_bits = 720; /* 90 bytes */
	} else if (mode == NRF_RADIO_MODE_BLE_LR500KBIT) {
		/* 80     preamble
		 * 32 * 8 sync word coding=8
		 *  2 * 8 Coding indicator, coding=8
		 *  3 * 8 TERM 1 coding=8
		 *  8 * 2 PDU header, actually packetHeaderS0len * 8 coding=2
		 *  8 * 2 PDU length, actually packetHeaderLFlen coding=2
		 * 24 * 2 CRC coding=2
		 *  3 * 2 TERM2 coding=2
		 * NOTE: this makes us clock out 46 bits for CI + TERM1 + TERM2
		 *       assumption the radio will handle this
		 */
		overhead_bits = 462; /* 57.75 bytes */
#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */
	}

	/* Add PDU payload test_payload length */
	test_packet_length = (test_payload_length * 8); /* in bits */

	/* Account for the encoding of PDU */
#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	if (mode == NRF_RADIO_MODE_BLE_LR125KBIT) {
		test_packet_length *= 8; /* 1 to 8 encoding */
	}

	if (mode == NRF_RADIO_MODE_BLE_LR500KBIT) {
		test_packet_length *= 2; /* 1 to 2 encoding */
	}
#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */

	/* Add overhead calculated above */
	test_packet_length += overhead_bits;
	/* remember this bits are us in 1Mbit */
	if (mode == NRF_RADIO_MODE_BLE_2MBIT) {
		test_packet_length /= 2; /* double speed */
	}

	if (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) {
		/* Add 8 - bit S1 field with CTEInfo. */
		((test_packet_length += mode) == RADIO_MODE_MODE_Ble_1Mbit) ?
						 8 : 4;

		/* Add CTE length in us to test packet length. */
		test_packet_length +=
				dtm_inst.cte_info.time * NRF_CTE_TIME_IN_US;
	}

	/* Packet_interval = ceil((test_packet_length + 249) / 625) * 625
	 * NOTE: To avoid floating point an equivalent calculation is used.
	 */
	uint32_t i = 0;
	uint32_t timeout = 0;

	do {
		i++;
		timeout = i * 625;
	} while (test_packet_length + 249 > timeout);

	packet_interval = i * 625;

	return packet_interval;
}

void dtm_setup_prepare(void)
{
	dtm_test_done();
}

int dtm_setup_reset(void)
{
	/* Reset the packet length upper bits. */
	dtm_inst.packet_len = 0;

	/* Reset the selected PHY to 1Mbit */
	dtm_inst.radio_mode = NRF_RADIO_MODE_BLE_1MBIT;
	dtm_inst.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_8BIT;

#if DIRECTION_FINDING_SUPPORTED
	memset(&dtm_inst.cte_info, 0, sizeof(dtm_inst.cte_info));
#endif /* DIRECTION_FINDING_SUPPORTED */

	errata_191_handle(false);
	errata_172_handle(false);
	errata_117_handle(false);

	return radio_init();
}

int dtm_setup_set_phy(enum dtm_phy phy)
{
	switch (phy) {
	case DTM_PHY_1M:
		dtm_inst.radio_mode = NRF_RADIO_MODE_BLE_1MBIT;
		dtm_inst.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_8BIT;

		errata_191_handle(false);
		errata_172_handle(false);
		errata_117_handle(false);
		break;

	case DTM_PHY_2M:
		dtm_inst.radio_mode = NRF_RADIO_MODE_BLE_2MBIT;
		dtm_inst.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;

		errata_191_handle(false);
		errata_172_handle(false);
		errata_117_handle(true);
		break;

#if CONFIG_HAS_HW_NRF_RADIO_BLE_CODED
	case DTM_PHY_CODED_S8:
		dtm_inst.radio_mode = NRF_RADIO_MODE_BLE_LR125KBIT;
		dtm_inst.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_LONG_RANGE;

		errata_191_handle(true);
		errata_172_handle(true);
		errata_117_handle(false);
		break;

	case DTM_PHY_CODED_S2:
		dtm_inst.radio_mode = NRF_RADIO_MODE_BLE_LR500KBIT;
		dtm_inst.packet_hdr_plen = NRF_RADIO_PREAMBLE_LENGTH_LONG_RANGE;

		errata_191_handle(true);
		errata_172_handle(true);
		errata_117_handle(false);
		break;
#else
	case DTM_PHY_CODED_S8:
	case DTM_PHY_CODED_S2:
		return -ENOTSUP;
#endif /* CONFIG_HAS_HW_NRF_RADIO_BLE_CODED */

	default:
		return -EINVAL;
	}

	return radio_init();
}

int dtm_setup_set_modulation(enum dtm_modulation modulation)
{
	/* Only standard modulation is supported. */
	if (modulation != DTM_MODULATION_STANDARD) {
		return -ENOTSUP;
	}

	return 0;
}

struct dtm_supp_features dtm_setup_read_features(void)
{
	return supported_features;
}

int dtm_setup_read_max_supported_value(enum dtm_max_supported parameter, uint16_t *max_val)
{
	if (!max_val) {
		return -EINVAL;
	}

	switch (parameter) {
	case DTM_MAX_SUPPORTED_TX_OCTETS:
		*max_val = NRF_MAX_PAYLOAD_OCTETS;
		break;

	case DTM_MAX_SUPPORTED_TX_TIME:
		*max_val = NRF_MAX_RX_TX_TIME;
		break;

	case DTM_MAX_SUPPORTED_RX_OCTETS:
		*max_val = NRF_MAX_PAYLOAD_OCTETS;
		break;

	case DTM_MAX_SUPPORTED_RX_TIME:
		*max_val = NRF_MAX_RX_TX_TIME;
		break;

#if DIRECTION_FINDING_SUPPORTED
	case DTM_MAX_SUPPORTED_CTE_LENGTH:
		*max_val = NRF_CTE_MAX_LENGTH;
		break;
#else
	case DTM_MAX_SUPPORTED_CTE_LENGTH:
		return -ENOTSUP;
#endif /* DIRECTION_FINDING_SUPPORTED */

	default:
		return -EINVAL;
	}

	return 0;
}

#if DIRECTION_FINDING_SUPPORTED
int dtm_setup_set_cte_mode(enum dtm_cte_type type, uint8_t time)
{
	uint8_t cte_info = time & CTEINFO_TIME_MASK;

	if (type == DTM_CTE_TYPE_NONE) {
		dtm_inst.cte_info.mode = DTM_CTE_MODE_OFF;
		return 0;
	}

	if ((time < CTE_LENGTH_MIN) ||
	    (time > CTE_LENGTH_MAX)) {
		return -EINVAL;
	}

	dtm_inst.cte_info.time = time;

	switch (type) {
	case DTM_CTE_TYPE_AOA:
		dtm_inst.cte_info.mode = DTM_CTE_MODE_AOA;
		break;

	case DTM_CTE_TYPE_AOD_1US:
		dtm_inst.cte_info.mode = DTM_CTE_MODE_AOD;
		dtm_inst.cte_info.slot = DTM_CTE_SLOT_1US;
		break;

	case DTM_CTE_TYPE_AOD_2US:
		dtm_inst.cte_info.mode = DTM_CTE_MODE_AOD;
		dtm_inst.cte_info.slot = DTM_CTE_SLOT_2US;
		break;

	default:
		return -EINVAL;
	}

	cte_info |= ((dtm_inst.cte_info.mode & CTEINFO_TYPE_MASK) << CTEINFO_TYPE_POS);
	dtm_inst.cte_info.info = cte_info;

	return 0;
}

int dtm_setup_set_cte_slot(enum dtm_cte_slot_duration slot)
{
	switch (slot) {
	case DTM_CTE_SLOT_DURATION_1US:
		dtm_inst.cte_info.slot = DTM_CTE_SLOT_1US;
		break;

	case DTM_CTE_SLOT_DURATION_2US:
		dtm_inst.cte_info.slot = DTM_CTE_SLOT_2US;
		break;

	default:
		return -EINVAL;
	}

	return 0;
}

int dtm_setup_set_antenna_params(uint8_t count, uint8_t *pattern, uint8_t pattern_len)
{
	if (count > dtm_hw_radio_antenna_number_get()) {
		return -ENOTSUP;
	}

	if (!pattern) {
		return -EINVAL;
	}

	if (!pattern_len) {
		return -EINVAL;
	}

	dtm_inst.cte_info.antenna_number = count;
	dtm_inst.cte_info.antenna_pattern = pattern;
	dtm_inst.cte_info.antenna_pattern_len = pattern_len;

	return 0;
}

#else
int dtm_setup_set_cte_mode(enum dtm_cte_type type, uint8_t time)
{
	ARG_UNUSED(time);

	if (type != DTM_CTE_TYPE_NONE) {
		return -ENOTSUP;
	}

	return 0;
}

int dtm_setup_set_cte_slot(enum dtm_cte_slot_duration slot)
{
	ARG_UNUSED(slot);

	return -ENOTSUP;
}

int dtm_setup_set_antenna_params(uint8_t count, uint8_t *pattern, uint8_t pattern_len)
{
	ARG_UNUSED(count);
	ARG_UNUSED(pattern);
	ARG_UNUSED(pattern_len);

	return -ENOTSUP;
}
#endif /* DIRECTION_FINDING_SUPPORTED */

struct dtm_tx_power dtm_setup_set_transmit_power(enum dtm_tx_power_request power, int8_t val,
						 uint8_t channel)
{
	uint16_t frequency = radio_frequency_get(channel);
	const int8_t tx_power_min = dtm_radio_min_power_get(frequency);
	const int8_t tx_power_max = dtm_radio_max_power_get(frequency);
	struct dtm_tx_power tmp = {
		.power = 0,
		.min = false,
		.max = false,
	};

	switch (power) {
	case DTM_TX_POWER_REQUEST_MIN:
		dtm_inst.txpower = tx_power_min;
		break;

	case DTM_TX_POWER_REQUEST_MAX:
		dtm_inst.txpower = tx_power_max;
		break;

	case DTM_TX_POWER_REQUEST_VAL:
		if (val <= tx_power_min) {
			dtm_inst.txpower = tx_power_min;
		} else if (val >= tx_power_max) {
			dtm_inst.txpower = tx_power_max;
		} else {
			dtm_inst.txpower = dtm_radio_nearest_power_get(val, frequency);
		}

		break;

	default:
		return tmp;
	}

	if (dtm_inst.txpower == tx_power_min) {
		tmp.min = true;
	} else if (dtm_inst.txpower == tx_power_max) {
		tmp.max = true;
	}

	tmp.power = dtm_inst.txpower;

	return tmp;
}

int dtm_test_receive(uint8_t channel)
{
	if (channel > PHYS_CH_MAX) {
		return -EINVAL;
	}

	dtm_inst.current_pdu = dtm_inst.pdu;
	dtm_inst.phys_ch = channel;
	dtm_inst.rx_pkt_count = 0;

	/* Zero fill all pdu fields to avoid stray data from earlier
	 * test run.
	 */
	memset(&dtm_inst.pdu, 0, sizeof(dtm_inst.pdu));

	/* Reinitialize "everything"; RF interrupts OFF */
	radio_prepare(RX_MODE);

	dtm_inst.state = STATE_RECEIVER_TEST;
	return 0;
}

int dtm_test_transmit(uint8_t channel, uint8_t length, enum dtm_packet pkt)
{
	uint8_t header_len;

	if (dtm_inst.state != STATE_IDLE) {
		return -EBUSY;
	}

	if (pkt == DTM_PACKET_FF_OR_VENDOR) {
		if ((dtm_inst.radio_mode == NRF_RADIO_MODE_BLE_1MBIT ||
		     dtm_inst.radio_mode == NRF_RADIO_MODE_BLE_2MBIT)) {
			pkt = DTM_PACKET_VENDOR;
		} else {
			pkt = DTM_PACKET_FF;
		}
	}

	dtm_inst.packet_type = pkt;
	dtm_inst.packet_len = length;
	dtm_inst.phys_ch = channel;
	dtm_inst.current_pdu = dtm_inst.pdu;

	/* Check for illegal values of m_phys_ch. Skip the check if the
	 * packet is vendor specific.
	 */
	if (pkt != DTM_PACKET_VENDOR && dtm_inst.phys_ch > PHYS_CH_MAX) {
		/* Parameter error */
		/* Note: State is unchanged; ongoing test not affected */
		return -EINVAL;
	}

	/* Check for illegal values of packet_len. Skip the check
	 * if the packet is vendor spesific.
	 */
	if (dtm_inst.packet_type != DTM_PKT_TYPE_VENDORSPECIFIC &&
	    dtm_inst.packet_len > DTM_PAYLOAD_MAX_SIZE) {
		/* Parameter error */
		return -EINVAL;
	}

	dtm_inst.rx_pkt_count = 0;

	header_len = (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) ?
		     DTM_HEADER_WITH_CTE_SIZE : DTM_HEADER_SIZE;

	dtm_inst.current_pdu->content[DTM_LENGTH_OFFSET] = dtm_inst.packet_len;
	/* Note that PDU uses 4 bits even though BLE DTM uses only 2
	 * (the HCI SDU uses all 4)
	 */
	switch (dtm_inst.packet_type) {
	case DTM_PACKET_PRBS9:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_PRBS9;
		/* Non-repeated, must copy entire pattern to PDU */
		memcpy(dtm_inst.current_pdu->content + header_len,
		       dtm_prbs9_content, dtm_inst.packet_len);
		break;

	case DTM_PACKET_0F:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0X0F;
		/* Bit pattern 00001111 repeated */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0X0F_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_55:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0X55;
		/* Bit pattern 01010101 repeated */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0X55_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_PRBS15:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_PRBS15;
		/* Non-repeated, must copy entire pattern to PDU */
		memcpy(dtm_inst.current_pdu->content + header_len,
		       dtm_prbs15_content, dtm_inst.packet_len);
		break;
		break;

	case DTM_PACKET_FF:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0XFF;
		/* Bit pattern 11111111 repeated. */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0XFF_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_00:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0X00;
		/* Bit pattern 00000000 repeated */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0X00_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_F0:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0XF0;
		/* Bit pattern 11110000 repeated */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0XF0_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_AA:
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] =
			DTM_PDU_TYPE_0XAA;
		/* Bit pattern 10101010 repeated */
		memset(dtm_inst.current_pdu->content + header_len,
		       RFPHY_TEST_0XAA_REF_PATTERN,
		       dtm_inst.packet_len);
		break;

	case DTM_PACKET_VENDOR:
		/* The length field is for indicating the vendor
		 * specific command to execute. The channel field
		 * is used for vendor specific options to the command.
		 */
		return dtm_vendor_specific_pkt(length, channel);

	default:
		/* Parameter error */
		return -EINVAL;
	}

	if (dtm_inst.cte_info.mode != DTM_CTE_MODE_OFF) {
		dtm_inst.current_pdu->content[DTM_HEADER_OFFSET] |=
							DTM_PKT_CP_BIT;
		dtm_inst.current_pdu->content[DTM_HEADER_CTEINFO_OFFSET] =
							dtm_inst.cte_info.info;
	}

	/* Initialize CRC value, set channel */
	radio_prepare(TX_MODE);

	/* Set the timer to the correct period. The delay between each
	 * packet is described in the Bluetooth Core Specification,
	 * Vol. 6 Part F Section 4.1.6.
	 */
	nrfx_timer_extended_compare(&dtm_inst.timer, NRF_TIMER_CC_CHANNEL0,
			dtm_packet_interval_calculate(dtm_inst.packet_len, dtm_inst.radio_mode),
			NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, false);

#if CONFIG_FEM
	if ((dtm_inst.fem.tx_power_control != FEM_USE_DEFAULT_TX_POWER_CONTROL) &&
	    (!IS_ENABLED(CONFIG_DTM_POWER_CONTROL_AUTOMATIC))) {
		if (fem_tx_power_control_set(dtm_inst.fem.tx_power_control) != 0) {
			return -EINVAL;
		}
	}

	(void)fem_power_up();
	(void)fem_tx_configure(dtm_inst.fem.ramp_up_time);
#endif /* CONFIG_FEM */

	radio_ppi_configure(false, 0);

	unsigned int key = irq_lock();
	/* Trigger first radio and timer start. */
	radio_start(false, true);

	/* Reconfigure radio TX trigger event. */
	radio_tx_ppi_reconfigure();

	irq_unlock(key);

	dtm_inst.state = STATE_TRANSMITTER_TEST;

	return 0;
}

int dtm_test_end(uint16_t *pack_cnt)
{
	if (!pack_cnt) {
		return -EINVAL;
	}

	*pack_cnt = dtm_inst.rx_pkt_count;
	dtm_test_done();

	return 0;
}

static struct dtm_pdu *radio_buffer_swap(void)
{
	struct dtm_pdu *received_pdu = dtm_inst.current_pdu;
	uint32_t packet_index = (dtm_inst.current_pdu == dtm_inst.pdu);

	dtm_inst.current_pdu = &dtm_inst.pdu[packet_index];

	nrf_radio_packetptr_set(NRF_RADIO, dtm_inst.current_pdu);

	return received_pdu;
}

static void on_radio_end_event(void)
{
	if (dtm_inst.state != STATE_RECEIVER_TEST) {
		return;
	}

	struct dtm_pdu *received_pdu = radio_buffer_swap();

	radio_start(true, false);

#if NRF52_ERRATA_172_PRESENT
	if (dtm_inst.anomaly_172_wa_enabled) {
		nrfx_timer_compare(&dtm_inst.anomaly_timer,
			NRF_TIMER_CC_CHANNEL0,
			nrfx_timer_ms_to_ticks(
				&dtm_inst.anomaly_timer,
				BLOCKER_FIX_WAIT_DEFAULT),
			true);
		nrfx_timer_compare(&dtm_inst.anomaly_timer,
			NRF_TIMER_CC_CHANNEL1,
			nrfx_timer_us_to_ticks(
				&dtm_inst.anomaly_timer,
				BLOCKER_FIX_WAIT_END),
			true);
		nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
				      NRF_TIMER_EVENT_COMPARE0);
		nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
				      NRF_TIMER_EVENT_COMPARE1);
		nrfx_timer_clear(&dtm_inst.anomaly_timer);
		nrfx_timer_enable(&dtm_inst.anomaly_timer);
	}
#endif /* NRF52_ERRATA_172_PRESENT */

	if (nrf_radio_crc_status_check(NRF_RADIO) &&
	    check_pdu(received_pdu)) {
		/* Count the number of successfully received
		 * packets.
		 */
		dtm_inst.rx_pkt_count++;
	}

	/* Note that failing packets are simply ignored (CRC or
	 * contents error).
	 */

	/* Zero fill all pdu fields to avoid stray data */
	memset(received_pdu, 0, DTM_PDU_MAX_MEMORY_SIZE);
}

static void radio_handler(const void *context)
{
	if (nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_ADDRESS)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_ADDRESS);
#if NRF52_ERRATA_172_PRESENT
		if (dtm_inst.state == STATE_RECEIVER_TEST &&
		    dtm_inst.anomaly_172_wa_enabled) {
			nrfx_timer_disable(&dtm_inst.anomaly_timer);
		}
#endif /* NRF52_ERRATA_172_PRESENT */
	}

	if (nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_END)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_END);

		NVIC_ClearPendingIRQ(RADIO_IRQn);

		on_radio_end_event();
	}

	if (nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_READY)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_READY);

#if NRF52_ERRATA_172_PRESENT
		if (dtm_inst.state == STATE_RECEIVER_TEST &&
		    dtm_inst.anomaly_172_wa_enabled) {
			nrfx_timer_clear(&dtm_inst.anomaly_timer);
			if (!nrfx_timer_is_enabled(&dtm_inst.anomaly_timer)) {
				nrfx_timer_enable(&dtm_inst.anomaly_timer);
			}
		}
#endif /* NRF52_ERRATA_172_PRESENT */
	}

#if defined(RADIO_EVENTS_RSSIEND_EVENTS_RSSIEND_Msk)
	if (nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_RSSIEND)) {
		nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_RSSIEND);
	}
#endif

}

static void dtm_timer_handler(nrf_timer_event_t event_type, void *context)
{
	// Do nothing
}

#if NRF52_ERRATA_172_PRESENT
static void anomaly_timer_handler(nrf_timer_event_t event_type, void *context)
{
	switch (event_type) {
	case NRF_TIMER_EVENT_COMPARE0:
	{
		uint8_t rssi = anomaly_172_rssi_check();

		if (dtm_inst.strict_mode) {
			if (rssi > BLOCKER_FIX_RSSI_THRESHOLD) {
				anomaly_172_strict_mode_set(false);
			}
		} else {
			bool too_many_detects = false;
			uint32_t packetcnt2 = *(volatile uint32_t *) 0x40001574;
			uint32_t detect_cnt = packetcnt2 & 0xffff;
			uint32_t addr_cnt = (packetcnt2 >> 16) & 0xffff;

			if ((detect_cnt > BLOCKER_FIX_CNTDETECTTHR) &&
			    (addr_cnt < BLOCKER_FIX_CNTADDRTHR)) {
				too_many_detects = true;
			}

			if ((rssi < BLOCKER_FIX_RSSI_THRESHOLD) ||
			    too_many_detects) {
				anomaly_172_strict_mode_set(true);
			}
		}

		anomaly_172_radio_operation();

		nrfx_timer_disable(&dtm_inst.anomaly_timer);

		nrfx_timer_compare(&dtm_inst.anomaly_timer,
			NRF_TIMER_CC_CHANNEL0,
			nrfx_timer_ms_to_ticks(&dtm_inst.anomaly_timer,
					       BLOCKER_FIX_WAIT_DEFAULT),
			true);

		nrfx_timer_clear(&dtm_inst.anomaly_timer);
		nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
				      NRF_TIMER_EVENT_COMPARE0);
		nrfx_timer_enable(&dtm_inst.anomaly_timer);

		NRFX_IRQ_PENDING_CLEAR(
			nrfx_get_irq_number(dtm_inst.anomaly_timer.p_reg));
	} break;

	case NRF_TIMER_EVENT_COMPARE1:
	{
		uint8_t rssi = anomaly_172_rssi_check();

		if (dtm_inst.strict_mode) {
			if (rssi >= BLOCKER_FIX_RSSI_THRESHOLD) {
				anomaly_172_strict_mode_set(false);
			}
		} else {
			if (rssi < BLOCKER_FIX_RSSI_THRESHOLD) {
				anomaly_172_strict_mode_set(true);
			}
		}

		anomaly_172_radio_operation();

		nrf_timer_event_clear(dtm_inst.anomaly_timer.p_reg,
				      NRF_TIMER_EVENT_COMPARE1);
		/* Disable this event. */
		nrfx_timer_compare(&dtm_inst.anomaly_timer,
				   NRF_TIMER_CC_CHANNEL1,
				   0,
				   false);

		NRFX_IRQ_PENDING_CLEAR(
			nrfx_get_irq_number(dtm_inst.anomaly_timer.p_reg));
	} break;

	default:
		break;
	}
}
#endif /* NRF52_ERRATA_172_PRESENT */
