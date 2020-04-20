#ifndef __DEV_INFO__
#define __DEV_INFO__

#include <stdint.h>

#define BLE_ADV_NAME "BiXin_abcd"
#define BLE_ADV_NAME_LEN 10

#define BLE_MAC_LEN 0x06
#define BLE_NAME_LEN 0x0A

typedef struct BLE_DEVICE_INFO {
  uint8_t ucBle_Mac[BLE_MAC_LEN];
  uint8_t ucBle_Name[BLE_NAME_LEN + 1];
  uint8_t ucBle_Version[2];

} Ble_Info;

typedef struct USB_DEVICE_INFO {
  uint8_t ucUsb_lable[33];
  uint8_t ucUsb_sn[13];
  uint8_t ucfingerprint[33];
} USB_Info;

extern Ble_Info g_ble_info;
extern USB_Info g_usb_info;

#endif