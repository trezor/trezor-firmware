/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include STM32_HAL_H
#include TREZOR_BOARD

#include <string.h>

#include "common.h"
#include "secbool.h"

#include "i2c.h"
#include "stmpe811.h"
#include "touch.h"

/* Chip IDs */
#define STMPE811_ID 0x0811

/* Identification registers & System Control */
#define STMPE811_REG_CHP_ID_LSB 0x00
#define STMPE811_REG_CHP_ID_MSB 0x01
#define STMPE811_REG_ID_VER 0x02

/* Global interrupt Enable bit */
#define STMPE811_GIT_EN 0x01

/* IO expander functionalities */
#define STMPE811_ADC_FCT 0x01
#define STMPE811_TS_FCT 0x02
#define STMPE811_IO_FCT 0x04
#define STMPE811_TEMPSENS_FCT 0x08

/* Global Interrupts definitions */
#define STMPE811_GIT_IO 0x80    /* IO interrupt                   */
#define STMPE811_GIT_ADC 0x40   /* ADC interrupt                  */
#define STMPE811_GIT_TEMP 0x20  /* Not implemented                */
#define STMPE811_GIT_FE 0x10    /* FIFO empty interrupt           */
#define STMPE811_GIT_FF 0x08    /* FIFO full interrupt            */
#define STMPE811_GIT_FOV 0x04   /* FIFO overflowed interrupt      */
#define STMPE811_GIT_FTH 0x02   /* FIFO above threshold interrupt */
#define STMPE811_GIT_TOUCH 0x01 /* Touch is detected interrupt    */
#define STMPE811_ALL_GIT 0x1F   /* All global interrupts          */
#define STMPE811_TS_IT                                        \
  (STMPE811_GIT_TOUCH | STMPE811_GIT_FTH | STMPE811_GIT_FOV | \
   STMPE811_GIT_FF | STMPE811_GIT_FE) /* Touch screen interrupts */

/* General Control Registers */
#define STMPE811_REG_SYS_CTRL1 0x03
#define STMPE811_REG_SYS_CTRL2 0x04
#define STMPE811_REG_SPI_CFG 0x08

/* Interrupt system Registers */
#define STMPE811_REG_INT_CTRL 0x09
#define STMPE811_REG_INT_EN 0x0A
#define STMPE811_REG_INT_STA 0x0B
#define STMPE811_REG_IO_INT_EN 0x0C
#define STMPE811_REG_IO_INT_STA 0x0D

/* IO Registers */
#define STMPE811_REG_IO_SET_PIN 0x10
#define STMPE811_REG_IO_CLR_PIN 0x11
#define STMPE811_REG_IO_MP_STA 0x12
#define STMPE811_REG_IO_DIR 0x13
#define STMPE811_REG_IO_ED 0x14
#define STMPE811_REG_IO_RE 0x15
#define STMPE811_REG_IO_FE 0x16
#define STMPE811_REG_IO_AF 0x17

/* ADC Registers */
#define STMPE811_REG_ADC_INT_EN 0x0E
#define STMPE811_REG_ADC_INT_STA 0x0F
#define STMPE811_REG_ADC_CTRL1 0x20
#define STMPE811_REG_ADC_CTRL2 0x21
#define STMPE811_REG_ADC_CAPT 0x22
#define STMPE811_REG_ADC_DATA_CH0 0x30
#define STMPE811_REG_ADC_DATA_CH1 0x32
#define STMPE811_REG_ADC_DATA_CH2 0x34
#define STMPE811_REG_ADC_DATA_CH3 0x36
#define STMPE811_REG_ADC_DATA_CH4 0x38
#define STMPE811_REG_ADC_DATA_CH5 0x3A
#define STMPE811_REG_ADC_DATA_CH6 0x3B
#define STMPE811_REG_ADC_DATA_CH7 0x3C

/* Touch Screen Registers */
#define STMPE811_REG_TSC_CTRL 0x40
#define STMPE811_REG_TSC_CFG 0x41
#define STMPE811_REG_WDM_TR_X 0x42
#define STMPE811_REG_WDM_TR_Y 0x44
#define STMPE811_REG_WDM_BL_X 0x46
#define STMPE811_REG_WDM_BL_Y 0x48
#define STMPE811_REG_FIFO_TH 0x4A
#define STMPE811_REG_FIFO_STA 0x4B
#define STMPE811_REG_FIFO_SIZE 0x4C
#define STMPE811_REG_TSC_DATA_X 0x4D
#define STMPE811_REG_TSC_DATA_Y 0x4F
#define STMPE811_REG_TSC_DATA_Z 0x51
#define STMPE811_REG_TSC_DATA_XYZ 0x52
#define STMPE811_REG_TSC_FRACT_XYZ 0x56
#define STMPE811_REG_TSC_DATA_INC 0x57
#define STMPE811_REG_TSC_DATA_NON_INC 0xD7
#define STMPE811_REG_TSC_I_DRIVE 0x58
#define STMPE811_REG_TSC_SHIELD 0x59

/* Touch Screen Pins definition */
#define STMPE811_TOUCH_YD STMPE811_PIN_7
#define STMPE811_TOUCH_XD STMPE811_PIN_6
#define STMPE811_TOUCH_YU STMPE811_PIN_5
#define STMPE811_TOUCH_XU STMPE811_PIN_4
#define STMPE811_TOUCH_IO_ALL                                            \
  (uint32_t)(STMPE811_TOUCH_YD | STMPE811_TOUCH_XD | STMPE811_TOUCH_YU | \
             STMPE811_TOUCH_XU)

/* IO Pins definition */
#define STMPE811_PIN_0 0x01
#define STMPE811_PIN_1 0x02
#define STMPE811_PIN_2 0x04
#define STMPE811_PIN_3 0x08
#define STMPE811_PIN_4 0x10
#define STMPE811_PIN_5 0x20
#define STMPE811_PIN_6 0x40
#define STMPE811_PIN_7 0x80
#define STMPE811_PIN_ALL 0xFF

/* IO Pins directions */
#define STMPE811_DIRECTION_IN 0x00
#define STMPE811_DIRECTION_OUT 0x01

/* IO IT types */
#define STMPE811_TYPE_LEVEL 0x00
#define STMPE811_TYPE_EDGE 0x02

/* IO IT polarity */
#define STMPE811_POLARITY_LOW 0x00
#define STMPE811_POLARITY_HIGH 0x04

/* IO Pin IT edge modes */
#define STMPE811_EDGE_FALLING 0x01
#define STMPE811_EDGE_RISING 0x02

/* TS registers masks */
#define STMPE811_TS_CTRL_ENABLE 0x01
#define STMPE811_TS_CTRL_STATUS 0x80

#define TOUCH_ADDRESS \
  (0x38U << 1)  // the HAL requires the 7-bit address to be shifted by one bit
#define TOUCH_PACKET_SIZE 7U
#define EVENT_PRESS_DOWN 0x00U
#define EVENT_CONTACT 0x80U
#define EVENT_LIFT_UP 0x40U
#define EVENT_NO_EVENT 0xC0U
#define GESTURE_NO_GESTURE 0x00U
#define X_POS_MSB (touch_data[3] & 0x0FU)
#define X_POS_LSB (touch_data[4])
#define Y_POS_MSB (touch_data[5] & 0x0FU)
#define Y_POS_LSB (touch_data[6])

#define EVENT_OLD_TIMEOUT_MS 50
#define EVENT_MISSING_TIMEOUT_MS 50

#define TS_I2C_ADDRESS 0x82

#define I2Cx_TIMEOUT_MAX \
  0x3000 /*<! The value of the maximal timeout for I2C waiting loops */
uint32_t I2cxTimeout =
    I2Cx_TIMEOUT_MAX; /*<! Value of Timeout when I2C communication fails */

/**
 * @brief  I2Cx error treatment function
 */
static void I2Cx_Error(void) { i2c_cycle(TOUCH_I2C_NUM); }

/**
 * @brief  Writes a value in a register of the device through BUS.
 * @param  Addr: Device address on BUS Bus.
 * @param  Reg: The target register address to write
 * @param  Value: The target register value to be written
 */
static void I2Cx_WriteData(uint8_t Addr, uint8_t Reg, uint8_t Value) {
  HAL_StatusTypeDef status = HAL_OK;

  status = i2c_mem_write(TOUCH_I2C_NUM, Addr, (uint16_t)Reg,
                         I2C_MEMADD_SIZE_8BIT, &Value, 1, I2cxTimeout);

  /* Check the communication status */
  if (status != HAL_OK) {
    /* Re-Initialize the BUS */
    I2Cx_Error();
  }
}

/**
 * @brief  Writes a value in a register of the device through BUS.
 * @param  Addr: Device address on BUS Bus.
 * @param  Reg: The target register address to write
 * @param  pBuffer: The target register value to be written
 * @param  Length: buffer size to be written
 */
static void I2Cx_WriteBuffer(uint8_t Addr, uint8_t Reg, uint8_t *pBuffer,
                             uint16_t Length) {
  HAL_StatusTypeDef status = HAL_OK;

  status = i2c_mem_write(TOUCH_I2C_NUM, Addr, (uint16_t)Reg,
                         I2C_MEMADD_SIZE_8BIT, pBuffer, Length, I2cxTimeout);

  /* Check the communication status */
  if (status != HAL_OK) {
    /* Re-Initialize the BUS */
    I2Cx_Error();
  }
}

/**
 * @brief  Reads a register of the device through BUS.
 * @param  Addr: Device address on BUS Bus.
 * @param  Reg: The target register address to write
 * @retval Data read at register address
 */
static uint8_t I2Cx_ReadData(uint8_t Addr, uint8_t Reg) {
  HAL_StatusTypeDef status = HAL_OK;
  uint8_t value = 0;

  status = i2c_mem_read(TOUCH_I2C_NUM, Addr, Reg, I2C_MEMADD_SIZE_8BIT, &value,
                        1, I2cxTimeout);

  /* Check the communication status */
  if (status != HAL_OK) {
    /* Re-Initialize the BUS */
    I2Cx_Error();
  }
  return value;
}

/**
 * @brief  Reads multiple data on the BUS.
 * @param  Addr: I2C Address
 * @param  Reg: Reg Address
 * @param  pBuffer: pointer to read data buffer
 * @param  Length: length of the data
 * @retval 0 if no problems to read multiple data
 */
static uint8_t I2Cx_ReadBuffer(uint8_t Addr, uint8_t Reg, uint8_t *pBuffer,
                               uint16_t Length) {
  HAL_StatusTypeDef status = HAL_OK;

  status = i2c_mem_read(TOUCH_I2C_NUM, Addr, (uint16_t)Reg,
                        I2C_MEMADD_SIZE_8BIT, pBuffer, Length, I2cxTimeout);

  /* Check the communication status */
  if (status == HAL_OK) {
    return 0;
  } else {
    /* Re-Initialize the BUS */
    I2Cx_Error();

    return 1;
  }
}
/**
 * @brief  IOE Writes single data operation.
 * @param  Addr: I2C Address
 * @param  Reg: Reg Address
 * @param  Value: Data to be written
 */
void IOE_Write(uint8_t Addr, uint8_t Reg, uint8_t Value) {
  I2Cx_WriteData(Addr, Reg, Value);
}

/**
 * @brief  IOE Reads single data.
 * @param  Addr: I2C Address
 * @param  Reg: Reg Address
 * @retval The read data
 */
uint8_t IOE_Read(uint8_t Addr, uint8_t Reg) { return I2Cx_ReadData(Addr, Reg); }

/**
 * @brief  IOE Writes multiple data.
 * @param  Addr: I2C Address
 * @param  Reg: Reg Address
 * @param  pBuffer: pointer to data buffer
 * @param  Length: length of the data
 */
void IOE_WriteMultiple(uint8_t Addr, uint8_t Reg, uint8_t *pBuffer,
                       uint16_t Length) {
  I2Cx_WriteBuffer(Addr, Reg, pBuffer, Length);
}

/**
 * @brief  IOE Reads multiple data.
 * @param  Addr: I2C Address
 * @param  Reg: Reg Address
 * @param  pBuffer: pointer to data buffer
 * @param  Length: length of the data
 * @retval 0 if no problems to read multiple data
 */
uint16_t IOE_ReadMultiple(uint8_t Addr, uint8_t Reg, uint8_t *pBuffer,
                          uint16_t Length) {
  return I2Cx_ReadBuffer(Addr, Reg, pBuffer, Length);
}

/**
 * @brief  IOE Delay.
 * @param  Delay in ms
 */
void IOE_Delay(uint32_t Delay) { HAL_Delay(Delay); }

static void touch_active_pin_state(void) {
  //  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_RESET);  // CTP_ON/PB10
  //  HAL_Delay(10);  // we need to wait until the circuit fully kicks-in

  GPIO_InitTypeDef GPIO_InitStructure;

  // PC4 capacitive touch panel module (CTPM) interrupt (INT) input
  GPIO_InitStructure.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_15;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
  __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_15);

  //  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_5, GPIO_PIN_SET);  // release CTPM reset
  //  HAL_Delay(310);  // "Time of starting to report point after resetting" min
  //  is
  // 300ms, giving an extra 10ms
}

/**
 * @brief  Enable the AF for the selected IO pin(s).
 * @param  DeviceAddr: Device address on communication Bus.
 * @param  IO_Pin: The IO pin to be configured. This parameter could be any
 *         combination of the following values:
 *   @arg  STMPE811_PIN_x: Where x can be from 0 to 7.
 * @retval None
 */
void stmpe811_IO_EnableAF(uint16_t DeviceAddr, uint32_t IO_Pin) {
  uint8_t tmp = 0;

  /* Get the current register value */
  tmp = IOE_Read(DeviceAddr, STMPE811_REG_IO_AF);

  /* Enable the selected pins alternate function */
  tmp &= ~(uint8_t)IO_Pin;

  /* Write back the new register value */
  IOE_Write(DeviceAddr, STMPE811_REG_IO_AF, tmp);
}

void touch_set_mode(void) {
  // set register 0xA4 G_MODE to interrupt trigger mode (0x01). basically, CTPM
  // generates a pulse when new data is available
  //  uint8_t touch_panel_config[] = {0xA4, 0x01};
  //  ensure(
  //          sectrue * (HAL_OK == HAL_I2C_Master_Transmit(
  //                  &I2c_handle, TOUCH_ADDRESS, touch_panel_config,
  //                  sizeof(touch_panel_config), 10)),
  //          NULL);

  uint8_t mode;

  /* Get the current register value */
  mode = IOE_Read(TS_I2C_ADDRESS, STMPE811_REG_SYS_CTRL2);

  /* Set the Functionalities to be Enabled */
  mode &= ~(STMPE811_IO_FCT);

  /* Write the new register value */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_SYS_CTRL2, mode);

  /* Select TSC pins in TSC alternate mode */
  stmpe811_IO_EnableAF(TS_I2C_ADDRESS, STMPE811_TOUCH_IO_ALL);

  /* Set the Functionalities to be Enabled */
  mode &= ~(STMPE811_TS_FCT | STMPE811_ADC_FCT);

  /* Set the new register value */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_SYS_CTRL2, mode);

  /* Select Sample Time, bit number and ADC Reference */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_ADC_CTRL1, 0x49);

  /* Wait for 2 ms */
  IOE_Delay(2);

  /* Select the ADC clock speed: 3.25 MHz */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_ADC_CTRL2, 0x01);

  /* Select 2 nF filter capacitor */
  /* Configuration:
     - Touch average control    : 4 samples
     - Touch delay time         : 500 uS
     - Panel driver setting time: 500 uS
  */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_TSC_CFG, 0x9A);

  /* Configure the Touch FIFO threshold: single point reading */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_TH, 0x01);

  /* Clear the FIFO memory content. */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x01);

  /* Put the FIFO back into operation mode  */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x00);

  /* Set the range and accuracy pf the pressure measurement (Z) :
     - Fractional part :7
     - Whole part      :1
  */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_TSC_FRACT_XYZ, 0x01);

  /* Set the driving capability (limit) of the device for TSC pins: 50mA */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_TSC_I_DRIVE, 0x01);

  /* Touch screen control configuration (enable TSC):
     - No window tracking index
     - XYZ acquisition mode
   */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_TSC_CTRL, 0x01);

  /*  Clear all the status pending bits if any */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_INT_STA, 0xFF);

  /* Wait for 2 ms delay */
  IOE_Delay(2);
}

void touch_power_on(void) {
  // turn on CTP circuitry
  touch_active_pin_state();
  HAL_Delay(50);
}

void touch_power_off(void) {
  // turn off CTP circuitry
  HAL_Delay(50);
}

/**
 * @brief  Reset the stmpe811 by Software.
 * @param  DeviceAddr: Device address on communication Bus.
 * @retval None
 */
void stmpe811_Reset() {
  /* Power Down the stmpe811 */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_SYS_CTRL1, 2);

  /* Wait for a delay to ensure registers erasing */
  IOE_Delay(10);

  /* Power On the Codec after the power off => all registers are reinitialized
   */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_SYS_CTRL1, 0);

  /* Wait for a delay to ensure registers erasing */
  IOE_Delay(2);
}

void touch_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  __HAL_RCC_GPIOA_CLK_ENABLE();

  // PC4 capacitive touch panel module (CTPM) interrupt (INT) input
  GPIO_InitStructure.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_15;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
  __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_15);

  stmpe811_Reset();
  touch_set_mode();
  touch_sensitivity(0x06);
}

void touch_sensitivity(uint8_t value) {
  // set panel threshold (TH_GROUP) - default value is 0x12
  //  uint8_t touch_panel_threshold[] = {0x80, value};
  //  ensure(sectrue *
  //                 (HAL_OK == HAL_I2C_Master_Transmit(
  //                         &I2c_handle, TOUCH_ADDRESS, touch_panel_threshold,
  //                         sizeof(touch_panel_threshold), 10)),
  //         NULL);
}

uint32_t touch_is_detected(void) {
  uint8_t state = ((IOE_Read(TS_I2C_ADDRESS, STMPE811_REG_TSC_CTRL) &
                    (uint8_t)STMPE811_TS_CTRL_STATUS) == (uint8_t)0x80);
  return state > 0;
}

uint32_t touch_active(void) {
  // check the interrupt line coming in from the CTPM.
  // the line make a short pulse, which sets an interrupt flag when new data is
  // available.
  // Reference section 1.2 of "Application Note for FT6x06 CTPM". we
  // configure the touch controller to use "interrupt trigger mode".

  //  uint32_t event = __HAL_GPIO_EXTI_GET_FLAG(GPIO_PIN_15);
  //  if (event != 0) {
  //    __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_15);
  //  }

  uint8_t state;
  uint8_t ret = 0;

  state = ((IOE_Read(TS_I2C_ADDRESS, STMPE811_REG_TSC_CTRL) &
            (uint8_t)STMPE811_TS_CTRL_STATUS) == (uint8_t)0x80);

  if (state > 0) {
    if (IOE_Read(TS_I2C_ADDRESS, STMPE811_REG_FIFO_SIZE) > 0) {
      ret = 1;
    }
  } else {
    /* Reset FIFO */
    IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x01);
    /* Enable the FIFO again */
    IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x00);
  }

  return ret;
}

uint32_t check_timeout(uint32_t prev, uint32_t timeout) {
  uint32_t current = hal_ticks_ms();
  uint32_t diff = current - prev;

  if (diff >= timeout) {
    return 1;
  }

  return 0;
}

/**
 * @brief  Get the touch screen X and Y positions values
 * @param  DeviceAddr: Device address on communication Bus.
 * @param  X: Pointer to X position value
 * @param  Y: Pointer to Y position value
 * @retval None.
 */
void stmpe811_TS_GetXY(uint16_t *X, uint16_t *Y) {
  uint8_t dataXYZ[4];
  uint32_t uldataXYZ;

  IOE_ReadMultiple(TS_I2C_ADDRESS, STMPE811_REG_TSC_DATA_NON_INC, dataXYZ,
                   sizeof(dataXYZ));

  /* Calculate positions values */
  uldataXYZ = (dataXYZ[0] << 24) | (dataXYZ[1] << 16) | (dataXYZ[2] << 8) |
              (dataXYZ[3] << 0);
  *X = (uldataXYZ >> 20) & 0x00000FFF;
  *Y = (uldataXYZ >> 8) & 0x00000FFF;

  /* Reset FIFO */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x01);
  /* Enable the FIFO again */
  IOE_Write(TS_I2C_ADDRESS, STMPE811_REG_FIFO_STA, 0x00);
}

typedef struct {
  uint16_t TouchDetected;
  uint16_t X;
  uint16_t Y;
  uint16_t Z;
} TS_StateTypeDef;

/**
 * @brief  Returns status and positions of the touch screen.
 * @param  TsState: Pointer to touch screen current state structure
 */
void BSP_TS_GetState(TS_StateTypeDef *TsState) {
  static uint32_t _x = 0, _y = 0;
  uint16_t xDiff, yDiff, x, y, xr, yr;

  TsState->TouchDetected = touch_active();

  if (TsState->TouchDetected) {
    stmpe811_TS_GetXY(&x, &y);

    /* Y value first correction */
    y -= 360;

    /* Y value second correction */
    yr = y / 11;

    /* Return y position value */
    if (yr <= 0) {
      yr = 0;
    } else if (yr > 320) {
      yr = 320 - 1;
    } else {
      yr = 320 - yr;
    }
    y = yr;

    /* X value first correction */
    if (x <= 3000) {
      x = 3870 - x;
    } else {
      x = 3800 - x;
    }

    /* X value second correction */
    xr = x / 15;

    /* Return X position value */
    if (xr <= 0) {
      xr = 0;
    } else if (xr > 240) {
      xr = 240 - 1;
    } else {
    }

    x = xr;
    xDiff = x > _x ? (x - _x) : (_x - x);
    yDiff = y > _y ? (y - _y) : (_y - y);

    if (xDiff + yDiff > 5) {
      _x = x;
      _y = y;
    }

    /* Update the X position */
    TsState->X = _x;

    /* Update the Y position */
    TsState->Y = _y;
  }
}

uint32_t touch_read(void) {
  TS_StateTypeDef state = {0};
  static uint32_t xy = 0;
  static TS_StateTypeDef state_last = {0};
  // static uint16_t first = 1;
  static uint16_t touching = 0;

  if (!touch_is_detected()) {
    if (touching) {
      // touch end
      memcpy(&state_last, &state, sizeof(state));
      touching = 0;
      return TOUCH_END | xy;
    }
    return 0;
  }

  BSP_TS_GetState(&state);

  if (state.TouchDetected == 0) {
    return 0;
  }

  //  if (first != 0) {
  //    memcpy(&state_last, &state, sizeof(state));
  //    first = 0;
  //    return 0;
  //  }

  if ((state.TouchDetected == 0 && state_last.TouchDetected == 0) ||
      memcmp(&state, &state_last, sizeof(state)) == 0) {
    // no change detected
    return 0;
  }

  xy = touch_pack_xy(state.X, state.Y);

  if (state.TouchDetected && !state_last.TouchDetected) {
    // touch start
    memcpy(&state_last, &state, sizeof(state));
    touching = 1;
    return TOUCH_START | xy;
  } else if (!state.TouchDetected && state_last.TouchDetected) {
    // touch end
    memcpy(&state_last, &state, sizeof(state));
    touching = 0;
    return TOUCH_END | xy;
  } else {
    // touch move
    memcpy(&state_last, &state, sizeof(state));
    return TOUCH_MOVE | xy;
  }

  return 0;
}
