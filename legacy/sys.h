#ifndef _sys_H_
#define _sys_H_

#include <libopencm3/stm32/gpio.h>
#include "buttons.h"
#include "usart.h"
#include "timer.h"
#include "oled.h"

#define  NORMAL_PCB    0

// Ble display
#define BT_LINK 0x01          //蓝牙连接//Connect by Bluetooth
#define BT_UNLINK 0x02        //蓝牙断开连接指令
#define BT_DISPIN 0x03        //显示配对密码
#define BT_PINERROR 0x04      //配对密码错误
#define BT_PINTIMEOUT 0x05    //配对超时
#define BT_PAIRINGSCESS 0x06  //配对成功
#define BT_PINCANCEL 0x07     //取消配对请求


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



#if (NORMAL_PCB)
#define GPIO_USB_INSERT   GPIO13
#else
#define GPIO_USB_INSERT   GPIO8
#endif

#define GPIO_NFC_INSERT GPIO1

/*#define GPIO_BUTTON_OK    GPIO0*/
/*#define GPIO_BUTTON_UP    GPIO1*/
/*#define GPIO_BUTTON_DOWN  GPIO2*/
/*#define GPIO_BUTTON_CANCEL GPIO3*/

#define GPIO_SI2C_CMBUS GPIO9
#if (NORMAL_PCB)
#define GPIO_BLE_POWER GPIO2
#else
#define GPIO_BLE_POWER GPIO10
#endif

#if !EMULATOR
// combus io level
#define SET_COMBUS_HIGH() (gpio_set(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))
#define SET_COMBUS_LOW() (gpio_clear(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))

// usb
#if (NORMAL_PCB)
#define GET_USB_INSERT() (gpio_get(GPIOC, GPIO_USB_INSERT))
#else
#define GET_USB_INSERT() (gpio_get(GPIOA, GPIO_USB_INSERT))
#endif
#define GET_NFC_INSERT() (gpio_get(GPIOC, GPIO_NFC_INSERT))
#define GET_BUTTON_CANCEL() (gpio_get(BTN_PORT, BTN_PIN_NO))


#if (NORMAL_PCB)
// power control BLE
#define POWER_ON_BLE() (gpio_set(GPIOA, GPIO_BLE_POWER))
#define POWER_OFF_BLE() (gpio_clear(GPIOA, GPIO_BLE_POWER))
#else
// power control BLE
#define POWER_ON_BLE() (gpio_set(GPIOC, GPIO_BLE_POWER))
#define POWER_OFF_BLE() (gpio_clear(GPIOC, GPIO_BLE_POWER))
#endif

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
extern uint8_t g_ucWorkMode;


//#define POWER_OFF_TIMER_ENBALE()    (g_ucFlag |= 0x01)
//#define POWER_OFF_TIMER_CLEAR()     (g_ucFlag &= 0xFE)
//#define POWER_OFF_TIMER_READY()     (g_ucFlag & 0x01)

#define BUTTON_CHECK_ENBALE()    (g_ucFlag |= 0x02)
#define BUTTON_CHECK_CLEAR()     (g_ucFlag &= 0xFD)
#define PBUTTON_CHECK_READY()    (g_ucFlag & 0x02)


void vCalu_BleName(uint8_t * pucMac,uint8_t * pucName);
void vCheckMode(void);
void vPower_Control(uint8_t ucMode);
bool bBle_DisPlay(uint8_t ucIndex,uint8_t * ucStr);
#endif
