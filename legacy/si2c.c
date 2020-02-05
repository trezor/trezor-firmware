#include "si2c.h"
#include <errno.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/rcc.h>
#include <stdio.h>
#include <string.h>
#include "sys.h"
#include "timer.h"
#include "usart.h"

#if (_SUPPORT_SOFTI2C_ == 0)
#include <libopencm3/stm32/i2c.h>
#endif

uint8_t g_ucI2cRevBuf[SI2C_BUF_MAX_LEN];
uint16_t g_usI2cRevLen;
static uint8_t s_ucSendDataBak[SI2C_BUF_MAX_LEN];
static uint16_t s_usSendLenBak;
static uint8_t s_usTagbak;

bool bCheckNFC(void) {
  if (g_ucWorkMode == WORK_MODE_NFC) {
    if (GET_NFC_INSERT()) {
      return false;
    }
  }
  return true;
}

#if (_SUPPORT_SOFTI2C_ > 0)
static bool bSI2CDRV_Send_Ack(void) {
  while (1) {
    if (0 == GET_SCL_DAT) break;
    if (false == bCheckNFC()) {
      return false;
    }
  }
  SET_I2C_SDA_OUT();
  SET_SDA_LOW;
  while (1) {
    if (GET_SCL_DAT) break;
    if (false == bCheckNFC()) {
      return false;
    }
  }
  return true;
}

static uint8_t ucSI2CDRV_Get_Addr(void) {
  uint8_t bitcount, iic_slv_addr = 0;
  /*	uint32_t i2c_usTimeout;*/
  /*	*/
  /*	i2c_usTimeout = 0;*/
  while (1) {
    if (GET_SCL_DAT) break;

    vPower_Control(BUTTON_POWER_OFF);
    if (PBUTTON_CHECK_READY()) {
      if (true == hasbutton()) {
        return 0xFF;
      }
    }
  }
  /*	i2c_usTimeout = 0;*/
  while (1) {
    if (0 == GET_SDA_DAT) break;
    vPower_Control(BUTTON_POWER_OFF);
    if (PBUTTON_CHECK_READY()) {
      if (true == hasbutton()) {
        return 0xFF;
      }
    }
  }
  for (bitcount = 0; bitcount < 8; bitcount++) {
    while (1) {
      if (0 == GET_SCL_DAT) break;
      if (false == bCheckNFC()) {
        return 0xFF;
      }
    }
    SET_I2C_SDA_IN();
    while (1) {
      if (GET_SCL_DAT) break;
      if (false == bCheckNFC()) {
        return 0xFF;
      }
    }
    iic_slv_addr <<= 1;
    if (GET_SDA_DAT)
      iic_slv_addr |= 0x01;
    else
      iic_slv_addr |= 0x00;
  }
  return iic_slv_addr;
}
static uint8_t bSI2CDRV_ReadBytes(uint8_t *buf, uint16_t n) {
  uint16_t i = 0;

  uint8_t recFinish = 0, bitcount, rxbyte = 0;
  uint16_t r0 = 0, r1 = 0;
  // wati addr
  while (SI2C_ADDR != ucSI2CDRV_Get_Addr()) {
    return false;
  }
  if (false == bSI2CDRV_Send_Ack()) {
    return false;
  }

  while (!recFinish) {
    for (bitcount = 0; bitcount < 8; bitcount++) {
      while (1) {
        if (0 == GET_SCL_DAT) break;
        if (false == bCheckNFC()) {
          return false;
        }
      }
      SET_I2C_SDA_IN();
      while (1) {
        if (GET_SCL_DAT) break;
        if (false == bCheckNFC()) {
          return false;
        }
      }
      // check STOP,clk:high;dat:low->high
      r0 = GET_SDA_DAT;
      while (1) {
        if (GET_SCL_DAT) {
          r1 = GET_SDA_DAT;
          if ((r0 == 0) && (r1 > 0)) {
            recFinish = 1;
            i = n;
            return true;
          }
        } else
          break;
      }
      rxbyte <<= 1;
      if (r1)
        rxbyte |= 0x01;
      else
        rxbyte |= 0x00;
    }
    if (false == bSI2CDRV_Send_Ack()) {
      return false;
    }
    buf[i] = rxbyte;
    i++;
  }
  return false;
}

static bool bSI2CDRV_WriteBytes(uint8_t *buf, uint16_t buf_len) {
  uint16_t i = 0;

  uint8_t txbyte, bitcount;
  if ((SI2C_ADDR + 1) != ucSI2CDRV_Get_Addr()) {
    memset(buf, 0x00, 3);
    return false;
  }
  if (false == bSI2CDRV_Send_Ack()) {
    return false;
  }

  for (i = 0; i < buf_len; i++) {
    txbyte = buf[i];
    for (bitcount = 0; bitcount < 8; bitcount++) {
      while (1) {
        if (0 == GET_SCL_DAT) break;
        if (false == bCheckNFC()) {
          return false;
        }
      }
      SET_I2C_SDA_OUT();
      if (txbyte & 0x80)
        SET_SDA_HIGH;
      else
        SET_SDA_LOW;

      txbyte <<= 1;
      while (1) {
        if (GET_SCL_DAT) break;
        if (false == bCheckNFC()) {
          return false;
        }
      }
    }

    while (1) {
      if (0 == GET_SCL_DAT) break;
      if (false == bCheckNFC()) {
        return false;
      }
    }
    SET_I2C_SDA_IN();
    while (1) {
      if (GET_SCL_DAT) break;
      if (false == bCheckNFC()) {
        return false;
      }
    }
    if ((buf_len - 1) == i) {
      if (GET_SDA_DAT) {
        // wait stop
        while (1) {
          if (0 == GET_SCL_DAT) break;
          if (false == bCheckNFC()) {
            return false;
          }
        }
        while (1) {
          if (GET_SCL_DAT) break;
          if (false == bCheckNFC()) {
            return false;
          }
        }
        while (1) {
          if (GET_SDA_DAT) break;
          if (false == bCheckNFC()) {
            return false;
          }
        }
      }
    } else {
      if (GET_SDA_DAT) {
        break;
      }
    }
  }
  return true;
}

#else
static uint8_t bSI2CDRV_ReadBytes(uint8_t *res, uint16_t n) {
  uint16_t i;
  i2c_enable_ack(I2C2);
  i2c_send_7bit_address(I2C2, SI2C_ADDR, SLAVE_READ);
  // Waiting for address is transferred.
  while (!((I2C_SR1(I2C2) & I2C_SR1_ADDR))) {
    vPower_Control(BUTTON_POWER_OFF);
    if (PBUTTON_CHECK_READY()) {
      if (true == hasbutton()) {
        return false;
      }
    }
  }
  /* Clearing ADDR condition sequence. */
  (void)I2C_SR2(I2C2);
  (void)I2C_SR1(I2C2);

  for (i = 0; i < (n - 1); ++i) {
    while (!(I2C_SR1(I2C2) & I2C_SR1_RxNE)) {
      if (false == bCheckNFC()) {
        return false;
      }
    }
    res[i] = i2c_get_data(I2C2);
  }
  i2c_disable_ack(I2C2);
  while (!(I2C_SR1(I2C2) & I2C_SR1_RxNE)) {
    if (false == bCheckNFC()) {
      return false;
    }
  }
  res[i] = i2c_get_data(I2C2);
  while (!(I2C_SR1(I2C2) & I2C_SR1_STOPF)) {
    if (false == bCheckNFC()) {
      return false;
    }
  }

  i2c_send_stop(I2C2);
  (void)I2C_SR1(I2C2);
  vSI2CDRV_Init();
  return true;
}

static uint8_t bSI2CDRV_WriteBytes(uint8_t *data, uint16_t n) {
  uint16_t i;

  i2c_enable_ack(I2C2);
  i2c_send_7bit_address(I2C2, SI2C_ADDR, SLAVE_WRITE);
  /* Waiting for address is transferred. */
  while (!((I2C_SR1(I2C2) & I2C_SR1_ADDR))) {
    vPower_Control(BUTTON_POWER_OFF);
    if (PBUTTON_CHECK_READY()) {
      if (true == hasbutton()) {
        return false;
      }
    }
  }
  /* Clearing ADDR condition sequence. */
  (void)I2C_SR2(I2C2);
  (void)I2C_SR1(I2C2);
  for (i = 0; i < n - 1; i++) {
    i2c_send_data(I2C2, data[i]);
    while (!(I2C_SR1(I2C2) & I2C_SR1_TxE)) {
      if (false == bCheckNFC()) {
        return false;
      }
    }
  }
  i2c_disable_ack(I2C2);
  i2c_send_data(I2C2, data[i]);
  while (!(I2C_SR1(I2C2) & I2C_SR1_TxE)) {
    if (false == bCheckNFC()) {
      return false;
    }
  }
  delay_us(200);
  i2c_send_stop(I2C2);
  vSI2CDRV_Init();
  return true;
}
#endif

#if (_SUPPORT_SOFTI2C_ > 0)

void vSI2CDRV_Init(void) {
  rcc_periph_clock_enable(RCC_GPIOB);
  rcc_periph_clock_enable(RCC_GPIOC);
  gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_INPUT, GPIO_PUPD_PULLUP,
                  GPIO_SI2C_SDA);
  gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_INPUT, GPIO_PUPD_PULLUP,
                  GPIO_SI2C_SCL);
  memset(s_ucSendDataBak, 0x00, SI2C_BUF_MAX_LEN);
  s_usSendLenBak = 0;
}

#else
void vSI2CDRV_Init(void) {
  rcc_periph_clock_enable(RCC_I2C2);
  rcc_periph_clock_enable(RCC_GPIOB);

  i2c_reset(I2C2);

  gpio_set_output_options(GPIO_SI2C_PORT, GPIO_OTYPE_OD, GPIO_OSPEED_50MHZ,
                          GPIO_SI2C_SCL | GPIO_SI2C_SDA);
  gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_AF, GPIO_PUPD_NONE,
                  GPIO_SI2C_SCL | GPIO_SI2C_SDA);
  gpio_set_af(GPIO_SI2C_PORT, GPIO_AF4, GPIO_SI2C_SCL | GPIO_SI2C_SDA);
  i2c_peripheral_disable(I2C2);
  I2C_CR1(I2C2) &= ~I2C_CR1_NOSTRETCH;
  I2C_CR1(I2C2) |= I2C_CR1_NOSTRETCH;
  I2C_CR1(I2C2) |= I2C_CR1_ENGC;
  I2C_CR1(I2C2) |= I2C_CR1_POS;
  /*	//HSI is at 2Mhz */
  i2c_set_speed(I2C2, i2c_speed_sm_100k, 32);
  /*	//addressing mode*/
  i2c_set_own_7bit_slave_address(I2C2, SI2C_ADDR);
  i2c_peripheral_enable(I2C2);
  // i2c_enable_ack(I2C2);
  memset(s_ucSendDataBak, 0x00, SI2C_BUF_MAX_LEN);
  s_usSendLenBak = 0;
}
#endif

static void UpdateConnectLessCrc(uint8_t input, uint16_t *crc) {
  input = (input ^ (uint8_t)((*crc) & 0x00FF));
  input = (input ^ (input << 4));

  *crc = (*crc >> 8) ^ ((uint16_t)input << 8) ^ ((uint16_t)input << 3) ^
         ((uint16_t)input >> 4);
}

static uint16_t ConnectLessCrc(uint16_t icv, uint8_t *input, uint16_t length) {
  uint8_t p;
  uint16_t crc;

  crc = icv;

  while (length) {
    p = *((uint8_t *)input++);
    UpdateConnectLessCrc(p, &crc);
    length--;
  }

  if (0xffff == icv || 0x00 == icv) {
    crc = ~crc;
  }

  return crc;
}

/*
 *i2c rev
 */
uint8_t bSI2CDRV_ReceiveData(uint8_t *pucStr) {
  uint8_t i, ucBuf[3];
  uint16_t usLen, usCrc, usRevCrc;

  i = 0;

  while (i < 3) {
    if (false == bSI2CDRV_ReadBytes(pucStr, 3)) {
      return false;
    }
    // tlv tag + len + v
    usLen = (pucStr[1] << 8) + (pucStr[2] & 0xFF);
    if (usLen > (SI2C_BUF_MAX_LEN - DATA_HEAD_LEN)) {
      usLen = SI2C_BUF_MAX_LEN - DATA_HEAD_LEN;
    }
    if (usLen > 0) {
      SET_COMBUS_HIGH();
      // rev Data Remaining
      if (false == bSI2CDRV_ReadBytes(pucStr + 3, usLen)) {
        SET_COMBUS_LOW();
        return false;
      }
      // Compare checksums
      usCrc = ConnectLessCrc(0, pucStr + 3, usLen - CRC_LEN);
      usRevCrc = (pucStr[3 + usLen - CRC_LEN] << 8) +
                 (pucStr[3 + usLen - CRC_LEN + 1] & 0xFF);
      if (usCrc != usRevCrc) {
        SET_COMBUS_LOW();
        i++;
        ucBuf[0] = REPEAT_TAG;
        ucBuf[1] = 0x00;
        ucBuf[2] = 0x00;
        if (false == bSI2CDRV_WriteBytes(ucBuf, 3)) {
          return false;
        }
        continue;
      } else {
        s_usTagbak = pucStr[0];
        POWER_OFF_TIMER_CLEAR();
        system_millis_poweroff_start = 0;
        return true;
      }

    } else {
      if ((REPEAT_TAG == pucStr[0]) && (0x00 == pucStr[1]) &&
          (0x00 == pucStr[2])) {
        SET_COMBUS_LOW();
        if (false == bSI2CDRV_WriteBytes(s_ucSendDataBak, DATA_HEAD_LEN)) {
          return false;
        }
        if (false == bSI2CDRV_WriteBytes(s_ucSendDataBak + DATA_HEAD_LEN,
                                         s_usSendLenBak)) {
          return false;
        }
        continue;
      }
    }
  }

  return false;
}
/*
 *i2c send
 */
void vSI2CDRV_SendResponse(uint8_t *pucStr, uint16_t usStrLen) {
  uint16_t usCrc;
  uint8_t ucHead[DATA_HEAD_LEN];

  SET_COMBUS_LOW();

  if (usStrLen > (SI2C_BUF_MAX_LEN - DATA_HEAD_LEN)) {
    usStrLen = SI2C_BUF_MAX_LEN - DATA_HEAD_LEN;
  }

  // send head
  ucHead[0] = s_usTagbak;
  ucHead[1] = ((usStrLen + CRC_LEN) >> 8) & 0xFF;
  ucHead[2] = (usStrLen + CRC_LEN) & 0xFF;
  memcpy(s_ucSendDataBak, ucHead, DATA_HEAD_LEN);
  if (false == bSI2CDRV_WriteBytes(ucHead, DATA_HEAD_LEN)) {
    POWER_OFF_TIMER_ENBALE();
    system_millis_poweroff_start = 0;
    return;
  }
  // send data
  usCrc = ConnectLessCrc(0, pucStr, usStrLen);
  pucStr[usStrLen] = (usCrc >> 8) & 0xFF;
  pucStr[usStrLen + 1] = usCrc & 0xFF;
  usStrLen += CRC_LEN;
  memcpy(s_ucSendDataBak + DATA_HEAD_LEN, pucStr, usStrLen);
  s_usSendLenBak = usStrLen;
  bSI2CDRV_WriteBytes(pucStr, usStrLen);
  POWER_OFF_TIMER_ENBALE();
  system_millis_poweroff_start = 0;
}
