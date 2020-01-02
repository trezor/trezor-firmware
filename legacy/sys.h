#ifndef _sys_H_
#define _sys_H_

#include <libopencm3/stm32/gpio.h>
#include "buttons.h"

#define BLE_ADV_NAME "Bixin_6666"
#define BLE_ADV_NAME_LEN 10

// Ble display
#define BT_LINK 0x01          //蓝牙连接//Connect by Bluetooth
#define BT_UNLINK 0x02        //蓝牙断开连接指令
#define BT_DISPIN 0x03        //显示配对密码
#define BT_PINERROR 0x04      //配对密码错误
#define BT_PINTIMEOUT 0x05    //配对超时
#define BT_PAIRINGSCESS 0x06  //配对成功
#define BT_PINCANCEL 0x07     //取消配对请求

// prompt info display
#define DISP_NOT_ACTIVE 0x01  //未激活////Not Activated
#define DISP_TOUCHPH 0x02     //需与手机贴合//It needs to touch the phone
#define DISP_NFC_LINK 0x03    // NFC连接//Connect by NFC
#define DISP_USB_LINK 0x04    // USB连接//Connect by USB
#define DISP_COMPUTER_LINK 0x05  //与计算机连接//Connect to a computer
#define DISP_INPUTPIN \
  0x06  //按照右图提示输入PIN码//Enter PIN code according to the prompts on the
        // right screen
#define DISP_BUTTON_OK_RO_NO \
  0x07  //按下 OK 确认，按<取消//Press OK to confirm, Press < to Cancel
#define DISP_GEN_PRI_KEY 0x08  //正在生成私钥...//Generating private key…
#define DISP_ACTIVE_SUCCESS 0x09     //激活成功//Activated
#define DISP_BOTTON_UP_OR_DOWN 0x0A  //上下翻页查看//Turn up or down to view
#define DISP_SN 0x0B                 //序列号//Serial NO.
#define DISP_VERSION 0x0C            //固件版本//Firmware version
#define DISP_CONFIRM_PUB_KEY 0x0D    //确认公钥//Confirm public key
#define DISP_BOTTON_OK_SIGN 0x0E     //按下OK签名//Press OK to sign
#define DISP_SIGN_SUCCESS \
  0x0F  //签名成功！请与手机贴合//Signed! Touch it to the phone closely
#define DISP_SIGN_PRESS_OK_HOME \
  0x10  //签名完成！按OK返回首页//Signed! Press OK to return to homepage
#define DISP_SIGN_SUCCESS_VIEW \
  0x11  //签名成功！请在手机查看交易//Signed! Please view transaction on your
        // phone
#define DISP_UPDATGE_APP_GOING \
  0x12  //正在升级，请不要关机Upgrading, do not turn off
#define DISP_UPDATGE_SUCCESS \
  0x13  //固件升级成功，按OK返回首页//Firmware upgraded, press OK to return to
        // homepage
#define DISP_PRESSKEY_POWEROFF 0x14  //关机//power off
#define DISP_BLE_NAME 0x15           //蓝牙名称

// NFC 已连接
#define NFC_LINK 0x09
// USB 已连接
#define USB_LINK 0x08

//配对码的长度
#define BT_PAIR_LEN 0x06

// APDU TAG
#define APDU_TAG_BLE 0x44
#define APDU_TAG_BLE_NFC 0x46
#define APDU_TAG_HANDSHAKE 0x55
// work mode
#define WORK_MODE_BLE 0x10
#define WORK_MODE_USB 0x20
#define WORK_MODE_NFC 0x30
// power on/off
#define BUTTON_POWER_ON 0x10
#define BUTTON_POWER_OFF 0x20

#define GPIO_CMBUS_PORT GPIOC

#define GPIO_USB_INSERT GPIO8
#define GPIO_POWER_ON GPIO4

#if (OLD_PCB)
#define GPIO_NFC_INSERT GPIO5
#else
#define GPIO_NFC_INSERT GPIO1
#endif

/*#define GPIO_BUTTON_OK    GPIO0*/
/*#define GPIO_BUTTON_UP    GPIO1*/
/*#define GPIO_BUTTON_DOWN  GPIO2*/
/*#define GPIO_BUTTON_CANCEL GPIO3*/

#define GPIO_SI2C_CMBUS GPIO9
#define GPIO_BLE_POWER GPIO10

#if !EMULATOR
// combus io level
#define SET_COMBUS_HIGH() (gpio_set(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))
#define SET_COMBUS_LOW() (gpio_clear(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))

// usb
#define GET_USB_INSERT() (gpio_get(GPIOA, GPIO_USB_INSERT))
#define GET_NFC_INSERT() (gpio_get(GPIOC, GPIO_NFC_INSERT))
#define GET_BUTTON_CANCEL() (gpio_get(BTN_PORT, BTN_PIN_NO))

// power control
#define POWER_ON() (gpio_set(GPIOC, GPIO_POWER_ON))
#define POWER_OFF() (gpio_clear(GPIOC, GPIO_POWER_ON))
// power on button
#define POWER_ON() (gpio_set(GPIOC, GPIO_POWER_ON))

// power control BLE
#define POWER_ON_BLE() (gpio_set(GPIOC, GPIO_BLE_POWER))
#define POWER_OFF_BLE() (gpio_clear(GPIOC, GPIO_BLE_POWER))
#else
#define SET_COMBUS_HIGH()
#define SET_COMBUS_LOW()
#define GET_USB_INSERT() 1
#define GET_NFC_INSERT() 0
#define GET_BUTTON_CANCEL() 0
#define POWER_ON()
#define POWER_OFF()
#define POWER_ON_BLE()
#define POWER_OFF_BLE()
#endif

// power control Button status
#define POWER_BUTTON_UP 0
#define POWER_BUTTON_DOWN 1

extern uint8_t g_ucFlag;
extern uint8_t g_ucLanguageFlag;
extern uint8_t g_ucWorkMode;

#define POWER_OFF_ENBALE() (g_ucFlag |= 0x01)
#define POWER_OFF_CLEAR() (g_ucFlag &= 0xFE)
#define POWER_OFF_READY() (g_ucFlag & 0x01)

void delay_time(uint32_t uiDelay_Ms);
void delay_us(uint32_t uiDelay_us);
void vCheckMode(void);
void vPower_Control(uint8_t ucMode);
bool bBle_DisPlay(uint8_t ucIndex, uint8_t* ucStr);
void vDisp_PromptInfo(uint8_t ucIndex);
void vTransMode_DisPlay(void);

#endif
