
#include "sys.h"
#include <libopencm3/stm32/gpio.h>
#include <string.h>
#include "bitmaps.h"
#include "si2c.h"

uint8_t g_ucWorkMode = 0;
uint8_t g_ucFlag = 0;
uint8_t g_ucBatValue = 0;

uint8_t g_ucLanguageFlag = 0;
uint8_t g_ucPromptIndex = 0;

/*poweroff */
volatile uint32_t system_millis_poweroff_start;

/*
 * delay time
 */
void delay_time(uint32_t uiDelay_Ms) {
  uint32_t uiTimeout = uiDelay_Ms * 30000;
  while (uiTimeout--) {
    __asm__("nop");
  }
}
void delay_us(uint32_t uiDelay_us) {
  uint32_t uiTimeout = uiDelay_us * 30;
  while (uiTimeout--) {
    __asm__("nop");
  }
}

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
