#include "mi2c.h"
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/i2c.h>
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/flash.h>

#include <string.h>
#include "sys.h"
#include "usart.h"
#include "secbool.h"
#include "rand.h"
#include "aes/aes.h"


const uint8_t SessionModeMode_ROMKEY[16] =
{
    0x80,0xBA,0x15,0x37,0xD2,0x84,0x8D,0x64,0xA7,0xB4,0x58,0xF4,0x58,0xFE,0xD8,0x84
};

const uint8_t ucDefaultSessionKey[16] =
{
	0x97,0x1e,0xaa,0x62,0xbf,0xb1,0xfe,0xb6,0x99,0x88,0x0a,0xb2,0xdb,0x59,0x88,0x59
};


uint8_t g_ucMI2cRevBuf[MI2C_BUF_MAX_LEN];
uint8_t g_ucMI2cSendBuf[MI2C_BUF_MAX_LEN];
uint8_t g_ucSessionKey[SESSION_KEYLEN];
uint16_t g_usMI2cRevLen;
uint8_t g_uchash_mode = 0;


static uint8_t ucXorCheck(uint8_t ucInputXor, uint8_t *pucSrc, uint16_t usLen) {
  uint16_t i;
  uint8_t ucXor;

  ucXor = ucInputXor;
  for (i = 0; i < usLen; i++) {
    ucXor ^= pucSrc[i];
  }
  return ucXor;
}

static bool bMI2CDRV_ReadBytes(uint32_t i2c, uint8_t *res,
                                  uint16_t *pusOutLen) {
  uint8_t ucLenBuf[2], ucXor;
  uint16_t i, usRevLen, usTimeout, usRealLen;

  ucXor = 0;
  i = 0;
  usRealLen = 0;
  usTimeout = 0;

  ucLenBuf[0] = 0x00;
  ucLenBuf[1] = 0x00;

  while (1) {
    if (i > 5) {
      return false;
    }
    while ((I2C_SR2(i2c) & I2C_SR2_BUSY)) {
    }

    i2c_send_start(i2c);
    i2c_enable_ack(i2c);
    while (!(I2C_SR1(i2c) & I2C_SR1_SB))
      ;
    i2c_send_7bit_address(i2c, MI2C_ADDR, MI2C_READ);

    // Waiting for address is transferred.
    while (!(I2C_SR1(i2c) & I2C_SR1_ADDR)) {
      usTimeout++;
      if (usTimeout > MI2C_TIMEOUT) {
        break;
      }
    }
    if (usTimeout > MI2C_TIMEOUT) {
      usTimeout = 0;
      i++;
      continue;
    }
    /* Clearing ADDR condition sequence. */
    (void)I2C_SR2(i2c);
    (void)I2C_SR1(I2C2);
    break;
  }
  // rev len
  for (i = 0; i < 2; i++) {
    while (!(I2C_SR1(i2c) & I2C_SR1_RxNE))
      ;
    ucLenBuf[i] = i2c_get_data(i2c);
  }
  // len + xor
  usRevLen = (ucLenBuf[0] << 8) + (ucLenBuf[1] & 0xFF) + MI2C_XOR_LEN;
  // cal len xor
  ucXor = ucXorCheck(ucXor, ucLenBuf, sizeof(ucLenBuf));
  // rev data
  for (i = 0; i < usRevLen; ++i) {
    if (i == usRevLen - 1) {
      i2c_disable_ack(i2c);
    }
    while (!(I2C_SR1(i2c) & I2C_SR1_RxNE))
      ;
    if (usRevLen < *pusOutLen) {
      res[i] = i2c_get_data(i2c);
      usRealLen++;
    } else {
      ucLenBuf[0] = i2c_get_data(i2c);
    }
  }
  i2c_send_stop(i2c);
  if (0x00 == usRealLen) {
     return false;
   }

  // cal data xor
  ucXor = ucXorCheck(ucXor, res, usRealLen - MI2C_XOR_LEN);
  if (ucXor != res[usRealLen - MI2C_XOR_LEN]) {
    return false;
  }
  usRealLen -= MI2C_XOR_LEN;

  if( (0x90 != res[usRealLen -2]) ||(0x00 != res[usRealLen -1]) ) {
    return false;
  }
  *pusOutLen = usRealLen - 2;
  return true;
}

static bool bMI2CDRV_WriteBytes(uint32_t i2c, uint8_t *data,
                                   uint16_t ucSendLen) {
  uint8_t ucLenBuf[2], ucXor = 0;
  uint16_t i, usTimeout = 0;

  i = 0;
  while (1) {
    if (i > 5) {
      return false;
    }
    i2c_send_start(i2c);
    while (!(I2C_SR1(i2c) & I2C_SR1_SB))
    {
      usTimeout++;
      if (usTimeout > MI2C_TIMEOUT) {
        break;
      }
    }

    i2c_send_7bit_address(i2c, MI2C_ADDR, MI2C_WRITE);

    // Waiting for address is transferred.
    while (!(I2C_SR1(i2c) & I2C_SR1_ADDR)) {
      usTimeout++;
      if (usTimeout > MI2C_TIMEOUT) {
        break;
      }
    }
    if (usTimeout > MI2C_TIMEOUT) {
      i++;
      usTimeout = 0;
      continue;
    }
    /* Clearing ADDR condition sequence. */
    (void)I2C_SR2(i2c);
    (void)I2C_SR1(I2C2);
    break;
  }
  // send L + V + xor
  ucLenBuf[0] = ((ucSendLen >> 8) & 0xFF);
  ucLenBuf[1] = ucSendLen & 0xFF;
  // len xor
  ucXor = ucXorCheck(ucXor, ucLenBuf, sizeof(ucLenBuf));
  // send len
  for (i = 0; i < 2; i++) {
    i2c_send_data(i2c, ucLenBuf[i]);
    usTimeout = 0;
    while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
    {
      usTimeout++;
      if (usTimeout > MI2C_TIMEOUT) {
        return false;
      }
    }
  }
  // cal xor
  ucXor = ucXorCheck(ucXor, data, ucSendLen);
  // send data
  for (i = 0; i < ucSendLen; i++) {
    i2c_send_data(i2c, data[i]);
   usTimeout = 0;
    while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
    {
      usTimeout++;
      if (usTimeout > MI2C_TIMEOUT) {
        return false;
      }
    }
      
  }
  // send Xor
  i2c_send_data(i2c, ucXor);
  usTimeout = 0;
  while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
  {
    usTimeout++;
    if (usTimeout > MI2C_TIMEOUT) {
      return false;
    }
  }


  i2c_send_stop(i2c);
//  delay_us(100);

  return true;
}

void vMI2CDRV_Init(void) {
  rcc_periph_clock_enable(RCC_I2C1);
  rcc_periph_clock_enable(RCC_GPIOB);

  i2c_reset(MI2CX);

  gpio_set_output_options(GPIO_MI2C_PORT, GPIO_OTYPE_OD, GPIO_OSPEED_50MHZ,
                          GPIO_MI2C_SCL | GPIO_MI2C_SDA);
  gpio_set_af(GPIO_MI2C_PORT, GPIO_AF4, GPIO_MI2C_SCL | GPIO_MI2C_SDA);
  gpio_mode_setup(GPIO_MI2C_PORT, GPIO_MODE_AF, GPIO_PUPD_NONE,
                  GPIO_MI2C_SCL | GPIO_MI2C_SDA);
  i2c_peripheral_disable(MI2CX);

  // combus
  // gpio_mode_setup(GPIO_MI2C_PORT, GPIO_MODE_INPUT, GPIO_PUPD_NONE,
  // MI2C_COMBUS);

  I2C_CR1(MI2CX) |= I2C_CR1_NOSTRETCH;
  I2C_CR1(MI2CX) |= I2C_CR1_ENGC;
  I2C_CR1(MI2CX) |= I2C_CR1_POS;
  // 100k
  i2c_set_speed(MI2CX, i2c_speed_sm_100k, 30);
  // i2c_set_speed(MI2CX, i2c_speed_sm_100k, 32);
  i2c_set_own_7bit_slave_address(MI2CX, MI2C_ADDR);
  i2c_peripheral_enable(MI2CX);
  POWER_ON_SE();
}


void randomBuf_SE(uint8_t *ucRandom,uint8_t ucLen)
{
    uint8_t ucRandomCmd[5] = {0x00,0x84,0x00,0x00,0x00},ucTempBuf[32];
    uint16_t usLen;
    
    ucRandomCmd[4] = ucLen;
    usLen = sizeof(ucTempBuf);
    if(false ==bMI2CDRV_SendData(ucRandomCmd,sizeof(ucRandomCmd)))
    {
      return;
    }
    if(true == bMI2CDRV_ReceiveData(ucTempBuf,&usLen ))
    {
        memcpy(ucRandom, ucTempBuf, ucLen);
    }

}


/*
 *master i2c rev
 */
bool bMI2CDRV_ReceiveData(uint8_t *pucStr, uint16_t *pusRevLen) {
  if (*pusRevLen < 3) {
    return false;
  }
  if (false == bMI2CDRV_ReadBytes(MI2CX, pucStr, pusRevLen)) {
    return false;
  }

  return true;
}
/*
 *master i2c send
 */
bool bMI2CDRV_SendData(uint8_t *pucStr, uint16_t usStrLen) {
  if (usStrLen > (MI2C_BUF_MAX_LEN - 3)) {
    usStrLen = MI2C_BUF_MAX_LEN - 3;
  }

  return bMI2CDRV_WriteBytes(MI2CX, pucStr, usStrLen);
}
void  random_buffer_ST(uint8_t *buf, size_t len) {
  uint32_t r = 0;
  for (size_t i = 0; i < len; i++) {
    if (i % 4 == 0) {
      r = random32();
    }
    buf[i] = (r >> ((i % 4) * 8)) & 0xFF;
  }
}

static void flash_enter(void) {
  flash_wait_for_last_operation();
  flash_clear_status_flags();
  flash_unlock();
}

static void flash_exit(void) {
  flash_wait_for_last_operation();
  flash_lock();
}

/*
 *master i2c synsessionkey
 */
void vMI2CDRV_SynSessionKey(void)
{
    uint8_t ucSessionMode,i;
    uint8_t ucRandom[16];
    uint32_t uiSessionFlag,uiSessionKeyTemp;
    
    uiSessionFlag = *( uint32_t *)(SESSION_FALG_ADDR);
    
    if (SESSION_FALG != uiSessionFlag )
    {
        //enable mode session
        ucSessionMode = 1;
        memcpy( g_ucSessionKey,( uint8_t *)SessionModeMode_ROMKEY,sizeof(SessionModeMode_ROMKEY));
        if ( MI2C_OK == MI2CDRV_Transmit(MI2C_CMD_WR_PIN,SESSION_FALG_INDEX,( uint8_t *) &ucSessionMode, 1,NULL,0,0x00,SET_SESTORE_DATA) )
        {
             random_buffer_ST(ucRandom,sizeof(ucRandom));
             memcpy( g_ucSessionKey,( uint8_t *)ucDefaultSessionKey,sizeof(ucDefaultSessionKey));
             if ( MI2C_OK == MI2CDRV_Transmit(MI2C_CMD_WR_PIN,SESSION_ADDR_INDEX,ucRandom, sizeof(ucRandom),NULL,0,0x00,SET_SESTORE_DATA) )
             {
                 memcpy( g_ucSessionKey,ucRandom,SESSION_KEYLEN);
                 flash_enter();
                 for ( i = 0; i < SESSION_KEYLEN / sizeof(uint32_t); i++)
                 {
                    uiSessionKeyTemp = (uint32_t)((g_ucSessionKey[i* sizeof(uint32_t)+3]<<24) + (g_ucSessionKey[i * sizeof(uint32_t)+2]<<16)+ (g_ucSessionKey[i * sizeof(uint32_t)+1]<<8)+ (g_ucSessionKey[i * sizeof(uint32_t)]));
                    flash_program_word(SESSION_ADDR + i * sizeof(uint32_t),uiSessionKeyTemp);
                 } 
                 uiSessionFlag = SESSION_FALG;
                 flash_program_word(SESSION_FALG_ADDR ,uiSessionFlag);
                 flash_exit();
             }
        }
    }
    else
    {
       for ( i = 0; i < SESSION_KEYLEN; i++)
       {
            g_ucSessionKey[i] = *( uint8_t *)(SESSION_ADDR+i);
       }
                
    }
    
}

/*
 *master i2c send
 */
uint32_t MI2CDRV_Transmit(uint8_t ucCmd,uint8_t ucIndex,uint8_t *pucSendData, uint16_t usSendLen,uint8_t *pucRevData,uint16_t *pusRevLen,uint8_t ucMode,uint8_t ucWRFlag)
{
    uint8_t ucRandom[16],i;
    uint16_t usPadLen;
    aes_encrypt_ctx ctxe;
    aes_decrypt_ctx ctxd;
    //se apdu
    if (MI2C_ENCRYPT == ucMode )
    {   
        if (SET_SESTORE_DATA == ucWRFlag )
        {
            //data aes encrypt 
            randomBuf_SE(ucRandom,sizeof(ucRandom));
            memset(&ctxe, 0, sizeof(aes_encrypt_ctx));
            aes_encrypt_key128(g_ucSessionKey,&ctxe);
            memcpy(SH_IOBUFFER, ucRandom, sizeof(ucRandom));
            memcpy(SH_IOBUFFER+sizeof(ucRandom), pucSendData, usSendLen);
            usSendLen += sizeof(ucRandom);
            //add pad 
            if(usSendLen%AES_BLOCK_SIZE)
            {
              usPadLen =  AES_BLOCK_SIZE - (usSendLen%AES_BLOCK_SIZE);
              memset(SH_IOBUFFER+usSendLen, 0x00, usPadLen);
              SH_IOBUFFER[usSendLen]=0x80;
              usSendLen += usPadLen;
            }
            vUART_DebugInfo("\n\r  vMI2CDRV_SendData encrypt!\n\r", SH_IOBUFFER, usSendLen);
            aes_ecb_encrypt(SH_IOBUFFER, g_ucMI2cRevBuf,usSendLen,&ctxe);
         }
         else
         {
            // data add random  
            random_buffer_ST(ucRandom,sizeof(ucRandom));
            usSendLen += sizeof(ucRandom);
            memcpy(g_ucMI2cRevBuf,ucRandom, sizeof(ucRandom));
            memcpy(g_ucMI2cRevBuf+sizeof(ucRandom), pucSendData, usSendLen);
         }

    }
    
    CLA = 0x80;
    INS = ucCmd;
    P1 = ucIndex;
    P2 = ucWRFlag |ucMode;
    if (usSendLen > 255)
    {
        P3 = 0x00;
        SH_IOBUFFER[0] = (usSendLen>>8)&0xFF;
        SH_IOBUFFER[1] = usSendLen&0xFF;
        if (usSendLen > (MI2C_BUF_MAX_LEN - 7))
        {
             return MI2C_ERROR;
        }
        if (MI2C_ENCRYPT == ucMode )
        {
            memcpy(SH_IOBUFFER+2, g_ucMI2cRevBuf, usSendLen);
        }
        else
        {
            memcpy(SH_IOBUFFER+2, pucSendData, usSendLen);  
        }
        
        usSendLen +=7;
    }
    else
    {
        P3 = usSendLen&0xFF;
        if (MI2C_ENCRYPT == ucMode )
        {
            memcpy(SH_IOBUFFER, g_ucMI2cRevBuf, usSendLen);
        }
        else
        {
            memcpy(SH_IOBUFFER, pucSendData, usSendLen);  
        }
        usSendLen +=5;
    }
    if(false ==bMI2CDRV_SendData(SH_CMDHEAD,usSendLen))
    {
       return MI2C_ERROR;
    }
    g_usMI2cRevLen = sizeof(g_ucMI2cRevBuf);
    if(false == bMI2CDRV_ReceiveData(g_ucMI2cRevBuf,&g_usMI2cRevLen))
    {
        return MI2C_ERROR;
    }
    if (MI2C_ENCRYPT == ucMode )
    {
      //aes dencrypt data 
      if ((GET_SESTORE_DATA == ucWRFlag ) &&(g_usMI2cRevLen  > 0 )&& ((g_usMI2cRevLen%16 == 0x00 ) )  )
      {
        memset(&ctxd, 0, sizeof(aes_decrypt_ctx));
        aes_decrypt_key128(g_ucSessionKey,&ctxd);
        aes_ecb_decrypt(g_ucMI2cRevBuf, SH_IOBUFFER, g_usMI2cRevLen, &ctxd);

        if (memcmp(SH_IOBUFFER, ucRandom,sizeof(ucRandom)) != 0) 
        {
            return MI2C_ERROR;
        }
        //delete pad
        for(i=1;i<0x11;i++)
        {
          if(SH_IOBUFFER[g_usMI2cRevLen-i]==0x80)
          {
            for(usPadLen=1;usPadLen<i;usPadLen++)
            {
              if(SH_IOBUFFER[g_usMI2cRevLen-usPadLen]!=0x00)
              {
                i=0x11;
                break;
              }

            }
            break;
          }
        }

        if(i!=0x11)
        {
          g_usMI2cRevLen=g_usMI2cRevLen-i;
        }
        g_usMI2cRevLen  -=sizeof(ucRandom);
        if (pucRevData != NULL)
        {
          vUART_DebugInfo("\n\r bMI2CDRV_ReceiveData decrypt!\n\r", SH_IOBUFFER+sizeof(ucRandom), g_usMI2cRevLen);
          memcpy(pucRevData, SH_IOBUFFER+sizeof(ucRandom), g_usMI2cRevLen);
          *pusRevLen =g_usMI2cRevLen;
          return MI2C_OK;
        }
      }
   }
   if (pucRevData != NULL) {
        memcpy(pucRevData, g_ucMI2cRevBuf, g_usMI2cRevLen);
        *pusRevLen =g_usMI2cRevLen;;
    }
   return MI2C_OK;
    
}

