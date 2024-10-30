/*
 * Copyright (c) 2018 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

/** @file
 *  @brief Nordic UART Bridge Service (NUS) sample
 */

#include <zephyr/types.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <soc.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>


#include <dk_buttons_and_leds.h>

#include <zephyr/settings/settings.h>

#include <zephyr/logging/log.h>

#include "uart.h"
#include "spi.h"
#include "connection.h"
#include "int_comm.h"
#include "advertising.h"
#include "trz_nus.h"
#include "oob.h"
#include "events.h"

#define LOG_MODULE_NAME fw
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define STACKSIZE CONFIG_BT_NUS_THREAD_STACK_SIZE
#define PRIORITY 7

#define RUN_STATUS_LED DK_LED1
#define RUN_LED_BLINK_INTERVAL 1000

#define FW_RUNNING_SIG DK_LED3


static K_SEM_DEFINE(ble_init_ok, 0, 1);
static K_SEM_DEFINE(led_init_ok, 0, 1);

#define AUTH_SC_FLAG 0x08


static void security_changed(struct bt_conn *conn, bt_security_t level,
			     enum bt_security_err err)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	if (!err) {
		LOG_INF("Security changed: %s level %u", addr, level);
	} else {
		LOG_WRN("Security failed: %s level %u err %d", addr,
			level, err);
	}
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected    = connected,
	.disconnected = disconnected,
	.security_changed = security_changed,
};

//static enum bt_security_err pairing_accept(struct bt_conn *conn,
//                                           const struct bt_conn_pairing_feat *const feat)
//{
//  if (feat->oob_data_flag && (!(feat->auth_req & AUTH_SC_FLAG))) {
//    bt_le_oob_set_legacy_flag(true);
//  }
//
//  return BT_SECURITY_ERR_SUCCESS;
//
//}


static struct bt_conn_auth_cb conn_auth_callbacks = {
//  .pairing_accept = pairing_accept,
	.passkey_display = auth_passkey_display,
	.passkey_confirm = auth_passkey_confirm,
  .oob_data_request = auth_oob_data_request,
	.cancel = auth_cancel,
};

static struct bt_conn_auth_info_cb conn_auth_info_callbacks = {
	.pairing_complete = pairing_complete,
	.pairing_failed = pairing_failed
};


static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data,
			  uint16_t len)
{
  if ((dk_get_buttons() & DK_BTN2_MSK) == 0){
    LOG_INF("Trezor not ready, rejecting data");
//    send_error_response();
    return;
  }

	char addr[BT_ADDR_LE_STR_LEN] = {0};

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, ARRAY_SIZE(addr));

	LOG_DBG("Received data from: %s, %d", addr, len);

  spi_send(data, len);
}

static struct bt_nus_cb nus_cb = {
	.received = bt_receive_cb,
};

void error(void)
{
	dk_set_leds_state(DK_ALL_LEDS_MSK, DK_NO_LEDS_MSK);

	while (true) {
		/* Spin for ever */
		k_sleep(K_MSEC(1000));
	}
}


void button_changed(uint32_t button_state, uint32_t has_changed)
{

}

static void configure_gpio(void)
{
	int err;

	err = dk_buttons_init(button_changed);
	if (err) {
		LOG_ERR("Cannot init buttons (err: %d)", err);
	}

	err = dk_leds_init();
	if (err) {
		LOG_ERR("Cannot init LEDs (err: %d)", err);
	}
}

int main(void)
{
	int err = 0;

  LOG_INF("Initializing");


	configure_gpio();

  err = uart_init();
  if (err) {
    error();
  }

  spi_init();

  err = bt_conn_auth_cb_register(&conn_auth_callbacks);
  if (err) {
    printk("Failed to register authorization callbacks.\n");
    return 0;
  }

  err = bt_conn_auth_info_cb_register(&conn_auth_info_callbacks);
  if (err) {
    printk("Failed to register authorization info callbacks.\n");
    return 0;
  }

	err = bt_enable(NULL);
	if (err) {
		error();
	}

	LOG_INF("Bluetooth initialized");

	k_sem_give(&ble_init_ok);

	if (IS_ENABLED(CONFIG_SETTINGS)) {
		settings_load();
	}

	err = bt_nus_init(&nus_cb);
	if (err) {
		LOG_ERR("Failed to initialize UART service (err: %d)", err);
		return 0;
	}

  bt_set_name("TrezorGAP");

  events_init();
  advertising_init();
  int_comm_start();

  dk_set_led(FW_RUNNING_SIG, 1);
//  dk_set_led(FW_RUNNING_SIG, 0);
//  while(true) {
//    dk_set_led(FW_RUNNING_SIG, 1);
//    dk_set_led(FW_RUNNING_SIG, 0);
//  }
  send_status_event();

  //oob_init();

  k_sem_give(&led_init_ok);

	for (;;) {

    events_poll();
    printk("Event occurred\n");

    //oob_process();
    //int_comm_thread();
	}
}

void ble_write_thread(void)
{
	/* Don't go any further until BLE is initialized */
	k_sem_take(&ble_init_ok, K_FOREVER);

	for (;;) {
		/* Wait indefinitely for data to be sent over bluetooth */
		uart_data_t *buf = uart_get_data_ext();

		if (bt_nus_send(conn_get_current(), buf)) {
			LOG_WRN("Failed to send data over BLE connection: %d", buf->len);
			k_free(buf);
		}

      	LOG_DBG("Freeing UART data");
	}
}

void led_thread(void)
{
  int blink_status = 0;
  /* Don't go any further until BLE is initialized */
  k_sem_take(&led_init_ok, K_FOREVER);

  for (;;) {
		dk_set_led(RUN_STATUS_LED, (++blink_status) % 2);
		k_sleep(K_MSEC(RUN_LED_BLINK_INTERVAL));
  }
}


K_THREAD_DEFINE(ble_write_thread_id, STACKSIZE, ble_write_thread, NULL, NULL,
        NULL, PRIORITY, 0, 0);

K_THREAD_DEFINE(led_thread_id, STACKSIZE, led_thread, NULL, NULL,
        NULL, PRIORITY, 0, 0);
