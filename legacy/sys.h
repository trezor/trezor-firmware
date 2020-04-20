#ifndef _sys_H_
#define _sys_H_

#include <libopencm3/stm32/gpio.h>

#ifndef FEITIAN_PCB_V1_1
#define FEITIAN_PCB_V1_1 1
#endif

#if FEITIAN_PCB_V1_1
#define USB_INSERT_PORT GPIOC
#define USB_INSERT_PIN GPIO8

#define BLE_POWER_CTRL_PORT GPIOA
#define BLE_POWER_CTRL_PIN GPIO0

#define SE_POWER_PORT GPIOB
#define SE_POWER_PIN GPIO13
#else

#define SE_POWER_PORT GPIOC
#define SE_POWER_PIN GPIO8

#define USB_INSERT_PORT GPIOA
#define USB_INSERT_PIN GPIO15

#define BLE_POWER_CTRL_PORT GPIOA
#define BLE_POWER_CTRL_PIN GPIO2
#endif

#define NFC_SHOW_PORT GPIOC
#define NFC_SHOW_PIN GPIO1

#define BTN_POWER_PORT GPIOC
#define BTN_POWER_PIN GPIO0

#define STM32_POWER_CTRL_PORT GPIOC
#define STM32_POWER_CTRL_PIN GPIO4

#define BLE_CONNECT_PORT GPIOC
#define BLE_CONNECT_PIN GPIO11

#define stm32_power_on() gpio_set(STM32_POWER_CTRL_PORT, STM32_POWER_CTRL_PIN)
#define stm32_power_off() \
  gpio_clear(STM32_POWER_CTRL_PORT, STM32_POWER_CTRL_PIN)

#define ble_power_on() gpio_set(BLE_POWER_CTRL_PORT, BLE_POWER_CTRL_PIN)
#define ble_power_off() gpio_clear(BLE_POWER_CTRL_PORT, BLE_POWER_CTRL_PIN)

#define se_power_on() (gpio_set(SE_POWER_PORT, SE_POWER_PIN))
#define se_power_off() (gpio_clear(SE_POWER_PORT, SE_POWER_PIN))

#define get_nfc_state() gpio_get(NFC_SHOW_PORT, NFC_SHOW_PIN)
#define get_usb_state() gpio_get(USB_INSERT_PORT, USB_INSERT_PIN)
#define get_ble_state() gpio_get(BLE_CONNECT_PORT, BLE_CONNECT_PIN)
#define get_power_key_state() gpio_get(BTN_POWER_PORT, BTN_POWER_PIN)

bool sys_nfcState(void);
bool sys_usbState(void);
bool sys_bleState(void);
void sys_poweron(void);
void sys_shutdown(void);

// NFC Connected
#define NFC_LINK 0x09
// USB Connected
#define USB_LINK 0x08

// APDU TAG
#define APDU_TAG_BLE 0x44
#define APDU_TAG_BLE_NFC 0x46
#define APDU_TAG_BAT 0x47
#define APDU_TAG_HANDSHAKE 0x55

#define GPIO_CMBUS_PORT GPIOC
#define GPIO_SI2C_CMBUS GPIO9

// combus io level
#define SET_COMBUS_HIGH() (gpio_set(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))
#define SET_COMBUS_LOW() (gpio_clear(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))

extern uint8_t g_ucFlag;
extern uint8_t g_ucBatValue;
extern uint8_t battery_cap;
extern bool g_bBleTransMode;
extern bool g_bSelectSEFlag;
extern uint32_t g_uiFreePayFlag;

#endif
