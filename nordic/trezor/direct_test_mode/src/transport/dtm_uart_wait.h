/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#ifndef DTM_UART_WAIT_H_
#define DTM_UART_WAIT_H_

#ifdef __cplusplus
extern "C" {
#endif

#define DTM_UART DT_CHOSEN(ncs_dtm_uart)

/** @brief Initialize wait function.
 *
 * @return 0 in case of success or negative value in case of error.
 */
int dtm_uart_wait_init(void);

/** @brief Wait for UART poll cycle.
 *
 * Wait for half of the UART period used by the DTM.
 */
void dtm_uart_wait(void);

#ifdef __cplusplus
}
#endif

#endif /* DTM_UART_WAIT_H_ */
