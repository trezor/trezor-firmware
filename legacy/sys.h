#ifndef _sys_H_
#define _sys_H_

#include <libopencm3/stm32/gpio.h>


#define BLE_ADV_NAME "Bixin_6666"
#define BLE_ADV_NAME_LEN 10

//APDU TAG
#define APDU_TAG_BLE            0x44
#define APDU_TAG_BLE_NFC        0x46
#define APDU_TAG_HANDSHAKE      0x55
//work mode
#define WORK_MODE_BLE	        0x10
#define WORK_MODE_USB		0x20
#define WORK_MODE_NFC		0x30
//power on/off
#define BUTTON_POWER_ON		0x10
#define BUTTON_POWER_OFF	0x20

#define GPIO_CMBUS_PORT  GPIOC

#define GPIO_USB_INSERT   GPIO8
#define GPIO_POWER_ON     GPIO4
#define GPIO_NFC_INSERT   GPIO5

#define GPIO_BUTTON_OK    GPIO0
#define GPIO_BUTTON_UP    GPIO1
#define GPIO_BUTTON_DOWN  GPIO2
#define GPIO_BUTTON_CANCEL GPIO3
#define GPIO_SI2C_CMBUS   GPIO9
#define GPIO_BLE_POWER    GPIO10

//combus io level
#define SET_COMBUS_HIGH() (gpio_set(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))
#define SET_COMBUS_LOW()  (gpio_clear(GPIO_CMBUS_PORT, GPIO_SI2C_CMBUS))

//usb 
#define GET_USB_INSERT()    (gpio_get(GPIOA, GPIO_USB_INSERT))
#define GET_NFC_INSERT()    (gpio_get(GPIOC, GPIO_NFC_INSERT))
#define GET_BUTTON_CANCEL() (gpio_get(GPIOC, GPIO_BUTTON_CANCEL))

//power control
#define POWER_ON()	        (gpio_set(GPIOC, GPIO_POWER_ON))
#define POWER_OFF()	        (gpio_clear(GPIOC, GPIO_POWER_ON))
//power on button
#define POWER_ON()	        (gpio_set(GPIOC, GPIO_POWER_ON))

//power control BLE
#define POWER_ON_BLE()	     (gpio_set(GPIOC, GPIO_BLE_POWER))
#define POWER_OFF_BLE()	     (gpio_clear(GPIOC, GPIO_BLE_POWER))
//power control Button status
#define POWER_BUTTON_UP   0
#define POWER_BUTTON_DOWN 1


extern uint8_t g_ucWorkMode;



void delay_time(uint32_t uiDelay_Ms);

void vCheckMode(void);
void vPower_Control(uint8_t ucMode);



#endif

