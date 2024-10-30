
#include <zephyr/types.h>
#include <zephyr/kernel.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>

#include <zephyr/logging/log.h>

#include <dk_buttons_and_leds.h>

#include "connection.h"
#include "advertising.h"
#include "int_comm.h"
#include "oob.h"

#define CON_STATUS_LED DK_LED2

#define LOG_MODULE_NAME fw_int_connection
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static struct bt_conn *current_conn;
static struct bt_conn *auth_conn;

void connected(struct bt_conn *conn, uint8_t err)
{
  char addr[BT_ADDR_LE_STR_LEN];

  if (err) {
    LOG_ERR("Connection failed (err %u)", err);
    return;
  }

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
  LOG_INF("Connected %s", addr);

  current_conn = bt_conn_ref(conn);

//  struct bt_le_conn_param params = BT_LE_CONN_PARAM_INIT(6,6,0,400);
//
//  bt_conn_le_param_update(conn, &params);

  err = bt_conn_le_phy_update(current_conn, BT_CONN_LE_PHY_PARAM_2M);
  if (err) {
    LOG_ERR("Phy update request failed: %d",  err);
  }

  dk_set_led_on(CON_STATUS_LED);

  send_status_event();
}

void disconnected(struct bt_conn *conn, uint8_t reason)
{
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  LOG_INF("Disconnected: %s (reason %u)", addr, reason);

  if (auth_conn) {
    bt_conn_unref(auth_conn);
    auth_conn = NULL;
  }

  if (current_conn) {
    bt_conn_unref(current_conn);
    current_conn = NULL;
    dk_set_led_off(CON_STATUS_LED);
  }

  send_status_event();
}

bool is_connected(void) {
  return current_conn != NULL;
}


void disconnect(void){
  if (current_conn) {
    bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
  }
}

void num_comp_reply(bool accept)
{
  if (accept) {
    bt_conn_auth_passkey_confirm(auth_conn);
    LOG_INF("Numeric Match, conn %p", (void *)auth_conn);
  } else {
    bt_conn_auth_cancel(auth_conn);
    LOG_INF("Numeric Reject, conn %p", (void *)auth_conn);
  }

  bt_conn_unref(auth_conn);
  auth_conn = NULL;
}

void passkey_to_str(uint8_t buf[6], unsigned int passkey) {
  buf[5] = (passkey % 10) + '0';
  buf[4] = ((passkey / 10) % 10) + '0';
  buf[3] = ((passkey / 100) % 10) + '0';
  buf[2] = ((passkey / 1000) % 10) + '0';
  buf[1] = ((passkey / 10000) % 10) + '0';
  buf[0] = ((passkey / 100000) % 10) + '0';
}

void auth_passkey_display(struct bt_conn *conn, unsigned int passkey)
{
  char addr[BT_ADDR_LE_STR_LEN];

  uint8_t passkey_str[6];
  passkey_to_str(passkey_str, passkey);
  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  //pb_comm_enqueue(PASSKEY_DISPLAY, passkey_str, 6);
}

void auth_passkey_confirm(struct bt_conn *conn, unsigned int passkey)
{
  char addr[BT_ADDR_LE_STR_LEN];

  auth_conn = bt_conn_ref(conn);

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

//  num_comp_reply(true);

   uint8_t passkey_str[6];
   passkey_to_str(passkey_str, passkey);
   send_pairing_request_event(passkey_str, 6);

   send_status_event();

}


void auth_cancel(struct bt_conn *conn)
{
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  LOG_INF("Pairing cancelled: %s", addr);
}



void pairing_complete(struct bt_conn *conn, bool bonded)
{
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  oob_signal();
  bt_le_oob_set_sc_flag(false);
  bt_le_oob_set_legacy_flag(false);

  if (bonded) {
    advertising_setup_wl();
  }

  LOG_INF("Pairing completed: %s, bonded: %d", addr, bonded);
}


void pairing_failed(struct bt_conn *conn, enum bt_security_err reason)
{
  char addr[BT_ADDR_LE_STR_LEN];

  bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

  oob_signal();
  bt_le_oob_set_sc_flag(false);
  bt_le_oob_set_legacy_flag(false);

  LOG_INF("Pairing failed conn: %s, reason %d", addr, reason);
}


struct bt_conn * conn_get_current(void){
  return current_conn;
}
