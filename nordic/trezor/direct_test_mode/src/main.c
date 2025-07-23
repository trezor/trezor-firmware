/*
 * Copyright (c) 2020 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/device.h>
#include <zephyr/sys/printk.h>

#include "transport/dtm_transport.h"

int main(void)
{
	int err;
	union dtm_tr_packet cmd;

	printk("Starting Direct Test Mode example\n");

	err = dtm_tr_init();
	if (err) {
		printk("Error initializing DTM transport: %d\n", err);
		return err;
	}

	for (;;) {
		cmd = dtm_tr_get();
		err = dtm_tr_process(cmd);
		if (err) {
			printk("Error processing command: %d\n", err);
			return err;
		}
	}
}
