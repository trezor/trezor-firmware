
#include <zephyr/types.h>
#include <zephyr/kernel.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <bluetooth/services/nus.h>

#include <zephyr/logging/log.h>

#include "int_comm.h"
#include "connection.h"
#include "oob.h"


#define LOG_MODULE_NAME fw_int_advertising
LOG_MODULE_REGISTER(LOG_MODULE_NAME);


#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN	(sizeof(DEVICE_NAME) - 1)

bool advertising = false;
bool advertising_wl = false;
int bond_cnt = 0;
int bond_cnt_tmp = 0;

static const struct bt_data ad[] = {
        BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
        BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static const struct bt_data sd[] = {
        BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_NUS_VAL),
};


static void add_to_whitelist(const struct bt_bond_info *info, void *user_data){
  char addr[BT_ADDR_LE_STR_LEN];
  bt_addr_le_to_str(&info->addr, addr, sizeof(addr));

  int err = bt_le_filter_accept_list_add(&info->addr);
  if (err){
    LOG_WRN("whitelist add: %s FAILED!\n", addr);
  }else{
    LOG_INF("whitelist add: %s\n", addr);
  }

  bond_cnt_tmp++;
}


void advertising_setup_wl(void) {
  bt_le_filter_accept_list_clear();
  bond_cnt_tmp= 0;
  bt_foreach_bond(BT_ID_DEFAULT, add_to_whitelist, NULL);
  bond_cnt = bond_cnt_tmp;
}

void advertising_start(bool wl){

  if (advertising) {
    if (wl != advertising_wl) {
      LOG_WRN("Restarting advertising");
      bt_le_adv_stop();
    }else {
      LOG_WRN("Already advertising");

      send_status_event();
      return;
    }
  }

  int err;

  if (wl) {
    advertising_setup_wl();
    LOG_INF("Advertising with whitelist");
    err = bt_le_adv_start(
            BT_LE_ADV_PARAM(BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_FILTER_CONN | BT_LE_ADV_OPT_FILTER_SCAN_REQ,
                            160, 1600, NULL),
            ad, ARRAY_SIZE(ad),
            sd, ARRAY_SIZE(sd));
  }
  else {
    LOG_INF("Advertising no whitelist");
    err = bt_le_adv_start(
            BT_LE_ADV_PARAM(BT_LE_ADV_OPT_CONNECTABLE,
                            160, 1600, NULL),
            ad, ARRAY_SIZE(ad),
            sd, ARRAY_SIZE(sd));
  }
  if (err) {
    LOG_ERR("Advertising failed to start (err %d)", err);
    send_status_event();
    return;
  }
  advertising = true;
  advertising_wl = wl;


  oob_fetch_addr();

  send_status_event();
}

void advertising_stop(void){

  if (!advertising) {
    LOG_WRN("Not advertising");

    send_status_event();
    return;
  }

  int err = bt_le_adv_stop();
  if (err) {
    LOG_ERR("Advertising failed to stop (err %d)", err);
    send_status_event();
    return;
  }
  advertising = false;
  advertising_wl = false;
  send_status_event();
}

bool is_advertising(void){
  return advertising;
}

bool is_advertising_whitelist(void){
  return advertising_wl;
}


void advertising_init(void){
  LOG_INF("Advertising init");
  advertising_setup_wl();
}

void erase_bonds(void){
  int err = bt_unpair(BT_ID_DEFAULT, BT_ADDR_LE_ANY);
  if (err) {
    LOG_INF("Cannot delete bonds (err: %d)\n", err);
  } else {
  	bt_le_filter_accept_list_clear();
  	bond_cnt = 0;
    LOG_INF("Bonds deleted successfully \n");
  }
}

int advertising_get_bond_count(void){
  return bond_cnt;
}
