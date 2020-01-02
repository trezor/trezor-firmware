
#include "sys.h"
#include <libopencm3/stm32/gpio.h>
#include "bitmaps.h"
#include "oled.h"
#include "prompt.h"
#include "si2c.h"

uint8_t g_ucWorkMode = 0;
uint8_t g_ucFlag = 0;
uint8_t g_ucLanguageFlag = 0;
uint8_t s_usPower_Button_Status = POWER_BUTTON_UP;

#if !EMULATOR
extern void check_lock_screen(void);
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

void vTransMode_DisPlay(void) {
  oledClear();
  if (WORK_MODE_BLE == g_ucWorkMode) {
    oledDrawBitmap(0, 0, &bmp_ble);
  } else if (WORK_MODE_USB == g_ucWorkMode) {
    oledDrawBitmap(0, 0, &bmp_usb);
  } else if (WORK_MODE_NFC == g_ucWorkMode) {
    oledDrawBitmap(0, 0, &bmp_nfc);
  } else {
    oledDrawBitmap(0, 0, &bmp_ble);
    oledDrawBitmap(0, 16, &bmp_logo);
    oledDrawBitmap(0, 48, &bmp_cn_unactive);
  }
  oledRefresh();
  delay_time(10000);
}

/*
 * display ble message
 */
bool bBle_DisPlay(uint8_t ucIndex, uint8_t *ucStr) {
  uint8_t ucSw[4], ucDelayFalg;
  oledClear();
  ucDelayFalg = 0x00;
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
      ucDelayFalg = 1;
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
  ucSw[0] = 0x90;
  ucSw[1] = 0x00;
  vSI2CDRV_SendResponse(ucSw, 2);
  if (0x00 == ucDelayFalg) {
    delay_time(2000);
    return true;
  } else {
    return false;
  }
}
/*
 * display prompt info
 */
void vDisp_PromptInfo(uint8_t ucIndex) {
  // oledClear();
  // g_ucLanguageFlag = 1;
  switch (ucIndex) {
    case DISP_NOT_ACTIVE:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_unactive);
      } else {
        oledDrawStringCenter(60, 48, "Not Activated", FONT_STANDARD);
      }
      break;
    case DISP_TOUCHPH:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_touch_phone);
      } else {
        oledDrawStringCenter(60, 48, "It needs to", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "touch the phone", FONT_STANDARD);
      }
      break;
    case DISP_NFC_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_nfc_link);
      } else {
        oledDrawStringCenter(60, 48, "Connect by NFC", FONT_STANDARD);
      }
      break;
    case DISP_USB_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_usb_link);
      } else {
        oledDrawStringCenter(60, 48, "Connect by USB", FONT_STANDARD);
      }
      break;
    case DISP_COMPUTER_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_computerlink);
      } else {
        oledDrawStringCenter(0, 48, "Connect to a computer", FONT_STANDARD);
      }
      break;
    case DISP_INPUTPIN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_input_pin);
      } else {
        oledDrawStringCenter(0, 48, "Enter PIN code according ", FONT_STANDARD);
        oledDrawStringCenter(0, 56, "to the prompts on the right screen",
                             FONT_STANDARD);
      }
      break;
    case DISP_BUTTON_OK_RO_NO:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_button_yes_no);
      } else {
        oledDrawStringCenter(60, 48, "Press OK to confirm, ", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "Press < to Cancel", FONT_STANDARD);
      }
      break;
    case DISP_GEN_PRI_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_prikey_gen);
      } else {
        oledDrawStringCenter(60, 48, "Generating private key…", FONT_STANDARD);
      }
      break;
    case DISP_ACTIVE_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_active_success);
      } else {
        oledDrawStringCenter(60, 48, "Activated", FONT_STANDARD);
      }
      break;
    case DISP_BOTTON_UP_OR_DOWN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_updown_view);
      } else {
        oledDrawStringCenter(60, 30, "Turn up or down to view", FONT_STANDARD);
      }
      break;
    case DISP_SN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sn);
      } else {
        oledDrawStringCenter(60, 48, "Serial NO.", FONT_STANDARD);
      }
      break;
    case DISP_VERSION:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_version);
      } else {
        oledDrawStringCenter(60, 48, "Firmware version", FONT_STANDARD);
      }
      break;
    case DISP_CONFIRM_PUB_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_confirm_pubkey);
      } else {
        oledDrawStringCenter(60, 48, "Confirm public key", FONT_STANDARD);
      }
      break;
    case DISP_BOTTON_OK_SIGN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sign_ok);
      } else {
        oledDrawStringCenter(60, 48, "Press OK to sign", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sign_success_phone);
      } else {
        oledDrawStringCenter(0, 48, "Signed! Touch it to", FONT_STANDARD);
        oledDrawStringCenter(0, 56, "the phone closely", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_PRESS_OK_HOME:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sign_success_gohome);
      } else {
        oledDrawStringCenter(0, 48, "Signed! Press OK to", FONT_STANDARD);
        oledDrawStringCenter(0, 56, "return to homepage", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_SUCCESS_VIEW:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sign_ok_view);
      } else {
        oledDrawStringCenter(0, 48, "Signed! Please view ", FONT_STANDARD);
        oledDrawStringCenter(0, 56, "transaction on your phone", FONT_STANDARD);
      }
      break;
    case DISP_UPDATGE_APP_GOING:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_nfc_link);
      } else {
        oledDrawStringCenter(0, 48, "Upgrading, do not turn off",
                             FONT_STANDARD);
      }
      break;
    case DISP_UPDATGE_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_update_sucess);
      } else {
        oledDrawStringCenter(0, 48, "Firmware upgraded,", FONT_STANDARD);
        oledDrawStringCenter(0, 56, "press OK to return to homepage",
                             FONT_STANDARD);
      }
      break;
    case DISP_PRESSKEY_POWEROFF:
      oledClear();
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 0, &bmp_cn_poweroff);
      } else {
        oledDrawStringCenter(60, 30, "Power Off", FONT_STANDARD);
      }
      oledRefresh();
      delay_time(2000);
      return;
    case DISP_BLE_NAME:
      oledDrawStringCenter(60, 56, BLE_ADV_NAME, FONT_STANDARD);
      break;
    default:
      break;
  }
  //   oledRefresh();
}
/*
 * battery power on/off
 */
void vPower_Control(uint8_t ucMode) {
  uint32_t uiCount = 0;

  if (BUTTON_POWER_ON == ucMode) {
    while (1) {
      if (GET_BUTTON_CANCEL()) {
        delay_time(10);
        uiCount++;
        if (uiCount > 150) {
          POWER_ON();
          g_ucWorkMode = WORK_MODE_BLE;
          s_usPower_Button_Status = POWER_BUTTON_DOWN;
          break;
        }

      } else {
        delay_time(2);
        if (0x00 == GET_BUTTON_CANCEL()) {
          POWER_OFF();
          while (1)
            ;
        }
      }
    }

  } else {
    if ((WORK_MODE_USB != g_ucWorkMode) && (GET_BUTTON_CANCEL())) {
      // no usb and button down and no nfc
      if ((0x00 == GET_USB_INSERT()) &&
          (POWER_BUTTON_UP == s_usPower_Button_Status) && (GET_NFC_INSERT())) {
        while (GET_BUTTON_CANCEL()) {
          delay_time(10);
          uiCount++;
          if (uiCount > 150) {
            vDisp_PromptInfo(DISP_PRESSKEY_POWEROFF);
            POWER_OFF();
            while (1)
              ;
          }
        }
      }
    } else {
      s_usPower_Button_Status = POWER_BUTTON_UP;
    }
    check_lock_screen();
  }
}

/*
 * check usb/nfc/ble
 */
void vCheckMode(void) {
  g_ucWorkMode = 0;

  // nfc mode
  if (0x00 == GET_NFC_INSERT()) {
    delay_time(2);
    if (0x00 == GET_NFC_INSERT()) {
      g_ucWorkMode = WORK_MODE_NFC;
      POWER_ON();
      return;
    }
  } else {
    // usb mode
    if (GET_USB_INSERT()) {
      delay_time(2);
      if (GET_USB_INSERT()) {
        g_ucWorkMode = WORK_MODE_USB;
        POWER_OFF_BLE();
        return;
      }
    } else {
      // 2s power on
      vPower_Control(BUTTON_POWER_ON);
    }
  }
}
#endif