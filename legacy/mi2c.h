#ifndef _mi2c_H_
#define _mi2c_H_

#include <stdint.h>
#include <string.h>

#include "usart.h"
#include "sys.h"


#define MI2C_TIMEOUT (40000)
#define MI2C_BUF_MAX_LEN (1024+512)
#define MI2C_SEND_MAX_LEN (1024+512)

#define MI2C_XOR_LEN (1)
#define SESSION_KEYLEN (16)

//session key addr
#define SESSION_FALG         (0x55AA55AA)
#define SESSION_FALG_ADDR    (0x80E0000)
#define SESSION_ADDR         (0x80E0004)

#define BOOTLOAD_ADDR        (SESSION_ADDR + SESSION_KEYLEN)


//
#define SESSION_FALG_INDEX    (0x80)
#define SESSION_ADDR_INDEX    (0x81)


#define LITTLE_REVERSE32(w,x)	{ \
	uint32_t tmp = (w); \
	tmp = (tmp >> 16) | (tmp << 16); \
	(x) = ((tmp & 0xff00ff00UL) >> 8) | ((tmp & 0x00ff00ffUL) << 8); \
}


#define MI2C_OK     0xAAAAAAAAU
#define MI2C_ERROR  0x00000000U

#define MI2C_ENCRYPT 0x00
#define MI2C_PLAIN  0x80


#define GET_SESTORE_DATA        (0x00)   
#define SET_SESTORE_DATA        (0x01)   
#define DELETE_SESTORE_DATA     (0x02)   


#define MI2C_CMD_WR_PIN          (0xE1)   
#define MI2C_CMD_AES             (0xE2)   
#define MI2C_CMD_ECC_EDDSA       (0xE3)   


//ecc ed2519 index
#define ECC_INDEX_GITPUBKEY         (0x00)   
#define ECC_INDEX_SIGN              (0x01)   
#define ECC_INDEX_VERIFY            (0x02)   
#define EDDSA_INDEX_GITPUBKEY       (0x03)   
#define EDDSA_INDEX_SIGN            (0x04)   
#define EDDSA_INDEX_VERIFY          (0x05)   
#define EDDSA_INDEX_CHILDKEY        (0x06)   


//mnemonic index
#define MNEMONIC_INDEX_TOSEED       (26)   




#define MI2CX I2C1

// master I2C gpio
#define GPIO_MI2C_PORT GPIOB

//#define MI2C_COMBUS     GPIO2
#define GPIO_MI2C_SCL GPIO8
#define GPIO_MI2C_SDA GPIO9

#if (NORMAL_PCB)
// SE power IO
#define GPIO_SE_PORT GPIOB
#define GPIO_SE_POWER GPIO13
#else

// SE power IO
#define GPIO_SE_PORT GPIOC
#define GPIO_SE_POWER GPIO8

#endif

// power control SE
#define POWER_ON_SE() (gpio_set(GPIO_SE_PORT, GPIO_SE_POWER))
#define POWER_OFF_SE() (gpio_clear(GPIO_SE_PORT, GPIO_SE_POWER))

// master I2C addr
#define MI2C_ADDR 0x10
#define MI2C_READ 0x01
#define MI2C_WRITE 0x00

//#define	GET_MI2C_COMBUS	        (gpio_get(GPIO_MI2C_PORT, MI2C_COMBUS))

extern uint8_t g_ucMI2cRevBuf[MI2C_BUF_MAX_LEN];
extern uint8_t g_ucMI2cSendBuf[MI2C_BUF_MAX_LEN];
extern uint8_t g_ucSessionKey[SESSION_KEYLEN];

extern uint16_t g_usMI2cRevLen;
extern uint8_t g_uchash_mode;


#define CLA     (g_ucMI2cSendBuf[0])
#define INS     (g_ucMI2cSendBuf[1])
#define P1      (g_ucMI2cSendBuf[2])
#define P2      (g_ucMI2cSendBuf[3])
#define P3      (g_ucMI2cSendBuf[4])

#define SH_IOBUFFER      (g_ucMI2cSendBuf + 5)
#define SH_CMDHEAD       (g_ucMI2cSendBuf)






extern void vMI2CDRV_Init(void);

extern bool bMI2CDRV_ReceiveData(uint8_t *pucStr, uint16_t *pusRevLen);

extern bool bMI2CDRV_SendData(uint8_t *pucStr, uint16_t usStrLen);
extern void vMI2CDRV_SynSessionKey(void);
extern uint32_t MI2CDRV_Transmit(uint8_t ucCmd,uint8_t ucIndex,uint8_t *pucSendData, uint16_t usSendLen,uint8_t *pucRevData,uint16_t *pusRevLen,uint8_t ucMode,uint8_t ucWRFlag);

#endif
