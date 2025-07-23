/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <nrfx_timer.h>
#include <zephyr/logging/log.h>

#include "dtm_uart_wait.h"

LOG_MODULE_REGISTER(dtm_wait, CONFIG_DTM_TRANSPORT_LOG_LEVEL);

/* Timer used for measuring UART poll cycle wait time. */
#if defined(CONFIG_SOC_SERIES_NRF54HX)
	#define WAIT_TIMER_INSTANCE        021
#elif defined(CONFIG_SOC_SERIES_NRF54LX)
	#define WAIT_TIMER_INSTANCE        20
#else
	#define WAIT_TIMER_INSTANCE        1
#endif /* defined(CONFIG_SOC_SERIES_NRF54HX) */

#define WAIT_TIMER_IRQ             NRFX_CONCAT_3(TIMER,			 \
						 WAIT_TIMER_INSTANCE,    \
						 _IRQn)
#define WAIT_TIMER_IRQ_HANDLER     NRFX_CONCAT_3(nrfx_timer_,		 \
						 WAIT_TIMER_INSTANCE,    \
						 _irq_handler)

BUILD_ASSERT(NRFX_CONCAT_3(CONFIG_, NRFX_TIMER, WAIT_TIMER_INSTANCE) == 1,
	     "Wait DTM timer needs additional KConfig configuration");

#if DT_NODE_HAS_PROP(DTM_UART, current_speed)
/* UART Baudrate used to communicate with the DTM library. */
#define DTM_UART_BAUDRATE DT_PROP(DTM_UART, current_speed)

/* The UART poll cycle in micro seconds.
 * A baud rate of e.g. 19200 bits / second, and 8 data bits, 1 start/stop bit,
 * no flow control, give the time to transmit a byte:
 * 10 bits * 1/19200 = approx: 520 us. To ensure no loss of bytes,
 * the UART should be polled every 260 us.
 */
#define DTM_UART_POLL_CYCLE ((uint32_t) (10 * 1e6 / DTM_UART_BAUDRATE / 2))
#else
#error "DTM UART node not found"
#endif /* DT_NODE_HAS_PROP(DTM_UART, currrent_speed) */

/* Timer to be used for measuring UART poll cycle wait time. */
static const nrfx_timer_t wait_timer = NRFX_TIMER_INSTANCE(WAIT_TIMER_INSTANCE);

/* Semaphore for synchronizing UART poll cycle wait time.*/
static K_SEM_DEFINE(wait_sem, 0, 1);

static void wait_timer_handler(nrf_timer_event_t event_type, void *context)
{
	nrfx_timer_disable(&wait_timer);
	nrfx_timer_clear(&wait_timer);

	k_sem_give(&wait_sem);
}

int dtm_uart_wait_init(void)
{
	nrfx_err_t err;
	nrfx_timer_config_t timer_cfg = {
		.frequency = NRFX_MHZ_TO_HZ(1),
		.mode      = NRF_TIMER_MODE_TIMER,
		.bit_width = NRF_TIMER_BIT_WIDTH_16,
	};

	err = nrfx_timer_init(&wait_timer, &timer_cfg, wait_timer_handler);
	if (err != NRFX_SUCCESS) {
		LOG_ERR("nrfx_timer_init failed with: %d", err);
		return -EAGAIN;
	}

	IRQ_CONNECT(WAIT_TIMER_IRQ, CONFIG_DTM_TIMER_IRQ_PRIORITY,
		    WAIT_TIMER_IRQ_HANDLER, NULL, 0);

	nrfx_timer_compare(&wait_timer,
		NRF_TIMER_CC_CHANNEL0,
		nrfx_timer_us_to_ticks(&wait_timer, DTM_UART_POLL_CYCLE),
		true);

	return 0;
}

void dtm_uart_wait(void)
{
	int err;

	nrfx_timer_enable(&wait_timer);

	err = k_sem_take(&wait_sem, K_FOREVER);
	if (err) {
		LOG_ERR("UART wait error: %d", err);
	}
}
