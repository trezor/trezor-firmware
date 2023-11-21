

#include STM32_HAL_H
#include TREZOR_BOARD
#include "i2c.h"
#include "common.h"

static I2C_HandleTypeDef i2c_handle[I2C_COUNT];

typedef struct {
  I2C_TypeDef *Instance;
  GPIO_TypeDef *SclPort;
  GPIO_TypeDef *SdaPort;
  uint16_t SclPin;
  uint16_t SdaPin;
  uint8_t PinAF;
  volatile uint32_t *ResetReg;
  uint32_t ResetBit;
} i2c_instance_t;

i2c_instance_t i2c_defs[I2C_COUNT] = {
    {
        .Instance = I2C_INSTANCE_0,
        .SclPort = I2C_INSTANCE_0_SCL_PORT,
        .SdaPort = I2C_INSTANCE_0_SDA_PORT,
        .SclPin = I2C_INSTANCE_0_SCL_PIN,
        .SdaPin = I2C_INSTANCE_0_SDA_PIN,
        .PinAF = I2C_INSTANCE_0_PIN_AF,
        .ResetReg = I2C_INSTANCE_0_RESET_REG,
        .ResetBit = I2C_INSTANCE_0_RESET_BIT,
    },
#ifdef I2C_INSTANCE_1
    {
        .Instance = I2C_INSTANCE_1,
        .SclPort = I2C_INSTANCE_1_SCL_PORT,
        .SdaPort = I2C_INSTANCE_1_SDA_PORT,
        .SclPin = I2C_INSTANCE_1_SCL_PIN,
        .SdaPin = I2C_INSTANCE_1_SDA_PIN,
        .PinAF = I2C_INSTANCE_1_PIN_AF,
        .ResetReg = I2C_INSTANCE_1_RESET_REG,
        .ResetBit = I2C_INSTANCE_1_RESET_BIT,
    },
#endif

};

#ifndef I2C_VALID_TIMING_NBR
#define I2C_VALID_TIMING_NBR 128U
#endif /* I2C_VALID_TIMING_NBR */

#define I2C_SPEED_FREQ_STANDARD 0U       /* 100 kHz */
#define I2C_SPEED_FREQ_FAST 1U           /* 400 kHz */
#define I2C_SPEED_FREQ_FAST_PLUS 2U      /* 1 MHz */
#define I2C_ANALOG_FILTER_DELAY_MIN 50U  /* ns */
#define I2C_ANALOG_FILTER_DELAY_MAX 260U /* ns */
#define I2C_USE_ANALOG_FILTER 1U
#define I2C_DIGITAL_FILTER_COEF 0U
#define I2C_PRESC_MAX 16U
#define I2C_SCLDEL_MAX 16U
#define I2C_SDADEL_MAX 16U
#define I2C_SCLH_MAX 256U
#define I2C_SCLL_MAX 256U
#define SEC2NSEC 1000000000UL
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_Types BUS Private Types
 * @{
 */
typedef struct {
  uint32_t freq;      /* Frequency in Hz */
  uint32_t freq_min;  /* Minimum frequency in Hz */
  uint32_t freq_max;  /* Maximum frequency in Hz */
  uint32_t hddat_min; /* Minimum data hold time in ns */
  uint32_t vddat_max; /* Maximum data valid time in ns */
  uint32_t sudat_min; /* Minimum data setup time in ns */
  uint32_t lscl_min;  /* Minimum low period of the SCL clock in ns */
  uint32_t hscl_min;  /* Minimum high period of SCL clock in ns */
  uint32_t trise;     /* Rise time in ns */
  uint32_t tfall;     /* Fall time in ns */
  uint32_t dnf;       /* Digital noise filter coefficient */
} I2C_Charac_t;

typedef struct {
  uint32_t presc;   /* Timing prescaler */
  uint32_t tscldel; /* SCL delay */
  uint32_t tsdadel; /* SDA delay */
  uint32_t sclh;    /* SCL high period */
  uint32_t scll;    /* SCL low period */
} I2C_Timings_t;

static I2C_Timings_t I2c_valid_timing[I2C_VALID_TIMING_NBR];
static uint32_t I2c_valid_timing_nbr = 0;

static const I2C_Charac_t I2C_Charac[] = {
    [I2C_SPEED_FREQ_STANDARD] =
        {
            .freq = 100000,
            .freq_min = 80000,
            .freq_max = 120000,
            .hddat_min = 0,
            .vddat_max = 3450,
            .sudat_min = 250,
            .lscl_min = 4700,
            .hscl_min = 4000,
            .trise = 640,
            .tfall = 20,
            .dnf = I2C_DIGITAL_FILTER_COEF,
        },
    [I2C_SPEED_FREQ_FAST] =
        {
            .freq = 400000,
            .freq_min = 320000,
            .freq_max = 480000,
            .hddat_min = 0,
            .vddat_max = 900,
            .sudat_min = 100,
            .lscl_min = 1300,
            .hscl_min = 600,
            .trise = 250,
            .tfall = 100,
            .dnf = I2C_DIGITAL_FILTER_COEF,
        },
    [I2C_SPEED_FREQ_FAST_PLUS] =
        {
            .freq = 1000000,
            .freq_min = 800000,
            .freq_max = 1200000,
            .hddat_min = 0,
            .vddat_max = 450,
            .sudat_min = 50,
            .lscl_min = 500,
            .hscl_min = 260,
            .trise = 60,
            .tfall = 100,
            .dnf = I2C_DIGITAL_FILTER_COEF,
        },
};

/**
 * @brief  Compute PRESC, SCLDEL and SDADEL.
 * @param  clock_src_freq I2C source clock in HZ.
 * @param  I2C_speed I2C frequency (index).
 * @retval None.
 */
static void I2C_Compute_PRESC_SCLDEL_SDADEL(uint32_t clock_src_freq,
                                            uint32_t I2C_speed) {
  uint32_t prev_presc = I2C_PRESC_MAX;
  uint32_t ti2cclk;
  int32_t tsdadel_min;
  int32_t tsdadel_max;
  int32_t tscldel_min;
  uint32_t presc;
  uint32_t scldel;
  uint32_t sdadel;
  uint32_t tafdel_min;
  uint32_t tafdel_max;
  ti2cclk = (SEC2NSEC + (clock_src_freq / 2U)) / clock_src_freq;

  tafdel_min = I2C_ANALOG_FILTER_DELAY_MIN;
  tafdel_max = I2C_ANALOG_FILTER_DELAY_MAX;

  /* tDNF = DNF x tI2CCLK
     tPRESC = (PRESC+1) x tI2CCLK
     SDADEL >= {tf +tHD;DAT(min) - tAF(min) - tDNF - [3 x tI2CCLK]} / {tPRESC}
     SDADEL <= {tVD;DAT(max) - tr - tAF(max) - tDNF- [4 x tI2CCLK]} / {tPRESC}
   */

  tsdadel_min =
      (int32_t)I2C_Charac[I2C_speed].tfall +
      (int32_t)I2C_Charac[I2C_speed].hddat_min - (int32_t)tafdel_min -
      (int32_t)(((int32_t)I2C_Charac[I2C_speed].dnf + 3) * (int32_t)ti2cclk);

  tsdadel_max =
      (int32_t)I2C_Charac[I2C_speed].vddat_max -
      (int32_t)I2C_Charac[I2C_speed].trise - (int32_t)tafdel_max -
      (int32_t)(((int32_t)I2C_Charac[I2C_speed].dnf + 4) * (int32_t)ti2cclk);

  /* {[tr+ tSU;DAT(min)] / [tPRESC]} - 1 <= SCLDEL */
  tscldel_min = (int32_t)I2C_Charac[I2C_speed].trise +
                (int32_t)I2C_Charac[I2C_speed].sudat_min;

  if (tsdadel_min <= 0) {
    tsdadel_min = 0;
  }

  if (tsdadel_max <= 0) {
    tsdadel_max = 0;
  }

  for (presc = 0; presc < I2C_PRESC_MAX; presc++) {
    for (scldel = 0; scldel < I2C_SCLDEL_MAX; scldel++) {
      /* TSCLDEL = (SCLDEL+1) * (PRESC+1) * TI2CCLK */
      uint32_t tscldel = (scldel + 1U) * (presc + 1U) * ti2cclk;

      if (tscldel >= (uint32_t)tscldel_min) {
        for (sdadel = 0; sdadel < I2C_SDADEL_MAX; sdadel++) {
          /* TSDADEL = SDADEL * (PRESC+1) * TI2CCLK */
          uint32_t tsdadel = (sdadel * (presc + 1U)) * ti2cclk;

          if ((tsdadel >= (uint32_t)tsdadel_min) &&
              (tsdadel <= (uint32_t)tsdadel_max)) {
            if (presc != prev_presc) {
              I2c_valid_timing[I2c_valid_timing_nbr].presc = presc;
              I2c_valid_timing[I2c_valid_timing_nbr].tscldel = scldel;
              I2c_valid_timing[I2c_valid_timing_nbr].tsdadel = sdadel;
              prev_presc = presc;
              I2c_valid_timing_nbr++;

              if (I2c_valid_timing_nbr >= I2C_VALID_TIMING_NBR) {
                return;
              }
            }
          }
        }
      }
    }
  }
}

/**
 * @brief  Calculate SCLL and SCLH and find best configuration.
 * @param  clock_src_freq I2C source clock in HZ.
 * @param  I2C_speed I2C frequency (index).
 * @retval config index (0 to I2C_VALID_TIMING_NBR], 0xFFFFFFFF for no valid
 * config.
 */
static uint32_t I2C_Compute_SCLL_SCLH(uint32_t clock_src_freq,
                                      uint32_t I2C_speed) {
  uint32_t ret = 0xFFFFFFFFU;
  uint32_t ti2cclk;
  uint32_t ti2cspeed;
  uint32_t prev_error;
  uint32_t dnf_delay;
  uint32_t clk_min;
  uint32_t clk_max;
  uint32_t scll;
  uint32_t sclh;
  uint32_t tafdel_min;

  ti2cclk = (SEC2NSEC + (clock_src_freq / 2U)) / clock_src_freq;
  ti2cspeed = (SEC2NSEC + (I2C_Charac[I2C_speed].freq / 2U)) /
              I2C_Charac[I2C_speed].freq;

  tafdel_min = I2C_ANALOG_FILTER_DELAY_MIN;

  /* tDNF = DNF x tI2CCLK */
  dnf_delay = I2C_Charac[I2C_speed].dnf * ti2cclk;

  clk_max = SEC2NSEC / I2C_Charac[I2C_speed].freq_min;
  clk_min = SEC2NSEC / I2C_Charac[I2C_speed].freq_max;

  prev_error = ti2cspeed;

  for (uint32_t count = 0; count < I2c_valid_timing_nbr; count++) {
    /* tPRESC = (PRESC+1) x tI2CCLK*/
    uint32_t tpresc = (I2c_valid_timing[count].presc + 1U) * ti2cclk;

    for (scll = 0; scll < I2C_SCLL_MAX; scll++) {
      /* tLOW(min) <= tAF(min) + tDNF + 2 x tI2CCLK + [(SCLL+1) x tPRESC ] */
      uint32_t tscl_l =
          tafdel_min + dnf_delay + (2U * ti2cclk) + ((scll + 1U) * tpresc);

      /* The I2CCLK period tI2CCLK must respect the following conditions:
      tI2CCLK < (tLOW - tfilters) / 4 and tI2CCLK < tHIGH */
      if ((tscl_l > I2C_Charac[I2C_speed].lscl_min) &&
          (ti2cclk < ((tscl_l - tafdel_min - dnf_delay) / 4U))) {
        for (sclh = 0; sclh < I2C_SCLH_MAX; sclh++) {
          /* tHIGH(min) <= tAF(min) + tDNF + 2 x tI2CCLK + [(SCLH+1) x tPRESC]
           */
          uint32_t tscl_h =
              tafdel_min + dnf_delay + (2U * ti2cclk) + ((sclh + 1U) * tpresc);

          /* tSCL = tf + tLOW + tr + tHIGH */
          uint32_t tscl = tscl_l + tscl_h + I2C_Charac[I2C_speed].trise +
                          I2C_Charac[I2C_speed].tfall;

          if ((tscl >= clk_min) && (tscl <= clk_max) &&
              (tscl_h >= I2C_Charac[I2C_speed].hscl_min) &&
              (ti2cclk < tscl_h)) {
            int32_t error = (int32_t)tscl - (int32_t)ti2cspeed;

            if (error < 0) {
              error = -error;
            }

            /* look for the timings with the lowest clock error */
            if ((uint32_t)error < prev_error) {
              prev_error = (uint32_t)error;
              I2c_valid_timing[count].scll = scll;
              I2c_valid_timing[count].sclh = sclh;
              ret = count;
            }
          }
        }
      }
    }
  }

  return ret;
}

/*
 * @brief  Compute I2C timing according current I2C clock source and required
 * I2C clock.
 * @param  clock_src_freq I2C clock source in Hz.
 * @param  i2c_freq Required I2C clock in Hz.
 * @retval I2C timing or 0 in case of error.
 */
static uint32_t I2C_GetTiming(uint32_t clock_src_freq, uint32_t i2c_freq) {
  uint32_t ret = 0;
  uint32_t speed;
  uint32_t idx;

  if ((clock_src_freq != 0U) && (i2c_freq != 0U)) {
    for (speed = 0; speed <= (uint32_t)I2C_SPEED_FREQ_FAST_PLUS; speed++) {
      if ((i2c_freq >= I2C_Charac[speed].freq_min) &&
          (i2c_freq <= I2C_Charac[speed].freq_max)) {
        I2C_Compute_PRESC_SCLDEL_SDADEL(clock_src_freq, speed);
        idx = I2C_Compute_SCLL_SCLH(clock_src_freq, speed);

        if (idx < I2C_VALID_TIMING_NBR) {
          ret = ((I2c_valid_timing[idx].presc & 0x0FU) << 28) |
                ((I2c_valid_timing[idx].tscldel & 0x0FU) << 20) |
                ((I2c_valid_timing[idx].tsdadel & 0x0FU) << 16) |
                ((I2c_valid_timing[idx].sclh & 0xFFU) << 8) |
                ((I2c_valid_timing[idx].scll & 0xFFU) << 0);
        }
        break;
      }
    }
  }

  return ret;
}

void i2c_init_instance(uint16_t idx, i2c_instance_t *instance) {
  if (i2c_handle[idx].Instance) {
    return;
  }

  GPIO_InitTypeDef GPIO_InitStructure;

  // configure CTP I2C SCL and SDA GPIO lines
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed =
      GPIO_SPEED_FREQ_LOW;  // I2C is a KHz bus and low speed is still good into
  // the low MHz

  GPIO_InitStructure.Alternate = instance->PinAF;
  GPIO_InitStructure.Pin = instance->SclPin;
  HAL_GPIO_Init(instance->SclPort, &GPIO_InitStructure);

  GPIO_InitStructure.Alternate = instance->PinAF;
  GPIO_InitStructure.Pin = instance->SdaPin;
  HAL_GPIO_Init(instance->SdaPort, &GPIO_InitStructure);

  i2c_handle[idx].Instance = instance->Instance;
  i2c_handle[idx].Init.Timing = I2C_GetTiming(HAL_RCC_GetPCLK1Freq(), 400000);
  i2c_handle[idx].Init.OwnAddress1 = 0xFE;  // master
  i2c_handle[idx].Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  i2c_handle[idx].Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  i2c_handle[idx].Init.OwnAddress2 = 0;
  i2c_handle[idx].Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  i2c_handle[idx].Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_OK != HAL_I2C_Init(&i2c_handle[idx])) {
    ensure(secfalse, "I2C was not loaded properly.");
    return;
  }
}

void i2c_init(void) {
  // enable I2C clock
  I2C_INSTANCE_0_CLK_EN();
  I2C_INSTANCE_0_SCL_CLK_EN();
  I2C_INSTANCE_0_SDA_CLK_EN();
  i2c_init_instance(0, &i2c_defs[0]);

#ifdef I2C_INSTANCE_1
  I2C_INSTANCE_1_CLK_EN();
  I2C_INSTANCE_1_SCL_CLK_EN();
  I2C_INSTANCE_1_SDA_CLK_EN();
  i2c_init_instance(1, &i2c_defs[1]);
#endif
}

void i2c_deinit(uint16_t idx) {
  if (i2c_handle[idx].Instance) {
    HAL_I2C_DeInit(&i2c_handle[idx]);
    i2c_handle[idx].Instance = NULL;
  }
}

void i2c_ensure_pin(GPIO_TypeDef *port, uint16_t GPIO_Pin,
                    GPIO_PinState PinState) {
  HAL_GPIO_WritePin(port, GPIO_Pin, PinState);
  while (HAL_GPIO_ReadPin(port, GPIO_Pin) != PinState)
    ;
}

void i2c_cycle(uint16_t idx) {
  SET_BIT(*i2c_defs[idx].ResetReg, i2c_defs[idx].ResetBit);
  CLEAR_BIT(*i2c_defs[idx].ResetReg, i2c_defs[idx].ResetBit);
}

HAL_StatusTypeDef i2c_transmit(uint16_t idx, uint8_t addr, uint8_t *data,
                               uint16_t len, uint32_t timeout) {
  return HAL_I2C_Master_Transmit(&i2c_handle[idx], addr, data, len, timeout);
}

HAL_StatusTypeDef i2c_receive(uint16_t idx, uint8_t addr, uint8_t *data,
                              uint16_t len, uint32_t timeout) {
  HAL_StatusTypeDef ret =
      HAL_I2C_Master_Receive(&i2c_handle[idx], addr, data, len, timeout);
#ifdef USE_OPTIGA
  if (idx == OPTIGA_I2C_INSTANCE) {
    // apply GUARD_TIME as specified by the OPTIGA datasheet
    // (only applies to the I2C bus to which the OPTIGA is connected)
    hal_delay_us(50);
  }
#endif

  return ret;
}

HAL_StatusTypeDef i2c_mem_write(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                                uint16_t mem_addr_size, uint8_t *data,
                                uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Write(&i2c_handle[idx], addr, mem_addr, mem_addr_size,
                           data, len, timeout);
}
HAL_StatusTypeDef i2c_mem_read(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                               uint16_t mem_addr_size, uint8_t *data,
                               uint16_t len, uint32_t timeout) {
  return HAL_I2C_Mem_Read(&i2c_handle[idx], addr, mem_addr, mem_addr_size, data,
                          len, timeout);
}
