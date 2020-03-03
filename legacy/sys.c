#include <libopencm3/cm3/scb.h>
#include <libopencm3/stm32/gpio.h>
#include <string.h>

#include "bitmaps.h"
#include "oled.h"
#include "si2c.h"
#include "sys.h"
#include "timer.h"

uint8_t g_ucFlag = 0;
uint8_t g_ucBatValue = 0;

extern void vDISP_DeviceInfo(void);

/*
 * ble mac get ble name
 */
void vCalu_BleName(uint8_t *pucMac, uint8_t *pucName) {
  uint8_t i;

  memcpy(pucName, BLE_ADV_NAME, BLE_ADV_NAME_LEN);

  for (i = 0; i < 4; i++) {
    pucName[BLE_ADV_NAME_LEN - 4 + i] += pucMac[i] % 20;
  }
}

/*
 * display ble message
 */
bool bBle_DisPlay(uint8_t ucIndex, uint8_t *ucStr) {
  uint8_t ucDelayFlag;
  oledClear();
  ucDelayFlag = 0x00;
  switch (ucIndex) {
    case BT_LINK:
      oledDrawStringCenter(60, 30, "Connect by Bluetooth", FONT_STANDARD);
      break;
    case BT_UNLINK:
      oledDrawStringCenter(60, 30, "BLE unLink", FONT_STANDARD);
      break;
    case BT_DISPIN:
      ucStr[BT_PAIR_LEN] = '\0';
      oledDrawStringCenter(60, 30, "BLE Pair Pin", FONT_STANDARD);
      oledDrawStringCenter(60, 50, (char *)ucStr, FONT_STANDARD);
      ucDelayFlag = 1;
      break;
    case BT_PINERROR:
      oledDrawStringCenter(60, 30, "Pair Pin Error", FONT_STANDARD);
      break;
    case BT_PINTIMEOUT:
      oledDrawStringCenter(60, 30, "Pair Pin Timeout", FONT_STANDARD);
      break;
    case BT_PAIRINGSCESS:
      oledDrawStringCenter(60, 30, "Pair Pin Success", FONT_STANDARD);
      break;
    case BT_PINCANCEL:
      oledDrawStringCenter(60, 30, "Pair Pin Cancel", FONT_STANDARD);
      break;

    default:
      break;
  }
  oledRefresh();
#if !EMULATOR
  uint8_t ucSw[4];
  ucSw[0] = 0x90;
  ucSw[1] = 0x00;
  vSI2CDRV_SendResponse(ucSw, 2);
#endif
  if (0x00 == ucDelayFlag) {
    delay_time(2000);
    return true;
  } else {
    return false;
  }
}

bool sys_nfcState(void) {
  if (get_nfc_state() == 0) {
    delay_time(1);
    if (get_nfc_state() == 0) {
      return true;
    }
  }
  return false;
}
bool sys_usbState(void) {
  if (get_usb_state()) {
    delay_time(1);
    if (get_usb_state()) {
      return true;
    }
  }
  return false;
}

void sys_shutdown(void) {
  oledClear();
  oledDrawStringCenter(64, 30, "power off ...", FONT_STANDARD);
  oledRefresh();
  delay_time(500);
  oledClear();
  oledRefresh();
  ble_power_off();
  stm32_power_off();
  scb_reset_system();
}

void sys_poweron(void) {
  uint32_t count = 0;

  while (1) {
    if (get_power_key_state()) {
      delay_time(100);
      count++;
      if (count > 5) {
        oledClear();
        oledDrawStringCenter(64, 30, "power on...", FONT_STANDARD);
        oledRefresh();
        while (get_power_key_state())
          ;
        break;
      }
    } else if (sys_nfcState() || sys_usbState())
      break;
  }
  stm32_power_on();
  ble_power_on();
}
