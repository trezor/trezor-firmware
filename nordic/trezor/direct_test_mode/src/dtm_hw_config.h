/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef DTM_HW_CONFIG_H_
#define DTM_HW_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

/* Devicetree node identifier for the radio node. */
#define RADIO_NODE DT_NODELABEL(radio)

#if DT_PROP(DT_NODELABEL(radio), dfe_supported) && \
	DT_NODE_HAS_STATUS(RADIO_NODE, okay)
#define DIRECTION_FINDING_SUPPORTED 1
#else
#define DIRECTION_FINDING_SUPPORTED 0
#endif /* DT_PROP(DT_NODELABEL(radio), dfe_supported) && \
	* DT_NODE_HAS_STATUS(RADIO_NODE, okay)
	*/

/* Maximum transmit or receive time, in microseconds, that the local
 * Controller supports for transmission of a single
 * Link Layer Data Physical Channel PDU, divided by 2.
 */
#if defined(NRF52840_XXAA) || defined(NRF52833_XXAA) || \
	defined(NRF52811_XXAA) || defined(NRF52820_XXAA)
#define NRF_MAX_RX_TX_TIME 0x2148
#else
#define NRF_MAX_RX_TX_TIME 0x424
#endif /* defined(NRF52840_XXAA) || defined(NRF52833_XXAA) ||
	* defined(NRF52811_XXAA) || defined(NRF52820_XXAA)
	*/

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

#ifdef __cplusplus
}
#endif

#endif /* DTM_HW_CONFIG_H_ */
