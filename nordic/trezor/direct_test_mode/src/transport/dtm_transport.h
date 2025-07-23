/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef DTM_TRANSPORT_H_
#define DTM_TRANSPORT_H_

#include <zephyr/net_buf.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if (CONFIG_DTM_TRANSPORT_HCI || CONFIG_DTM_REMOTE_HCI_CHILD)
#define H4_TYPE_CMD 0x01
#define H4_TYPE_ACL 0x02
#define H4_TYPE_EVT 0x04
#define H4_TYPE_ISO 0x05
#endif

/** @brief DTM transport packet. */
union dtm_tr_packet {
	/** HCI packet buffer. */
	struct net_buf *hci;

	/** Two-wire uart 2-octet packet. */
	uint16_t twowire;
};

/** @brief Initialize DTM transport layer.
 *
 * @note This function also initializes the DTM module.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_tr_init(void);

/** @brief Poll for DTM command.
 *
 * This function polls for DTM command.
 *
 * @return DTM command.
 */
union dtm_tr_packet dtm_tr_get(void);

/** @brief Process DTM command and respond.
 *
 * This function processes the DTM command
 * and responds to the tester.
 *
 * @param[in] cmd DTM command.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_tr_process(union dtm_tr_packet cmd);

#ifdef __cplusplus
}
#endif

#endif /* DTM_TRANSPORT_H_ */
