#include "mi2c.h"
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/i2c.h>
#include <libopencm3/stm32/rcc.h>
#include <string.h>
#include "sys.h"
#include "usart.h"

uint8_t g_ucMI2cRevBuf[MI2C_BUF_MAX_LEN];
uint16_t g_usMI2cRevLen;

static uint8_t ucXorCheck(uint8_t ucInputXor, uint8_t *pucSrc, uint16_t usLen) {
  uint16_t i;
  uint8_t ucXor;

  ucXor = ucInputXor;
  for (i = 0; i < usLen; i++) {
    ucXor ^= pucSrc[i];
  }
  return ucXor;
}

static uint8_t bMI2CDRV_ReadBytes(uint32_t i2c, uint8_t *res,
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
    if (usRevLen <= *pusOutLen) {
      res[i] = i2c_get_data(i2c);
      usRealLen++;
    } else {
      ucLenBuf[0] = i2c_get_data(i2c);
    }
  }
  i2c_send_stop(i2c);
  // cal data xor
  ucXor = ucXorCheck(ucXor, res, usRealLen - MI2C_XOR_LEN);
  if (ucXor != res[usRealLen - MI2C_XOR_LEN]) {
    return false;
  }
  *pusOutLen = usRealLen - MI2C_XOR_LEN;
  return true;
}

static uint8_t bMI2CDRV_WriteBytes(uint32_t i2c, uint8_t *data,
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
      ;

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
    while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
      ;
  }
  // cal xor
  ucXor = ucXorCheck(ucXor, data, ucSendLen);
  // send data
  for (i = 0; i < ucSendLen; i++) {
    i2c_send_data(i2c, data[i]);
    while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
      ;
  }
  // send Xor
  i2c_send_data(i2c, ucXor);
  while (!(I2C_SR1(i2c) & (I2C_SR1_TxE)))
    ;

  i2c_send_stop(i2c);
  delay_us(100);

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

/*
 *master i2c rev
 */
uint8_t bMI2CDRV_ReceiveData(uint8_t *pucStr, uint16_t *pusRevLen) {
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
void vMI2CDRV_SendData(uint8_t *pucStr, uint16_t usStrLen) {
  if (usStrLen > (MI2C_BUF_MAX_LEN - 3)) {
    usStrLen = MI2C_BUF_MAX_LEN - 3;
  }

  bMI2CDRV_WriteBytes(MI2CX, pucStr, usStrLen);
}
