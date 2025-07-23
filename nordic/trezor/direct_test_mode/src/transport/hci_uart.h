/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef HCI_UART_H_
#define HCI_UART_H_

#include <zephyr/net_buf.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** @brief Put read HCI packet into the internal DTM buffer.
 *
 * This callback puts the HCI packet into the internal buffer
 * of the DTM module.
 *
 * @param[in] buf Buffer containing the HCI packet.
 */
typedef void (*hci_uart_read_cb)(struct net_buf *buf);

/** @brief Initialize the HCI UART interface.
 *
 * @param[in] cb Pointer to the callback function for
 * saving the HCI packet into the internal buffer.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int hci_uart_init(hci_uart_read_cb cb);

/** @brief Transmit an HCI packet.
 *
 * This function schedules transmission of an HCI packet.
 *
 * @param[in] type    Packet type.
 * @param[in] hdr     Packet header.
 * @param[in] hdr_len Length of the header.
 * @param[in] pld     Packet payload.
 * @param[in] len     Length of the payload.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int hci_uart_write(uint8_t type, const uint8_t *hdr, size_t hdr_len,
		   const uint8_t *pld, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* HCI_UART_H_ */
