/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef DTM_H_
#define DTM_H_

#include <stdbool.h>
#include <zephyr/types.h>
#include <zephyr/devicetree.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NRF_IQ_SAMPLE_INVALID -32768

/** @brief DTM PHY mode */
enum dtm_phy {
	/** Bluetooth Low Energy 1 Mbps PHY. */
	DTM_PHY_1M,

	/** Bluetooth Low Energy 2 Mbps PHY. */
	DTM_PHY_2M,

	/** Bluetooth Low Energy Coded S=8 PHY. */
	DTM_PHY_CODED_S8,

	/** Bluetooth Low Energy Coded S=2 PHY. */
	DTM_PHY_CODED_S2
};

/** @brief DTM modulation index. */
enum dtm_modulation {
	/** Standard modulation index. */
	DTM_MODULATION_STANDARD,

	/** Stable modulation index. */
	DTM_MODULATION_STABLE
};

/** @brief DTM maximum supported values. */
enum dtm_max_supported {
	/** Maximum supported TX octets. */
	DTM_MAX_SUPPORTED_TX_OCTETS,

	/** Maximum supported TX time. */
	DTM_MAX_SUPPORTED_TX_TIME,

	/** Maximum supported RX octets. */
	DTM_MAX_SUPPORTED_RX_OCTETS,

	/** Maximum supported RX time. */
	DTM_MAX_SUPPORTED_RX_TIME,

	/** Maximum supported Constant Tone Extension length. */
	DTM_MAX_SUPPORTED_CTE_LENGTH
};

/** @brief Constant Tone Extension type. */
enum dtm_cte_type {
	/** Do not use Constant Tone Extension. */
	DTM_CTE_TYPE_NONE,

	/** Angle of Arrival. */
	DTM_CTE_TYPE_AOA,

	/** Angle of Departure 1 us slots. */
	DTM_CTE_TYPE_AOD_1US,

	/** Angle of Departure 2 us slots. */
	DTM_CTE_TYPE_AOD_2US
};

/** @brief DTM Constant Tone Extension slot duration. */
enum dtm_cte_slot_duration {
	/** CTE 1 us slots duration. */
	DTM_CTE_SLOT_DURATION_1US,

	/** CTE 2 us slots duration. */
	DTM_CTE_SLOT_DURATION_2US
};

/** @brief DTM transmit power request. */
enum dtm_tx_power_request {
	/** Request minimum power. */
	DTM_TX_POWER_REQUEST_MIN,

	/** Request maximum power. */
	DTM_TX_POWER_REQUEST_MAX,

	/** Request power by value. */
	DTM_TX_POWER_REQUEST_VAL
};

/** @brief DTM packet type. */
enum dtm_packet {
	/** Packet filled with PRBS9 stream as payload. */
	DTM_PACKET_PRBS9,

	/** Packet with 0x0F bytes as payload. */
	DTM_PACKET_0F,

	/** Packet with 0x55 bytes as payload. */
	DTM_PACKET_55,

	/** Packet filled with PRBS15 stream as payload. */
	DTM_PACKET_PRBS15,

	/** Packet with 0xFF bytes as payload or vendor specific packet. */
	DTM_PACKET_FF_OR_VENDOR,

	/** Packet with 0xFF bytes as payload. */
	DTM_PACKET_FF,

	/** Packet with 0x00 bytes as payload. */
	DTM_PACKET_00,

	/** Packet with 0xF0 bytes as payload. */
	DTM_PACKET_F0,

	/** Packet with 0xAA bytes as payload. */
	DTM_PACKET_AA,

	/** Vendor-specific packet. */
	DTM_PACKET_VENDOR
};

/** @brief DTM supported features. */
struct dtm_supp_features {
	/** Support for Data Packet Length Extension. */
	bool data_len_ext;

	/** Support for Bluetooth Low Energy 2 Mbps PHY. */
	bool phy_2m;

	/** Support for Stable Modulation Index. */
	bool stable_mod;

	/** Support for Bluetooth Low Energy Coded PHY. */
	bool coded_phy;

	/** Support for Constant Tone Extension. */
	bool cte;

	/** Support for Antenna switching. */
	bool ant_switching;

	/** Support for AoD transmission 1 us switching. */
	bool aod_1us_tx;

	/** Support for AoD reception 1 us switching. */
	bool aod_1us_rx;

	/** Support for AoA reception 1 us switching and sampling. */
	bool aoa_1us_rx;
};

/** @brief DTM transmit power. */
struct dtm_tx_power {
	/** Actual power in dBm. */
	int8_t power;

	/** Power at minimum level. */
	bool min;

	/** Power at maximum level. */
	bool max;
};

/** @brief DTM Packet status for IQ Sample report. */
enum dtm_packet_status {
	/** Packet received with proper CRC. */
	DTM_PACKET_STATUS_CRC_OK,

	/** Packet received with invalid CRC.
	 *  The Length and CTEInfo was used to calculate sampling points.
	 */
	DTM_PACKET_STATUS_CRC_ERR_TIME,

	/** Packet received with invalid CRC.
	 *  The sampling points were calculated in another way.
	 */
	DTM_PACKET_STATUS_CRC_ERR_OTHER,

	/** Packet received with invalid CRC.
	 *  Insufficient resources to sample.
	 */
	DTM_PACKET_STATUS_CRC_ERR_INSUFFICIENT
};

/** @brief IQ sample format. */
struct dtm_iq_sample {
	/** I sample value. */
	int16_t i;

	/** Q sample value. */
	int16_t q;
};

/** @brief DTM IQ sampling data with additional information. */
struct dtm_iq_data {
	/** Channel number. */
	uint8_t channel;

	/** RSSI value of received packet. */
	int16_t rssi;

	/** Antenna number used to measure RSSI. */
	uint8_t rssi_ant;

	/** CTE type. */
	enum dtm_cte_type type;

	/** CTE slot duration. */
	enum dtm_cte_slot_duration slot;

	/** Packet status. */
	enum dtm_packet_status status;

	/** IQ sample count. */
	uint8_t sample_cnt;

	/** IQ samples. */
	struct dtm_iq_sample *samples;
};

/** @brief Callback to report received IQ samples.
 *
 * @note The callback is used only with direction finding.
 *
 * @param[in] data Pointer to dtm_iq_data structure.
 */
typedef void (*dtm_iq_report_callback_t)(struct dtm_iq_data *data);

/** @brief Initialize the DTM module.
 *
 * This function initializes the DTM module and registers the IQ sampling callback.
 * If the callback is not needed, the pointer can be NULL.
 *
 * @param[in] iq_callback Function pointer to the IQ report callback, can be NULL.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_init(dtm_iq_report_callback_t callback);

/** @brief Prepare DTM for setup.
 *
 * @note This function should be called before setup functions.
 * The function can be called once before a block of setup functions.
 */
void dtm_setup_prepare(void);

/** @brief Reset the DTM state.
 *
 * The PHY is set to Bluetooth Low Energy 1M mode.
 * The modulation index is set to standard.
 * The CTE is turned off.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_reset(void);

/** @brief Set the PHY for DTM.
 *
 * @param[in] phy The PHY to be used.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_set_phy(enum dtm_phy phy);

/** @brief Set the modulation for DTM.
 *
 * @param[in] modulation The modulation to be used.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_set_modulation(enum dtm_modulation modulation);

/** @brief Read supported BLE features.
 *
 * @return Features supported by the device.
 */
struct dtm_supp_features dtm_setup_read_features(void);

/** @brief Read the maximum supported parameter value by DTM.
 *
 * @param[in] parameter Value to be read.
 * @param[out] max_val  The pointer to the maximum value.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_read_max_supported_value(enum dtm_max_supported parameter, uint16_t *max_val);

/** @brief Setup the CTE for DTM.
 *
 * @param[in] type The CTE type to be used.
 * @param[in] time The time of CTE in 8 us units.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_set_cte_mode(enum dtm_cte_type type, uint8_t time);

/** @brief Set the CTE slots duration for DTM.
 *
 * @param[in] slot The CTE slots duration.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_set_cte_slot(enum dtm_cte_slot_duration slot);

/** @brief Set the antenna parameters for DTM.
 *
 * @param[in] count       The antenna count.
 * @param[in] pattern     The antenna switching pattern.
 * @param[in] pattern_len The length of the pattern.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_setup_set_antenna_params(uint8_t count, uint8_t *pattern, uint8_t pattern_len);

/** @brief Set the transmit power for DTM.
 *
 * @param[in] power   The transmit power request.
 * @param[in] val     TX power value (in dBm) in case of DTM_TX_POWER_REQUEST_VAL request.
 * @param[in] channel The channel to adjust power (set to 0 if unknown).
 *
 * @return The actual TX power set by the function.
 */
struct dtm_tx_power dtm_setup_set_transmit_power(enum dtm_tx_power_request power, int8_t val,
						 uint8_t channel);

/** @brief Start the DTM reception test.
 *
 * @param[in] channel The reception channel.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_test_receive(uint8_t channel);

/** @brief Start the DTM transmission test.
 *
 * @param[in] channel The transmission channel.
 * @param[in] length  The packet length.
 * @param[in] pkt     The packet type.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_test_transmit(uint8_t channel, uint8_t length, enum dtm_packet pkt);

/** @brief Stop the DTM test.
 *
 * Stop current DTM test and return the number of received packets.
 *
 * @param[out] pack_cnt The pointer to the received packet count.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_test_end(uint16_t *pack_cnt);

#ifdef __cplusplus
}
#endif

#endif /* DTM_H_ */
