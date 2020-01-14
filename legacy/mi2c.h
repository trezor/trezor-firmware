#ifndef _mi2c_H_
#define _mi2c_H_

#include <stdint.h>
#include "usart.h"

#define MI2C_TIMEOUT (40000)
#define MI2C_BUF_MAX_LEN (1024)
#define MI2C_XOR_LEN (1)

#define MI2C_TEST 0

#define MI2CX I2C1

// master I2C gpio
#define GPIO_MI2C_PORT GPIOB

//#define MI2C_COMBUS     GPIO2
#define GPIO_MI2C_SCL GPIO8
#define GPIO_MI2C_SDA GPIO9

// SE power IO
#define GPIO_SE_PORT GPIOC
#define GPIO_SE_POWER GPIO8

// power control SE
#define POWER_ON_SE() (gpio_set(GPIO_SE_PORT, GPIO_SE_POWER))
#define POWER_OFF_SE() (gpio_clear(GPIO_SE_PORT, GPIO_SE_POWER))

// master I2C addr
#define MI2C_ADDR 0x10
#define MI2C_READ 0x01
#define MI2C_WRITE 0x00

//#define	GET_MI2C_COMBUS	        (gpio_get(GPIO_MI2C_PORT, MI2C_COMBUS))

extern uint8_t g_ucMI2cRevBuf[MI2C_BUF_MAX_LEN];
extern uint16_t g_usMI2cRevLen;

extern void vMI2CDRV_Init(void);

extern uint8_t bMI2CDRV_ReceiveData(uint8_t *pucStr, uint16_t *pusRevLen);

extern void vMI2CDRV_SendData(uint8_t *pucStr, uint16_t usStrLen);
#endif
