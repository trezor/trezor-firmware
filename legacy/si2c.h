#ifndef _si2c_H_
#define _si2c_H_

#include <stdint.h>

#define I2C_TIMEOUT 400000
#define _SUPPORT_SOFTI2C_ 0
#define SI2C_BUF_MAX_LEN (1024 * 3)

// I2C gpio
#define GPIO_SI2C_PORT GPIOB

#define GPIO_SI2C_SCL GPIO10  // GPIO6//
#define GPIO_SI2C_SDA GPIO11  // GPIO7//

// I2C addr
#if (_SUPPORT_SOFTI2C_ > 0)
#define SI2C_ADDR 0x90
#else
#define SI2C_ADDR 0x48  // 90
#define SLAVE_READ 0x00
#define SLAVE_WRITE 0x01
#endif
// repeat tag
#define REPEAT_TAG 0x45
#define DATA_HEAD_LEN 0x03
#define CRC_LEN 0x02

#define SET_SDA_HIGH (gpio_set(GPIO_SI2C_PORT, GPIO_SI2C_SDA))
#define SET_SDA_LOW (gpio_clear(GPIO_SI2C_PORT, GPIO_SI2C_SDA))
#define GET_SDA_DAT (gpio_get(GPIO_SI2C_PORT, GPIO_SI2C_SDA))
#define GET_SCL_DAT (gpio_get(GPIO_SI2C_PORT, GPIO_SI2C_SCL))
#define SET_I2C_SDA_OUT()                                            \
  (gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, \
                   GPIO_SI2C_SDA))
#define SET_I2C_SDA_IN()                                              \
  (gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_INPUT, GPIO_PUPD_PULLUP, \
                   GPIO_SI2C_SDA))

extern uint8_t g_ucI2cRevBuf[SI2C_BUF_MAX_LEN];
extern uint16_t g_usI2cRevLen;

extern void vSI2CDRV_Init(void);

extern uint8_t bSI2CDRV_ReceiveData(uint8_t *pucStr);

extern void vSI2CDRV_SendResponse(uint8_t *pucStr, uint16_t usStrLen);

#endif
