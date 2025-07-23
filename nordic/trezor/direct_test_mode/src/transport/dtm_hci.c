/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/net_buf.h>
#include <zephyr/bluetooth/hci_types.h>
#include <zephyr/sys/util.h>
#include <zephyr/sys/byteorder.h>
#include <dtm.h>

#include "hci_uart.h"
#include "dtm_transport.h"

LOG_MODULE_REGISTER(dtm_hci_tr, CONFIG_DTM_TRANSPORT_LOG_LEVEL);

#define BT_LE_FEAT_SET(feat, n)	(feat[(n) >> 3] |= BIT((n) & 7))

#define MAX_ANT_PATTERN_LENGTH 0x4B
#define SYNC_HANDLE_RECEIVER_TEST 0x0FFF

#define CONNECTIONLESS_IQ_REPORT_MAX_SIZE (sizeof(struct hci_connectionless_iq_report_evt) +	\
		(B_HCI_LE_CTE_REPORT_SAMPLE_COUNT_MAX * sizeof(struct bt_hci_le_iq_sample)))

/* HCI_Command_Complete with status only */
struct hci_base_cc_evt {
	struct bt_hci_evt_cmd_complete evt;
	struct bt_hci_evt_cc_status ret;
} __packed;

/* HCI_Command_Complete for Test End */
struct hci_test_end_cc_evt {
	struct bt_hci_evt_cmd_complete evt;
	struct bt_hci_rp_le_test_end ret;
} __packed;

/* HCI_Command_Complete for Read BD Addr */
struct hci_read_bd_addr_evt {
	struct bt_hci_evt_cmd_complete evt;
	struct bt_hci_rp_read_bd_addr ret;
} __packed;

/* HCI_Command_Complete for Read Local Features */
struct hci_read_local_feat_evt {
	struct bt_hci_evt_cmd_complete evt;
	struct bt_hci_rp_le_read_local_features ret;
} __packed;

/* HCI Connectionless IQ report */
struct hci_connectionless_iq_report_evt {
	struct bt_hci_evt_le_meta_event evt;
	struct bt_hci_evt_le_connectionless_iq_report report;
} __packed;

/* HCI RX Test all versions params */
union rx_params {
	struct bt_hci_cp_le_rx_test v1;
	struct bt_hci_cp_le_enh_rx_test v2;
	struct bt_hci_cp_le_rx_test_v3 v3;
};

/* HCI TX Test all versions params */
union tx_params {
	struct bt_hci_cp_le_tx_test v1;
	struct bt_hci_cp_le_enh_tx_test v2;
	struct bt_hci_cp_le_tx_test_v3 v3;
	struct bt_hci_cp_le_tx_test_v4 v4;
};

static K_FIFO_DEFINE(hci_rx_queue);

static int hci_to_dtm_payload(uint8_t hci_pld, enum dtm_packet *dtm_pld)
{
	if (!dtm_pld) {
		return -EINVAL;
	}

	switch (hci_pld) {
	case BT_HCI_TEST_PKT_PAYLOAD_PRBS9:
		*dtm_pld = DTM_PACKET_PRBS9;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_11110000:
		*dtm_pld = DTM_PACKET_0F;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_10101010:
		*dtm_pld = DTM_PACKET_55;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_PRBS15:
		*dtm_pld = DTM_PACKET_PRBS15;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_11111111:
		*dtm_pld = DTM_PACKET_FF;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_00000000:
		*dtm_pld = DTM_PACKET_00;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_00001111:
		*dtm_pld = DTM_PACKET_F0;
		break;

	case BT_HCI_TEST_PKT_PAYLOAD_01010101:
		*dtm_pld = DTM_PACKET_AA;
		break;

	default:
		return -EINVAL;
	}

	return 0;
}

static int phy_set(uint8_t phy)
{
	switch (phy) {
	case BT_HCI_LE_TX_PHY_1M:
		return dtm_setup_set_phy(DTM_PHY_1M);

	case BT_HCI_LE_TX_PHY_2M:
		return dtm_setup_set_phy(DTM_PHY_2M);

	case BT_HCI_LE_TX_PHY_CODED_S8:
		return dtm_setup_set_phy(DTM_PHY_CODED_S8);

	case BT_HCI_LE_TX_PHY_CODED_S2:
		return dtm_setup_set_phy(DTM_PHY_CODED_S2);

	default:
		return -EINVAL;
	}
}

static int mod_set(uint8_t mod)
{
	switch (mod) {
	case BT_HCI_LE_MOD_INDEX_STANDARD:
		return dtm_setup_set_modulation(DTM_MODULATION_STANDARD);

	case BT_HCI_LE_MOD_INDEX_STABLE:
		return dtm_setup_set_modulation(DTM_MODULATION_STABLE);

	default:
		return -EINVAL;
	}
}

static int cte_set(uint8_t cte_len, uint8_t cte_type,
		   uint8_t pattern_len, uint8_t *pattern)
{
	static uint8_t cur_pattern[MAX_ANT_PATTERN_LENGTH];
	int err;

	/* Check if CTE is used at all */
	if (!cte_len) {
		return dtm_setup_set_cte_mode(DTM_CTE_TYPE_NONE, 0);
	}

	if (pattern_len > MAX_ANT_PATTERN_LENGTH) {
		return -EINVAL;
	}

	switch (cte_type) {
	case BT_HCI_LE_AOA_CTE:
		err = dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOA, cte_len);
		break;

	case BT_HCI_LE_AOD_CTE_1US:
		err = dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOD_1US, cte_len);
		break;

	case BT_HCI_LE_AOD_CTE_2US:
		err = dtm_setup_set_cte_mode(DTM_CTE_TYPE_AOD_2US, cte_len);
		break;

	default:
		err = -EINVAL;
		break;
	}

	if (err) {
		return err;
	}

	memcpy(cur_pattern, pattern, pattern_len);

	return dtm_setup_set_antenna_params(0, cur_pattern, pattern_len);
}

static int tx_power_set(int8_t power, uint8_t channel)
{
	switch (power) {
	case BT_HCI_TX_TEST_POWER_MIN_SET:
		dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_MIN, 0, channel);
		break;

	case BT_HCI_TX_TEST_POWER_MAX_SET:
		dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_MAX, 0, channel);
		break;

	case BT_HCI_TX_TEST_POWER_MIN ... BT_HCI_TX_TEST_POWER_MAX:
		dtm_setup_set_transmit_power(DTM_TX_POWER_REQUEST_VAL, power, channel);
		break;

	default:
		return -EINVAL;
	}

	return 0;
}

static int base_cc_evt(uint16_t opcode, uint8_t status)
{
	struct hci_base_cc_evt tmp;
	struct bt_hci_evt_hdr hdr;

	hdr.evt = BT_HCI_EVT_CMD_COMPLETE;
	hdr.len = sizeof(tmp);

	tmp.evt.ncmd = 1;
	sys_put_le16(opcode, (uint8_t *)&tmp.evt.opcode);

	tmp.ret.status = status;

	LOG_INF("Responding to opcode %x, with status %d", opcode, status);
	return hci_uart_write(H4_TYPE_EVT, (uint8_t *)&hdr, sizeof(hdr), (uint8_t *)&tmp, hdr.len);
}

static int test_end_cc_evt(uint8_t status, uint16_t cnt)
{
	struct hci_test_end_cc_evt tmp;
	struct bt_hci_evt_hdr hdr;

	hdr.evt = BT_HCI_EVT_CMD_COMPLETE;
	hdr.len = sizeof(tmp);

	tmp.evt.ncmd = 1;
	sys_put_le16(BT_HCI_OP_LE_TEST_END, (uint8_t *)&tmp.evt.opcode);

	tmp.ret.status = status;
	sys_put_le16(cnt, (uint8_t *)&tmp.ret.rx_pkt_count);

	LOG_INF("Responding to test end, with status %d and count %d", status, cnt);
	return hci_uart_write(H4_TYPE_EVT, (uint8_t *)&hdr, sizeof(hdr), (uint8_t *)&tmp, hdr.len);
}

static int read_bd_addr_cc_evt(uint8_t status)
{
	struct hci_read_bd_addr_evt tmp;
	struct bt_hci_evt_hdr hdr;
	bt_addr_t bt_addr_zero = { { 0, 0, 0, 0, 0, 0 } };

	hdr.evt = BT_HCI_EVT_CMD_COMPLETE;
	hdr.len = sizeof(tmp);

	tmp.evt.ncmd = 1;
	sys_put_le16(BT_HCI_OP_READ_BD_ADDR, (uint8_t *)&tmp.evt.opcode);

	tmp.ret.status = status;
	memcpy(&tmp.ret.bdaddr, &bt_addr_zero, sizeof(tmp.ret.bdaddr));

	LOG_INF("Responding to address query with status %d", status);
	return hci_uart_write(H4_TYPE_EVT, (uint8_t *)&hdr, sizeof(hdr), (uint8_t *)&tmp, hdr.len);
}

static int read_local_feat_cc_evt(uint8_t status, uint8_t *features)
{
	struct hci_read_local_feat_evt tmp;
	struct bt_hci_evt_hdr hdr;

	hdr.evt = BT_HCI_EVT_CMD_COMPLETE;
	hdr.len = sizeof(tmp);

	tmp.evt.ncmd = 1;
	sys_put_le16(BT_HCI_OP_LE_READ_LOCAL_FEATURES, (uint8_t *)&tmp.evt.opcode);

	tmp.ret.status = status;
	memcpy(&tmp.ret.features, features, sizeof(tmp.ret.features));

	LOG_INF("Responding to features query with status %d", status);
	return hci_uart_write(H4_TYPE_EVT, (uint8_t *)&hdr, sizeof(hdr), (uint8_t *)&tmp, hdr.len);
}

static void iq_report_evt(struct dtm_iq_data *iq_data)
{
	uint8_t buf[CONNECTIONLESS_IQ_REPORT_MAX_SIZE];
	struct hci_connectionless_iq_report_evt *tmp =
						(struct hci_connectionless_iq_report_evt *)buf;
	struct bt_hci_evt_hdr hdr;
	size_t i;
	int err;

	hdr.evt = BT_HCI_EVT_LE_META_EVENT;
	hdr.len = sizeof(*tmp);
	hdr.len += sizeof(struct bt_hci_le_iq_sample) * iq_data->sample_cnt;

	if (hdr.len > CONNECTIONLESS_IQ_REPORT_MAX_SIZE) {
		LOG_ERR("Invalid sample count in IQ report callback.");
		return;
	}

	tmp->evt.subevent = BT_HCI_EVT_LE_CONNECTIONLESS_IQ_REPORT;

	tmp->report.sync_handle = sys_cpu_to_le16(SYNC_HANDLE_RECEIVER_TEST);
	tmp->report.chan_idx = iq_data->channel;
	tmp->report.rssi = iq_data->rssi;
	tmp->report.rssi_ant_id = iq_data->rssi_ant;

	switch (iq_data->type) {
	case DTM_CTE_TYPE_AOA:
		tmp->report.cte_type = BT_HCI_LE_AOA_CTE;
		break;

	case DTM_CTE_TYPE_AOD_1US:
		tmp->report.cte_type = BT_HCI_LE_AOD_CTE_1US;
		break;

	case DTM_CTE_TYPE_AOD_2US:
		tmp->report.cte_type = BT_HCI_LE_AOD_CTE_2US;
		break;

	default:
		LOG_ERR("Invalid CTE type in IQ report callback.");
		return;
	}

	switch (iq_data->slot) {
	case DTM_CTE_SLOT_DURATION_1US:
		tmp->report.slot_durations = BT_HCI_LE_ANTENNA_SWITCHING_SLOT_1US;
		break;

	case DTM_CTE_SLOT_DURATION_2US:
		tmp->report.slot_durations = BT_HCI_LE_ANTENNA_SWITCHING_SLOT_2US;
		break;

	default:
		LOG_ERR("Invalid CTE slot duration in IQ report callback.");
		return;
	}

	switch (iq_data->status) {
	case DTM_PACKET_STATUS_CRC_OK:
		tmp->report.packet_status = BT_HCI_LE_CTE_CRC_OK;
		break;

	case DTM_PACKET_STATUS_CRC_ERR_TIME:
		tmp->report.packet_status = BT_HCI_LE_CTE_CRC_ERR_CTE_BASED_TIME;
		break;

	case DTM_PACKET_STATUS_CRC_ERR_OTHER:
		tmp->report.packet_status = BT_HCI_LE_CTE_CRC_ERR_CTE_BASED_OTHER;
		break;

	case DTM_PACKET_STATUS_CRC_ERR_INSUFFICIENT:
		tmp->report.packet_status = BT_HCI_LE_CTE_INSUFFICIENT_RESOURCES;
		break;

	default:
		LOG_ERR("Invalid status in IQ report callback.");
		return;
	}

	tmp->report.per_evt_counter = 0;

	tmp->report.sample_count = iq_data->sample_cnt;
	for (i = 0; i < tmp->report.sample_count; i++) {
		if (iq_data->samples[i].i == NRF_IQ_SAMPLE_INVALID) {
			tmp->report.sample[i].i = BT_HCI_LE_CTE_REPORT_NO_VALID_SAMPLE;
		} else {
			tmp->report.sample[i].i  = (int8_t)(iq_data->samples[i].i >> 4);
		}

		if (iq_data->samples[i].q == NRF_IQ_SAMPLE_INVALID) {
			tmp->report.sample[i].q = BT_HCI_LE_CTE_REPORT_NO_VALID_SAMPLE;
		} else {
			tmp->report.sample[i].q  = (int8_t)(iq_data->samples[i].q >> 4);
		}
	}

	err = hci_uart_write(H4_TYPE_EVT, (uint8_t *)&hdr, sizeof(hdr), (uint8_t *)&buf, hdr.len);
	if (err) {
		LOG_ERR("Error writing LE Connectionless IQ Report event.");
	}
}

static int hci_reset(void)
{
	int err;

	err = dtm_setup_reset();
	if (err) {
		base_cc_evt(BT_HCI_OP_RESET, BT_HCI_ERR_HW_FAILURE);
	}

	return base_cc_evt(BT_HCI_OP_RESET, BT_HCI_ERR_SUCCESS);
}

static int hci_read_bd_addr(void)
{
	return read_bd_addr_cc_evt(BT_HCI_ERR_SUCCESS);
}

static int hci_read_local_features(void)
{
	uint8_t hci_features[8] = { 0 };
	struct dtm_supp_features features;

	features = dtm_setup_read_features();

	if (features.data_len_ext) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_DLE);
	}

	if (features.phy_2m) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_PHY_2M);
	}

	if (features.stable_mod) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_SMI_TX);
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_SMI_RX);
	}

	if (features.coded_phy) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_PHY_CODED);
	}

	if (features.cte) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_RX_CTE);
	}

	if (features.ant_switching) {
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_ANT_SWITCH_TX_AOD);
		BT_LE_FEAT_SET(hci_features, BT_LE_FEAT_BIT_ANT_SWITCH_RX_AOA);
	}

	return read_local_feat_cc_evt(BT_HCI_ERR_SUCCESS, hci_features);
}

static int hci_rx_test(uint16_t opcode, const uint8_t *data)
{
	union rx_params *params = (union rx_params *)data;
	uint8_t def_pattern[2] = {0, 0};
	int err;

	uint8_t chan;
	uint8_t phy = 0x01;
	uint8_t mod = 0x00;
	uint8_t cte_len = 0x00;
	uint8_t cte_type = 0x00;
	uint8_t slot_durations = 0x01;
	uint8_t pattern_len = 0x02;
	uint8_t *pattern = def_pattern;

	switch (opcode) {
	case BT_HCI_OP_LE_RX_TEST:
		chan = params->v1.rx_ch;
		LOG_DBG("RX Test command: v1, chan: %d.", chan);
		break;

	case BT_HCI_OP_LE_ENH_RX_TEST:
		chan = params->v2.rx_ch;
		phy = params->v2.phy;
		mod = params->v2.mod_index;
		LOG_DBG("RX Test command: v2, chan: %d, phy: %d, mod: %d.", chan, phy, mod);
		break;

	case BT_HCI_OP_LE_RX_TEST_V3:
		chan = params->v3.rx_ch;
		phy = params->v3.phy;
		mod = params->v3.mod_index;
		cte_len = params->v3.expected_cte_len;
		cte_type = params->v3.expected_cte_type;
		slot_durations = params->v3.slot_durations;
		pattern_len = params->v3.switch_pattern_len;
		pattern = params->v3.ant_ids;
		LOG_DBG("RX Test command: v3, chan: %d, phy: %d, mod: %d, cte_len: %d,"
			" cte_type: %d, slot_durations: %d, pattern_len: %d.",
			chan, phy, mod, cte_len, cte_type, slot_durations, pattern_len);
		break;

	default:
		return -EINVAL;
	}

	dtm_setup_prepare();

	err = phy_set(phy);
	if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	}

	err = mod_set(mod);
	if (err == -ENOTSUP) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	} else if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
	}

	if ((cte_len != 0) &&
		(phy != BT_HCI_LE_TX_PHY_CODED_S8) && (phy != BT_HCI_LE_TX_PHY_CODED_S2)) {
		return base_cc_evt(opcode, BT_HCI_ERR_CMD_DISALLOWED);
	}

	err = cte_set(cte_len, cte_type, pattern_len, pattern);
	if (err == -ENOTSUP) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	} else if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
	}

	if (cte_len != 0) {
		err = dtm_setup_set_cte_slot(slot_durations);
		if (err == -ENOTSUP) {
			return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
		} else if (err == -EINVAL) {
			return base_cc_evt(opcode, BT_HCI_ERR_INVALID_PARAM);
		} else if (err != 0) {
			return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
		}
	}

	err = dtm_test_receive(chan);
	if (err == -EINVAL) {
		return base_cc_evt(opcode, BT_HCI_ERR_INVALID_PARAM);
	} else if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
	}

	return base_cc_evt(opcode, BT_HCI_ERR_SUCCESS);
}

static int hci_tx_test(uint16_t opcode, const uint8_t *data)
{
	union tx_params *params = (union tx_params *)data;
	uint8_t def_pattern[2] = {0, 0};

	uint8_t chan;
	uint8_t data_len;
	uint8_t payload;
	uint8_t phy = BT_HCI_LE_TX_PHY_1M;
	uint8_t cte_len = 0x00;
	uint8_t cte_type = 0x00;
	uint8_t pattern_len = 0x02;
	uint8_t *pattern = def_pattern;
	int8_t power = 0x7F;

	enum dtm_packet pld;
	int err;

	switch (opcode) {
	case BT_HCI_OP_LE_TX_TEST:
		chan = params->v1.tx_ch;
		data_len = params->v1.test_data_len;
		payload = params->v1.pkt_payload;
		LOG_DBG("TX Test command: v1, chan: %d, data_len: %d, payload %d.",
			chan, data_len, payload);
		break;

	case BT_HCI_OP_LE_ENH_TX_TEST:
		chan = params->v2.tx_ch;
		data_len = params->v2.test_data_len;
		payload = params->v2.pkt_payload;
		phy = params->v2.phy;
		LOG_DBG("TX Test command: v2, chan: %d, data_len: %d, payload: %d, phy: %d.",
			chan, data_len, payload, phy);
		break;

	case BT_HCI_OP_LE_TX_TEST_V3:
		chan = params->v3.tx_ch;
		data_len = params->v3.test_data_len;
		payload = params->v3.pkt_payload;
		phy = params->v3.phy;
		cte_len = params->v3.cte_len;
		cte_type = params->v3.cte_type;
		pattern_len = params->v3.switch_pattern_len;
		pattern = params->v3.ant_ids;
		LOG_DBG("TX Test command: v3, chan: %d, data_len: %d, payload: %d, phy: %d,"
			" cte_len: %d, cte_type: %d, pattern_len: %d.",
			chan, data_len, payload, phy, cte_len, cte_type, pattern_len);
		break;

	case BT_HCI_OP_LE_TX_TEST_V4:
		struct bt_hci_cp_le_tx_test_v4_tx_power *tmp;

		chan = params->v4.tx_ch;
		data_len = params->v4.test_data_len;
		payload = params->v4.pkt_payload;
		phy = params->v4.phy;
		cte_len = params->v4.cte_len;
		cte_type = params->v4.cte_type;
		pattern_len = params->v4.switch_pattern_len;
		pattern = params->v4.ant_ids;
		tmp = (struct bt_hci_cp_le_tx_test_v4_tx_power *)&(params->v4.ant_ids[pattern_len]);
		power = tmp->tx_power;
		LOG_DBG("TX Test command: v3, chan: %d, data_len: %d, payload: %d, phy: %d,"
			" cte_len: %d, cte_type: %d, pattern_len: %d, power: %d.",
			chan, data_len, payload, phy, cte_len, cte_type, pattern_len, power);
		break;

	default:
		return -EINVAL;
	}

	dtm_setup_prepare();

	err = hci_to_dtm_payload(payload, &pld);
	if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	}

	err = phy_set(phy);
	if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	}

	if ((cte_len != 0) &&
		(phy != BT_HCI_LE_TX_PHY_CODED_S8) && (phy != BT_HCI_LE_TX_PHY_CODED_S2)) {
		return base_cc_evt(opcode, BT_HCI_ERR_CMD_DISALLOWED);
	}

	err = cte_set(cte_len, cte_type, pattern_len, pattern);
	if (err == -ENOTSUP) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	} else if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
	}

	err = tx_power_set(power, chan);
	if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_UNSUPP_FEATURE_PARAM_VAL);
	}

	err = dtm_test_transmit(chan, data_len, pld);
	if (err == -EINVAL) {
		return base_cc_evt(opcode, BT_HCI_ERR_INVALID_PARAM);
	} else if (err) {
		return base_cc_evt(opcode, BT_HCI_ERR_HW_FAILURE);
	}

	return base_cc_evt(opcode, BT_HCI_ERR_SUCCESS);
}

static int hci_test_end(void)
{
	uint16_t cnt;
	int err;

	err = dtm_test_end(&cnt);

	if (err == -EINVAL) {
		return test_end_cc_evt(BT_HCI_ERR_INVALID_PARAM, cnt);
	} else if (err) {
		return test_end_cc_evt(BT_HCI_ERR_HW_FAILURE, cnt);
	}

	return test_end_cc_evt(BT_HCI_ERR_SUCCESS, cnt);
}

static int hci_cmd(const struct bt_hci_cmd_hdr *hdr, const uint8_t *data)
{
	uint16_t cmd;

	cmd = sys_le16_to_cpu(hdr->opcode);

	LOG_INF("Processing HCI command opcode: 0x%04x", cmd);

	switch (cmd) {
	case BT_HCI_OP_RESET:
		LOG_INF("Executing HCI reset command.");
		return hci_reset();

	case BT_HCI_OP_READ_BD_ADDR:
		LOG_INF("Executing HCI Read BD_ADDR command.");
		return hci_read_bd_addr();

	case BT_HCI_OP_LE_READ_LOCAL_FEATURES:
		LOG_INF("Executing HCI LE Read Local Supported Features command.");
		return hci_read_local_features();

	case BT_HCI_OP_LE_RX_TEST:
	case BT_HCI_OP_LE_ENH_RX_TEST:
	case BT_HCI_OP_LE_RX_TEST_V3:
		LOG_INF("Executing HCI LE Receiver Test command.");
		return hci_rx_test(cmd, data);

	case BT_HCI_OP_LE_TX_TEST:
	case BT_HCI_OP_LE_ENH_TX_TEST:
	case BT_HCI_OP_LE_TX_TEST_V3:
	case BT_HCI_OP_LE_TX_TEST_V4:
		LOG_INF("Executing HCI LE Transmitter Test command.");
		return hci_tx_test(cmd, data);

	case BT_HCI_OP_LE_TEST_END:
		LOG_INF("Executing HCI LE Test End command.");
		return hci_test_end();

	default:
		LOG_ERR("Unknown HCI command opcode: 0x%04x", cmd);
		base_cc_evt(cmd, BT_HCI_ERR_UNKNOWN_CMD);
		return -ENOTSUP;
	}
}

static void dtm_hci_put(struct net_buf *buf)
{
	k_fifo_put(&hci_rx_queue, buf);
}

int dtm_tr_init(void)
{
	int err;

	err = hci_uart_init(dtm_hci_put);
	if (err) {
		LOG_ERR("Failed to initialize HCI over UART: %d", err);
		return err;
	}

	err = dtm_init(iq_report_evt);
	if (err) {
		LOG_ERR("Failed to initialize DTM: %d", err);
		return err;
	}

	return 0;
}

union dtm_tr_packet dtm_tr_get(void)
{
	union dtm_tr_packet tmp;

	tmp.hci = k_fifo_get(&hci_rx_queue, K_FOREVER);
	return tmp;
}

int dtm_tr_process(union dtm_tr_packet cmd)
{
	struct net_buf *buf = cmd.hci;
	const struct bt_hci_cmd_hdr *hdr;
	const uint8_t *data;
	uint8_t type;
	int err;

	if (!buf) {
		LOG_ERR("Command pointer is NULL.");
		return -EINVAL;
	}

	type = *(uint8_t *)net_buf_user_data(buf);

	switch (type) {
	case H4_TYPE_CMD:
		hdr = (const struct bt_hci_cmd_hdr *)buf->data;
		data = buf->data + sizeof(*hdr);
		err = hci_cmd(hdr, data);
		net_buf_unref(buf);
		return err;

	default:
		LOG_ERR("Tried to process unsupported HCI type.");
		return -ENOTSUP;
	}
}
