#include STM32_HAL_H

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY_BUS
 * @{
 */
/** @defgroup STM32U5x9J_DISCOVERY_BUS_Exported_Types BUS Exported Types
 * @{
 */
/* Common Error codes */
#define BSP_ERROR_NONE 0
#define BSP_ERROR_NO_INIT -1
#define BSP_ERROR_WRONG_PARAM -2
#define BSP_ERROR_BUSY -3
#define BSP_ERROR_PERIPH_FAILURE -4
#define BSP_ERROR_COMPONENT_FAILURE -5
#define BSP_ERROR_UNKNOWN_FAILURE -6
#define BSP_ERROR_UNKNOWN_COMPONENT -7
#define BSP_ERROR_BUS_FAILURE -8
#define BSP_ERROR_CLOCK_FAILURE -9
#define BSP_ERROR_MSP_FAILURE -10
#define BSP_ERROR_FEATURE_NOT_SUPPORTED -11

/* BSP OSPI error codes */
#define BSP_ERROR_OSPI_SUSPENDED -20
#define BSP_ERROR_OSPI_MMP_UNLOCK_FAILURE -21
#define BSP_ERROR_OSPI_MMP_LOCK_FAILURE -22

/* BSP HSPI error codes */
#define BSP_ERROR_HSPI_MMP_UNLOCK_FAILURE -31
#define BSP_ERROR_HSPI_MMP_LOCK_FAILURE -32

/* BSP BUS error codes */
#define BSP_ERROR_BUS_TRANSACTION_FAILURE -100
#define BSP_ERROR_BUS_ARBITRATION_LOSS -101
#define BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE -102
#define BSP_ERROR_BUS_PROTOCOL_FAILURE -103

#define BSP_ERROR_BUS_MODE_FAULT -104
#define BSP_ERROR_BUS_FRAME_ERROR -105
#define BSP_ERROR_BUS_CRC_ERROR -106
#define BSP_ERROR_BUS_DMA_FAILURE -107

#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
typedef struct {
  pI2C_CallbackTypeDef pMspI2cInitCb;
  pI2C_CallbackTypeDef pMspI2cDeInitCb;
} BSP_I2C_Cb_t;
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS > 0) */

__weak HAL_StatusTypeDef MX_I2C5_Init(I2C_HandleTypeDef *hI2c, uint32_t timing);
__weak HAL_StatusTypeDef MX_I2C4_Init(I2C_HandleTypeDef *hI2c, uint32_t timing);
__weak HAL_StatusTypeDef MX_I2C2_Init(I2C_HandleTypeDef *hI2c, uint32_t timing);
__weak HAL_StatusTypeDef MX_I2C3_Init(I2C_HandleTypeDef *hI2c, uint32_t timing);
/**
 * @}
 */
/** @defgroup STM32U5x9J_DISCOVERY_BUS_Exported_Constants BUS Exported Constants
 * @{
 */
/* Definition for I2C5 clock resources */
#define BUS_I2C5 I2C5

#define BUS_I2C5_CLK_ENABLE() __HAL_RCC_I2C5_CLK_ENABLE()
#define BUS_I2C5_CLK_DISABLE() __HAL_RCC_I2C5_CLK_DISABLE()

#define BUS_I2C5_SCL_GPIO_CLK_ENABLE() __HAL_RCC_GPIOH_CLK_ENABLE()
#define BUS_I2C5_SCL_GPIO_CLK_DISABLE() __HAL_RCC_GPIOH_CLK_DISABLE()

#define BUS_I2C5_SDA_GPIO_CLK_ENABLE() __HAL_RCC_GPIOH_CLK_ENABLE()
#define BUS_I2C5_SDA_GPIO_CLK_DISABLE() __HAL_RCC_GPIOH_CLK_DISABLE()

#define BUS_I2C5_FORCE_RESET() __HAL_RCC_I2C5_FORCE_RESET()
#define BUS_I2C5_RELEASE_RESET() __HAL_RCC_I2C5_RELEASE_RESET()

/* Definition for I2C5 Pins */
#define BUS_I2C5_SCL_PIN GPIO_PIN_5
#define BUS_I2C5_SCL_GPIO_PORT GPIOH
#define BUS_I2C5_SCL_AF GPIO_AF2_I2C5

#define BUS_I2C5_SDA_PIN GPIO_PIN_4
#define BUS_I2C5_SDA_GPIO_PORT GPIOH
#define BUS_I2C5_SDA_AF GPIO_AF2_I2C5

#ifndef BUS_I2C5_FREQUENCY
#define BUS_I2C5_FREQUENCY 400000U /* Frequency of I2C5 = 400 KHz*/
#endif                             /* BUS_I2C5_FREQUENCY */

/* Definition for I2C4 clock resources */
#define BUS_I2C4 I2C4

#define BUS_I2C4_CLK_ENABLE() __HAL_RCC_I2C4_CLK_ENABLE()
#define BUS_I2C4_CLK_DISABLE() __HAL_RCC_I2C4_CLK_DISABLE()

#define BUS_I2C4_SCL_GPIO_CLK_ENABLE() __HAL_RCC_GPIOB_CLK_ENABLE()
#define BUS_I2C4_SCL_GPIO_CLK_DISABLE() __HAL_RCC_GPIOB_CLK_DISABLE()

#define BUS_I2C4_SDA_GPIO_CLK_ENABLE() __HAL_RCC_GPIOB_CLK_ENABLE()
#define BUS_I2C4_SDA_GPIO_CLK_DISABLE() __HAL_RCC_GPIOB_CLK_DISABLE()

#define BUS_I2C4_FORCE_RESET() __HAL_RCC_I2C4_FORCE_RESET()
#define BUS_I2C4_RELEASE_RESET() __HAL_RCC_I2C4_RELEASE_RESET()

/* Definition for I2C4 Pins */
#define BUS_I2C4_SCL_PIN GPIO_PIN_6
#define BUS_I2C4_SCL_GPIO_PORT GPIOB
#define BUS_I2C4_SCL_AF GPIO_AF5_I2C4

#define BUS_I2C4_SDA_PIN GPIO_PIN_7
#define BUS_I2C4_SDA_GPIO_PORT GPIOB
#define BUS_I2C4_SDA_AF GPIO_AF5_I2C4

#ifndef BUS_I2C4_FREQUENCY
#define BUS_I2C4_FREQUENCY 100000U /* Frequency of I2C4 = 400 KHz*/
#endif                             /* BUS_I2C4_FREQUENCY */

/* Definition for I2C2 clock resources */
#define BUS_I2C2 I2C2

#define BUS_I2C2_CLK_ENABLE() __HAL_RCC_I2C2_CLK_ENABLE()
#define BUS_I2C2_CLK_DISABLE() __HAL_RCC_I2C2_CLK_DISABLE()

#define BUS_I2C2_SCL_GPIO_CLK_ENABLE() __HAL_RCC_GPIOF_CLK_ENABLE()
#define BUS_I2C2_SCL_GPIO_CLK_DISABLE() __HAL_RCC_GPIOF_CLK_DISABLE()

#define BUS_I2C2_SDA_GPIO_CLK_ENABLE() __HAL_RCC_GPIOF_CLK_ENABLE()
#define BUS_I2C2_SDA_GPIO_CLK_DISABLE() __HAL_RCC_GPIOF_CLK_DISABLE()

#define BUS_I2C2_FORCE_RESET() __HAL_RCC_I2C2_FORCE_RESET()
#define BUS_I2C2_RELEASE_RESET() __HAL_RCC_I2C2_RELEASE_RESET()

/* Definition for I2C2 Pins */
#define BUS_I2C2_SCL_PIN GPIO_PIN_1
#define BUS_I2C2_SCL_GPIO_PORT GPIOF
#define BUS_I2C2_SCL_AF GPIO_AF4_I2C2

#define BUS_I2C2_SDA_PIN GPIO_PIN_0
#define BUS_I2C2_SDA_GPIO_PORT GPIOF
#define BUS_I2C2_SDA_AF GPIO_AF4_I2C2

#ifndef BUS_I2C2_FREQUENCY
#define BUS_I2C2_FREQUENCY 400000U /* Frequency of I2C2 = 400 KHz*/
#endif                             /* BUS_I2C2_FREQUENCY */

/* Definition for I2C3 clock resources */
#define BUS_I2C3 I2C3

#define BUS_I2C3_CLK_ENABLE() __HAL_RCC_I2C3_CLK_ENABLE()
#define BUS_I2C3_CLK_DISABLE() __HAL_RCC_I2C3_CLK_DISABLE()

#define BUS_I2C3_SCL_GPIO_CLK_ENABLE() __HAL_RCC_GPIOH_CLK_ENABLE()
#define BUS_I2C3_SCL_GPIO_CLK_DISABLE() __HAL_RCC_GPIOH_CLK_DISABLE()

#define BUS_I2C3_SDA_GPIO_CLK_ENABLE() __HAL_RCC_GPIOH_CLK_ENABLE()
#define BUS_I2C3_SDA_GPIO_CLK_DISABLE() __HAL_RCC_GPIOH_CLK_DISABLE()

#define BUS_I2C3_FORCE_RESET() __HAL_RCC_I2C3_FORCE_RESET()
#define BUS_I2C3_RELEASE_RESET() __HAL_RCC_I2C3_RELEASE_RESET()

/* Definition for I2C3 Pins */
#define BUS_I2C3_SCL_PIN GPIO_PIN_7
#define BUS_I2C3_SCL_GPIO_PORT GPIOH
#define BUS_I2C3_SCL_AF GPIO_AF4_I2C3

#define BUS_I2C3_SDA_PIN GPIO_PIN_8
#define BUS_I2C3_SDA_GPIO_PORT GPIOH
#define BUS_I2C3_SDA_AF GPIO_AF4_I2C3

#ifndef BUS_I2C3_FREQUENCY
#define BUS_I2C3_FREQUENCY 400000U /* Frequency of I2C3 = 400 KHz*/
#endif                             /* BUS_I2C3_FREQUENCY */

/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_BUS_Exported_Variables
 * @{
 */
extern I2C_HandleTypeDef hbus_i2c2;
extern I2C_HandleTypeDef hbus_i2c3;
extern I2C_HandleTypeDef hbus_i2c4;
extern I2C_HandleTypeDef hbus_i2c5;

/** @addtogroup BSP
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS BUS
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_Constants BUS Private Constants
 * @{
 */
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
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_Constants BUS Private Constants
 * @{
 */
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
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_Variables BUS Private Variables
 * @{
 */
#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
static uint32_t IsI2c5MspCbValid = 0;
static uint32_t IsI2c4MspCbValid = 0;
static uint32_t IsI2c2MspCbValid = 0;
static uint32_t IsI2c3MspCbValid = 0;
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS */

static uint32_t I2c5InitCounter = 0;
static uint32_t I2c4InitCounter = 0;
static uint32_t I2c2InitCounter = 0;
static uint32_t I2c3InitCounter = 0;
static I2C_Timings_t I2c_valid_timing[I2C_VALID_TIMING_NBR];
static uint32_t I2c_valid_timing_nbr = 0;
#if defined(BSP_USE_CMSIS_OS)
static osSemaphoreId BspI2cSemaphore = 0;
#endif /* BSP_USE_CMSIS_OS */
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Exported_Variables BUS Exported Variables
 * @{
 */
I2C_HandleTypeDef hbus_i2c5;
I2C_HandleTypeDef hbus_i2c4;
I2C_HandleTypeDef hbus_i2c2;
I2C_HandleTypeDef hbus_i2c3;

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_FunctionPrototypes BUS Private
 * FunctionPrototypes
 * @{
 */
static void I2C5_MspInit(I2C_HandleTypeDef *hI2c);
static void I2C5_MspDeInit(I2C_HandleTypeDef *hI2c);
static int32_t I2C5_WriteReg(uint16_t DevAddr, uint16_t MemAddSize,
                             uint16_t Reg, uint8_t *pData, uint16_t Length);
static int32_t I2C5_ReadReg(uint16_t DevAddr, uint16_t MemAddSize, uint16_t Reg,
                            uint8_t *pData, uint16_t Length);
static int32_t I2C5_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
static int32_t I2C5_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length);

static void I2C4_MspInit(I2C_HandleTypeDef *hI2c);
static void I2C4_MspDeInit(I2C_HandleTypeDef *hI2c);
static int32_t I2C4_WriteReg(uint16_t DevAddr, uint16_t MemAddSize,
                             uint16_t Reg, uint8_t *pData, uint16_t Length);
static int32_t I2C4_ReadReg(uint16_t DevAddr, uint16_t MemAddSize, uint16_t Reg,
                            uint8_t *pData, uint16_t Length);
static int32_t I2C4_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
static int32_t I2C4_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length);

static void I2C2_MspInit(I2C_HandleTypeDef *hI2c);
static void I2C2_MspDeInit(I2C_HandleTypeDef *hI2c);
static int32_t I2C2_WriteReg(uint16_t DevAddr, uint16_t MemAddSize,
                             uint16_t Reg, uint8_t *pData, uint16_t Length);
static int32_t I2C2_ReadReg(uint16_t DevAddr, uint16_t MemAddSize, uint16_t Reg,
                            uint8_t *pData, uint16_t Length);
static int32_t I2C2_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
static int32_t I2C2_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length);

static void I2C3_MspInit(I2C_HandleTypeDef *hI2c);
static void I2C3_MspDeInit(I2C_HandleTypeDef *hI2c);
static int32_t I2C3_WriteReg(uint16_t DevAddr, uint16_t MemAddSize,
                             uint16_t Reg, uint8_t *pData, uint16_t Length);
static int32_t I2C3_ReadReg(uint16_t DevAddr, uint16_t MemAddSize, uint16_t Reg,
                            uint8_t *pData, uint16_t Length);
static int32_t I2C3_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
static int32_t I2C3_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length);

static uint32_t I2C_GetTiming(uint32_t clock_src_freq, uint32_t i2c_freq);
static uint32_t I2C_Compute_SCLL_SCLH(uint32_t clock_src_freq,
                                      uint32_t I2C_speed);
static void I2C_Compute_PRESC_SCLDEL_SDADEL(uint32_t clock_src_freq,
                                            uint32_t I2C_speed);

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Exported_Functions BUS Exported Functions
 * @{
 */

/**
 * @brief  Initializes I2C5 HAL.
 * @retval BSP status
 */
int32_t BSP_I2C5_Init(void) {
  int32_t ret = BSP_ERROR_NONE;

  hbus_i2c5.Instance = BUS_I2C5;

  if (I2c5InitCounter == 0U) {
    I2c5InitCounter++;

    if (HAL_I2C_GetState(&hbus_i2c5) == HAL_I2C_STATE_RESET) {
#if defined(BSP_USE_CMSIS_OS)
      if (BspI2cSemaphore == NULL) {
        /* Create semaphore to prevent multiple I2C access */
        osSemaphoreDef(BSP_I2C_SEM);
        BspI2cSemaphore = osSemaphoreCreate(osSemaphore(BSP_I2C_SEM), 1);
      }
#endif /* BSP_USE_CMSIS_OS */
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
      /* Init the I2C5 Msp */
      I2C5_MspInit(&hbus_i2c5);
#else
      if (IsI2c5MspCbValid == 0U) {
        if (BSP_I2C5_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) {
          ret = BSP_ERROR_MSP_FAILURE;
        }
      }
      if (ret == BSP_ERROR_NONE) {
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */
      if (MX_I2C5_Init(&hbus_i2c5, I2C_GetTiming(HAL_RCC_GetPCLK1Freq(),
                                                 BUS_I2C5_FREQUENCY)) !=
          HAL_OK) {
        ret = BSP_ERROR_BUS_FAILURE;
      }
#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
    }
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS > 0) */
  }
}
return ret;
}

/**
 * @brief  DeInitializes I2C HAL.
 * @retval BSP status
 */
int32_t BSP_I2C5_DeInit(void) {
  int32_t ret = BSP_ERROR_NONE;

  I2c5InitCounter--;

  if (I2c5InitCounter == 0U) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
    I2C5_MspDeInit(&hbus_i2c5);
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */

    /* Init the I2C */
    if (HAL_I2C_DeInit(&hbus_i2c5) != HAL_OK) {
      ret = BSP_ERROR_BUS_FAILURE;
    }
  }

  return ret;
}

/**
 * @brief  MX I2C5 initialization.
 * @param  hI2c I2C handle
 * @param  timing I2C timing
 * @retval HAL status
 */
__weak HAL_StatusTypeDef MX_I2C5_Init(I2C_HandleTypeDef *hI2c,
                                      uint32_t timing) {
  HAL_StatusTypeDef status = HAL_OK;

  hI2c->Init.Timing = timing;
  hI2c->Init.OwnAddress1 = 0;
  hI2c->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hI2c->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hI2c->Init.OwnAddress2 = 0;
  hI2c->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hI2c->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hI2c->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(hI2c) != HAL_OK) {
    status = HAL_ERROR;
  } else {
    uint32_t analog_filter;

    analog_filter = I2C_ANALOGFILTER_ENABLE;
    if (HAL_I2CEx_ConfigAnalogFilter(hI2c, analog_filter) != HAL_OK) {
      status = HAL_ERROR;
    } else {
      if (HAL_I2CEx_ConfigDigitalFilter(hI2c, I2C_DIGITAL_FILTER_COEF) !=
          HAL_OK) {
        status = HAL_ERROR;
      }
    }
  }

  return status;
}

/**
 * @brief  Write a 8bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C5_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                          uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 8bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C5_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                         uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Write a 16bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C5_WriteReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                            uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 16bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C5_ReadReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                           uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C5_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_Recv(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Send data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C5_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C5_Send(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c5) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Checks if target device is ready for communication.
 * @note   This function is used with Memory devices
 * @param  DevAddr  Target device address
 * @param  Trials      Number of trials
 * @retval BSP status
 */
int32_t BSP_I2C5_IsReady(uint16_t DevAddr, uint32_t Trials) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (HAL_I2C_IsDeviceReady(&hbus_i2c5, DevAddr, Trials, 1000) != HAL_OK) {
    ret = BSP_ERROR_BUSY;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
/**
 * @brief Register Default I2C5 Bus Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_I2C5_RegisterDefaultMspCallbacks(void) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c5);

  /* Register default MspInit/MspDeInit Callback */
  if (HAL_I2C_RegisterCallback(&hbus_i2c5, HAL_I2C_MSPINIT_CB_ID,
                               I2C5_MspInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c5, HAL_I2C_MSPDEINIT_CB_ID,
                                      I2C5_MspDeInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c5MspCbValid = 1U;
  }

#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */
  /* BSP status */
  return ret;
}

/**
 * @brief Register I2C5 Bus Msp Callback registering
 * @param Callbacks     pointer to I2C5 MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_I2C5_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c5);

  /* Register MspInit/MspDeInit Callbacks */
  if (HAL_I2C_RegisterCallback(&hbus_i2c5, HAL_I2C_MSPINIT_CB_ID,
                               Callback->pMspI2cInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c5, HAL_I2C_MSPDEINIT_CB_ID,
                                      Callback->pMspI2cDeInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c5MspCbValid = 1U;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  /* BSP status */
  return ret;
}
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS */

/**
 * @brief  Initializes I2C4 HAL.
 * @retval BSP status
 */
int32_t BSP_I2C4_Init(void) {
  int32_t ret = BSP_ERROR_NONE;

  hbus_i2c4.Instance = BUS_I2C4;

  if (I2c4InitCounter == 0U) {
    I2c4InitCounter++;

    if (HAL_I2C_GetState(&hbus_i2c4) == HAL_I2C_STATE_RESET) {
#if defined(BSP_USE_CMSIS_OS)
      if (BspI2cSemaphore == NULL) {
        /* Create semaphore to prevent multiple I2C access */
        osSemaphoreDef(BSP_I2C_SEM);
        BspI2cSemaphore = osSemaphoreCreate(osSemaphore(BSP_I2C_SEM), 1);
      }
#endif /* BSP_USE_CMSIS_OS */
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
      /* Init the I2C4 Msp */
      I2C4_MspInit(&hbus_i2c4);
#else
        if (IsI2c4MspCbValid == 0U) {
          if (BSP_I2C4_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) {
            ret = BSP_ERROR_MSP_FAILURE;
          }
        }
        if (ret == BSP_ERROR_NONE) {
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */
      if (MX_I2C4_Init(&hbus_i2c4, I2C_GetTiming(HAL_RCC_GetPCLK1Freq(),
                                                 BUS_I2C4_FREQUENCY)) !=
          HAL_OK) {
        ret = BSP_ERROR_BUS_FAILURE;
      }
#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
    }
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS > 0) */
  }
}
return ret;
}

/**
 * @brief  DeInitializes I2C HAL.
 * @retval BSP status
 */
int32_t BSP_I2C4_DeInit(void) {
  int32_t ret = BSP_ERROR_NONE;

  I2c4InitCounter--;

  if (I2c4InitCounter == 0U) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
    I2C4_MspDeInit(&hbus_i2c4);
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */

    /* Init the I2C */
    if (HAL_I2C_DeInit(&hbus_i2c4) != HAL_OK) {
      ret = BSP_ERROR_BUS_FAILURE;
    }
  }

  return ret;
}

/**
 * @brief  MX I2C4 initialization.
 * @param  hI2c I2C handle
 * @param  timing I2C timing
 * @retval HAL status
 */
__weak HAL_StatusTypeDef MX_I2C4_Init(I2C_HandleTypeDef *hI2c,
                                      uint32_t timing) {
  HAL_StatusTypeDef status = HAL_OK;

  hI2c->Init.Timing = timing;
  hI2c->Init.OwnAddress1 = 0;
  hI2c->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hI2c->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hI2c->Init.OwnAddress2 = 0;
  hI2c->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hI2c->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hI2c->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(hI2c) != HAL_OK) {
    status = HAL_ERROR;
  } else {
    uint32_t analog_filter;

    analog_filter = I2C_ANALOGFILTER_ENABLE;
    if (HAL_I2CEx_ConfigAnalogFilter(hI2c, analog_filter) != HAL_OK) {
      status = HAL_ERROR;
    } else {
      if (HAL_I2CEx_ConfigDigitalFilter(hI2c, I2C_DIGITAL_FILTER_COEF) !=
          HAL_OK) {
        status = HAL_ERROR;
      }
    }
  }

  return status;
}

/**
 * @brief  Write a 8bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C4_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                          uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 8bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C4_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                         uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Write a 16bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C4_WriteReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                            uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 16bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C4_ReadReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                           uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C4_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_Recv(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Send data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C4_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C4_Send(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c4) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Checks if target device is ready for communication.
 * @note   This function is used with Memory devices
 * @param  DevAddr  Target device address
 * @param  Trials      Number of trials
 * @retval BSP status
 */
int32_t BSP_I2C4_IsReady(uint16_t DevAddr, uint32_t Trials) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (HAL_I2C_IsDeviceReady(&hbus_i2c4, DevAddr, Trials, 1000) != HAL_OK) {
    ret = BSP_ERROR_BUSY;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
/**
 * @brief Register Default I2C4 Bus Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_I2C4_RegisterDefaultMspCallbacks(void) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c4);

  /* Register default MspInit/MspDeInit Callback */
  if (HAL_I2C_RegisterCallback(&hbus_i2c4, HAL_I2C_MSPINIT_CB_ID,
                               I2C4_MspInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c4, HAL_I2C_MSPDEINIT_CB_ID,
                                      I2C4_MspDeInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c4MspCbValid = 1U;
  }

#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */
  /* BSP status */
  return ret;
}

/**
 * @brief Register I2C4 Bus Msp Callback registering
 * @param Callbacks     pointer to I2C4 MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_I2C4_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c4);

  /* Register MspInit/MspDeInit Callbacks */
  if (HAL_I2C_RegisterCallback(&hbus_i2c4, HAL_I2C_MSPINIT_CB_ID,
                               Callback->pMspI2cInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c4, HAL_I2C_MSPDEINIT_CB_ID,
                                      Callback->pMspI2cDeInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c4MspCbValid = 1U;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  /* BSP status */
  return ret;
}
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS */

/***************************************************************/
/**
 * @brief  Initializes I2C3 HAL.
 * @retval BSP status
 */
int32_t BSP_I2C3_Init(void) {
  int32_t ret = BSP_ERROR_NONE;

  hbus_i2c3.Instance = BUS_I2C3;

  if (I2c3InitCounter == 0U) {
    I2c3InitCounter++;

    if (HAL_I2C_GetState(&hbus_i2c3) == HAL_I2C_STATE_RESET) {
#if defined(BSP_USE_CMSIS_OS)
      if (BspI2cSemaphore == NULL) {
        /* Create semaphore to prevent multiple I2C access */
        osSemaphoreDef(BSP_I2C_SEM);
        BspI2cSemaphore = osSemaphoreCreate(osSemaphore(BSP_I2C_SEM), 1);
      }
#endif /* BSP_USE_CMSIS_OS */
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
      /* Init the I2C3 Msp */
      I2C3_MspInit(&hbus_i2c3);
#else
          if (IsI2c3MspCbValid == 0U) {
            if (BSP_I2C3_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) {
              ret = BSP_ERROR_MSP_FAILURE;
            }
          }
          if (ret == BSP_ERROR_NONE) {
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS == 0 */
      if (MX_I2C3_Init(&hbus_i2c3, I2C_GetTiming(HAL_RCC_GetPCLK1Freq(),
                                                 BUS_I2C3_FREQUENCY)) !=
          HAL_OK) {
        ret = BSP_ERROR_BUS_FAILURE;
      }
#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
    }
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS > 0 */
  }
}
return ret;
}

/**
 * @brief  DeInitializes I2C3 HAL.
 * @retval BSP status
 */
int32_t BSP_I2C3_DeInit(void) {
  int32_t ret = BSP_ERROR_NONE;

  I2c3InitCounter--;

  if (I2c3InitCounter == 0U) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
    I2C3_MspDeInit(&hbus_i2c3);
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */

    /* Init the I2C */
    if (HAL_I2C_DeInit(&hbus_i2c3) != HAL_OK) {
      ret = BSP_ERROR_BUS_FAILURE;
    }
  }

  return ret;
}

/**
 * @brief  MX I2C3 initialization.
 * @param  hI2c I2C handle
 * @param  timing I2C timing
 * @retval HAL status
 */
__weak HAL_StatusTypeDef MX_I2C3_Init(I2C_HandleTypeDef *hI2c,
                                      uint32_t timing) {
  HAL_StatusTypeDef status = HAL_OK;

  hI2c->Init.Timing = timing;
  hI2c->Init.OwnAddress1 = 0;
  hI2c->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hI2c->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hI2c->Init.OwnAddress2 = 0;
  hI2c->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hI2c->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hI2c->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(hI2c) != HAL_OK) {
    status = HAL_ERROR;
  } else {
    uint32_t analog_filter;

    analog_filter = I2C_ANALOGFILTER_ENABLE;
    if (HAL_I2CEx_ConfigAnalogFilter(hI2c, analog_filter) != HAL_OK) {
      status = HAL_ERROR;
    } else {
      if (HAL_I2CEx_ConfigDigitalFilter(hI2c, I2C_DIGITAL_FILTER_COEF) !=
          HAL_OK) {
        status = HAL_ERROR;
      }
    }
  }

  return status;
}

/**
 * @brief  Write a 8bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C3_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                          uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 8bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C3_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                         uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Write a 16bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C3_WriteReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                            uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 16bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C3_ReadReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                           uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C3_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_Recv(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Send data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C3_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C3_Send(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c3) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Checks if target device is ready for communication.
 * @note   This function is used with Memory devices
 * @param  DevAddr  Target device address
 * @param  Trials      Number of trials
 * @retval BSP status
 */
int32_t BSP_I2C3_IsReady(uint16_t DevAddr, uint32_t Trials) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (HAL_I2C_IsDeviceReady(&hbus_i2c3, DevAddr, Trials, 1000) != HAL_OK) {
    ret = BSP_ERROR_BUSY;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Initializes I2C2 HAL.
 * @retval BSP status
 */
int32_t BSP_I2C2_Init(void) {
  int32_t ret = BSP_ERROR_NONE;

  hbus_i2c2.Instance = BUS_I2C2;

  if (I2c2InitCounter == 0U) {
    I2c2InitCounter++;

    if (HAL_I2C_GetState(&hbus_i2c2) == HAL_I2C_STATE_RESET) {
#if defined(BSP_USE_CMSIS_OS)
      if (BspI2cSemaphore == NULL) {
        /* Create semaphore to prevent multiple I2C access */
        osSemaphoreDef(BSP_I2C_SEM);
        BspI2cSemaphore = osSemaphoreCreate(osSemaphore(BSP_I2C_SEM), 1);
      }
#endif /* BSP_USE_CMSIS_OS */
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
      /* Init the I2C2 Msp */
      I2C2_MspInit(&hbus_i2c2);
#else
            if (IsI2c2MspCbValid == 0U) {
              if (BSP_I2C2_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) {
                ret = BSP_ERROR_MSP_FAILURE;
              }
            }
            if (ret == BSP_ERROR_NONE) {
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS == 0 */
      if (MX_I2C2_Init(&hbus_i2c2, I2C_GetTiming(HAL_RCC_GetPCLK1Freq(),
                                                 BUS_I2C2_FREQUENCY)) !=
          HAL_OK) {
        ret = BSP_ERROR_BUS_FAILURE;
      }
#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
    }
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS > 0 */
  }
}
return ret;
}

/**
 * @brief  DeInitializes I2C HAL.
 * @retval BSP status
 */
int32_t BSP_I2C2_DeInit(void) {
  int32_t ret = BSP_ERROR_NONE;

  I2c2InitCounter--;

  if (I2c2InitCounter == 0U) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0)
    I2C2_MspDeInit(&hbus_i2c2);
#endif /* (USE_HAL_I2C_REGISTER_CALLBACKS == 0) */

    /* Init the I2C */
    if (HAL_I2C_DeInit(&hbus_i2c2) != HAL_OK) {
      ret = BSP_ERROR_BUS_FAILURE;
    }
  }

  return ret;
}

/**
 * @brief  MX I2C2 initialization.
 * @param  hI2c I2C handle
 * @param  timing I2C timing
 * @retval HAL status
 */
__weak HAL_StatusTypeDef MX_I2C2_Init(I2C_HandleTypeDef *hI2c,
                                      uint32_t timing) {
  HAL_StatusTypeDef status = HAL_OK;

  hI2c->Init.Timing = timing;
  hI2c->Init.OwnAddress1 = 0;
  hI2c->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hI2c->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hI2c->Init.OwnAddress2 = 0;
  hI2c->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hI2c->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hI2c->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(hI2c) != HAL_OK) {
    status = HAL_ERROR;
  } else {
    uint32_t analog_filter;

    analog_filter = I2C_ANALOGFILTER_ENABLE;
    if (HAL_I2CEx_ConfigAnalogFilter(hI2c, analog_filter) != HAL_OK) {
      status = HAL_ERROR;
    } else {
      if (HAL_I2CEx_ConfigDigitalFilter(hI2c, I2C_DIGITAL_FILTER_COEF) !=
          HAL_OK) {
        status = HAL_ERROR;
      }
    }
  }

  return status;
}

/**
 * @brief  Write a 8bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C2_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                          uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 8bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C2_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                         uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Write a 16bit value in a register of the device through BUS.
 * @param  DevAddr Device address on Bus.
 * @param  Reg    The target register address to write
 * @param  pData  The target register value to be written
 * @param  Length buffer size to be written
 * @retval BSP status
 */
int32_t BSP_I2C2_WriteReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                            uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_WriteReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read a 16bit register of the device through BUS
 * @param  DevAddr Device address on BUS
 * @param  Reg     The target register address to read
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C2_ReadReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                           uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_ReadReg(DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Read data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C2_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_Recv(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Send data
 * @param  DevAddr Device address on BUS
 * @param  pData   Pointer to data buffer
 * @param  Length  Length of the data
 * @retval BSP status
 */
int32_t BSP_I2C2_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  int32_t ret;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (I2C2_Send(DevAddr, pData, Length) == 0) {
    ret = BSP_ERROR_NONE;
  } else {
    if (HAL_I2C_GetError(&hbus_i2c2) == HAL_I2C_ERROR_AF) {
      ret = BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    } else {
      ret = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Checks if target device is ready for communication.
 * @note   This function is used with Memory devices
 * @param  DevAddr  Target device address
 * @param  Trials      Number of trials
 * @retval BSP status
 */
int32_t BSP_I2C2_IsReady(uint16_t DevAddr, uint32_t Trials) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  if (HAL_I2C_IsDeviceReady(&hbus_i2c2, DevAddr, Trials, 1000) != HAL_OK) {
    ret = BSP_ERROR_BUSY;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  return ret;
}

/**
 * @brief  Delay function
 * @retval Tick value
 */
int32_t BSP_GetTick(void) { return (int32_t)HAL_GetTick(); }

#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
/**
 * @brief Register Default I2C2 Bus Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_I2C2_RegisterDefaultMspCallbacks(void) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c2);

  /* Register default MspInit/MspDeInit Callback */
  if (HAL_I2C_RegisterCallback(&hbus_i2c2, HAL_I2C_MSPINIT_CB_ID,
                               I2C2_MspInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c2, HAL_I2C_MSPDEINIT_CB_ID,
                                      I2C2_MspDeInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c2MspCbValid = 1U;
  }

#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */
  /* BSP status */
  return ret;
}

/**
 * @brief Register I2C2 Bus Msp Callback registering
 * @param Callbacks     pointer to I2C2 MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_I2C2_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c2);

  /* Register MspInit/MspDeInit Callbacks */
  if (HAL_I2C_RegisterCallback(&hbus_i2c2, HAL_I2C_MSPINIT_CB_ID,
                               Callback->pMspI2cInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c2, HAL_I2C_MSPDEINIT_CB_ID,
                                      Callback->pMspI2cDeInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c2MspCbValid = 1U;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  /* BSP status */
  return ret;
}

/**
 * @brief Register Default I2C3 Bus Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_I2C3_RegisterDefaultMspCallbacks(void) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c3);

  /* Register default MspInit/MspDeInit Callback */
  if (HAL_I2C_RegisterCallback(&hbus_i2c3, HAL_I2C_MSPINIT_CB_ID,
                               I2C3_MspInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c3, HAL_I2C_MSPDEINIT_CB_ID,
                                      I2C3_MspDeInit) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c3MspCbValid = 1U;
  }

#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */
  /* BSP status */
  return ret;
}

/**
 * @brief Register I2C3 Bus Msp Callback registering
 * @param Callbacks     pointer to I2C3 MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_I2C3_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback) {
  int32_t ret = BSP_ERROR_NONE;

#if defined(BSP_USE_CMSIS_OS)
  /* Get semaphore to prevent multiple I2C access */
  osSemaphoreWait(BspI2cSemaphore, osWaitForever);
#endif /* BSP_USE_CMSIS_OS */
  __HAL_I2C_RESET_HANDLE_STATE(&hbus_i2c3);

  /* Register MspInit/MspDeInit Callbacks */
  if (HAL_I2C_RegisterCallback(&hbus_i2c3, HAL_I2C_MSPINIT_CB_ID,
                               Callback->pMspI2cInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else if (HAL_I2C_RegisterCallback(&hbus_i2c3, HAL_I2C_MSPDEINIT_CB_ID,
                                      Callback->pMspI2cDeInitCb) != HAL_OK) {
    ret = BSP_ERROR_PERIPH_FAILURE;
  } else {
    IsI2c3MspCbValid = 1U;
  }
#if defined(BSP_USE_CMSIS_OS)
  /* Release semaphore to prevent multiple I2C access */
  osSemaphoreRelease(BspI2cSemaphore);
#endif /* BSP_USE_CMSIS_OS */

  /* BSP status */
  return ret;
}

#endif /* USE_HAL_I2C_REGISTER_CALLBACKS */
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_BUS_Private_Functions BUS Private Functions
 * @{
 */
/**
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

/**
 * @brief  Initializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C5_MspInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /*** Configure the GPIOs ***/
  /* Enable SCL GPIO clock */
  BUS_I2C5_SCL_GPIO_CLK_ENABLE();
  /* Enable SDA GPIO clock */
  BUS_I2C5_SDA_GPIO_CLK_ENABLE();

  /* Configure I2C Tx as alternate function */
  gpio_init_structure.Pin = BUS_I2C5_SCL_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C5_SCL_AF;
  HAL_GPIO_Init(BUS_I2C5_SCL_GPIO_PORT, &gpio_init_structure);

  /* Configure I2C Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C5_SDA_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C5_SDA_AF;
  HAL_GPIO_Init(BUS_I2C5_SDA_GPIO_PORT, &gpio_init_structure);

  /*** Configure the I2C peripheral ***/
  /* Enable I2C clock */
  BUS_I2C5_CLK_ENABLE();

  /* Force the I2C peripheral clock reset */
  BUS_I2C5_FORCE_RESET();

  /* Release the I2C peripheral clock reset */
  BUS_I2C5_RELEASE_RESET();
}

/**
 * @brief  DeInitializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C5_MspDeInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /* Configure I2C Tx, Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C5_SCL_PIN;
  HAL_GPIO_DeInit(BUS_I2C5_SCL_GPIO_PORT, gpio_init_structure.Pin);
  gpio_init_structure.Pin = BUS_I2C5_SDA_PIN;
  HAL_GPIO_DeInit(BUS_I2C5_SDA_GPIO_PORT, gpio_init_structure.Pin);

  /* Disable I2C clock */
  BUS_I2C5_CLK_DISABLE();
}

/**
 * @brief  Write a value in a register of the device through BUS.
 * @param  DevAddr    Device address on Bus.
 * @param  Reg        The target register address to write
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C5_WriteReg(uint16_t DevAddr, uint16_t Reg,
                             uint16_t MemAddSize, uint8_t *pData,
                             uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hbus_i2c5, DevAddr, Reg, MemAddSize, pData, Length,
                        10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Read a register of the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  Reg        The target register address to read
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C5_ReadReg(uint16_t DevAddr, uint16_t Reg, uint16_t MemAddSize,
                            uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hbus_i2c5, DevAddr, Reg, MemAddSize, pData, Length,
                       10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Receive data from the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be received
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C5_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Receive(&hbus_i2c5, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Send data to the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be sent
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C5_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Transmit(&hbus_i2c5, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Initializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C4_MspInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /*** Configure the GPIOs ***/
  /* Enable SCL GPIO clock */
  BUS_I2C4_SCL_GPIO_CLK_ENABLE();
  /* Enable SDA GPIO clock */
  BUS_I2C4_SDA_GPIO_CLK_ENABLE();

  /* Configure I2C Tx as alternate function */
  gpio_init_structure.Pin = BUS_I2C4_SCL_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C4_SCL_AF;
  HAL_GPIO_Init(BUS_I2C4_SCL_GPIO_PORT, &gpio_init_structure);

  /* Configure I2C Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C4_SDA_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C4_SDA_AF;
  HAL_GPIO_Init(BUS_I2C4_SDA_GPIO_PORT, &gpio_init_structure);

  /*** Configure the I2C peripheral ***/
  /* Enable I2C clock */
  BUS_I2C4_CLK_ENABLE();

  /* Force the I2C peripheral clock reset */
  BUS_I2C4_FORCE_RESET();

  /* Release the I2C peripheral clock reset */
  BUS_I2C4_RELEASE_RESET();
}

/**
 * @brief  DeInitializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C4_MspDeInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /* Configure I2C Tx, Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C4_SCL_PIN;
  HAL_GPIO_DeInit(BUS_I2C4_SCL_GPIO_PORT, gpio_init_structure.Pin);
  gpio_init_structure.Pin = BUS_I2C4_SDA_PIN;
  HAL_GPIO_DeInit(BUS_I2C4_SDA_GPIO_PORT, gpio_init_structure.Pin);

  /* Disable I2C clock */
  BUS_I2C4_CLK_DISABLE();
}

/**
 * @brief  Write a value in a register of the device through BUS.
 * @param  DevAddr    Device address on Bus.
 * @param  Reg        The target register address to write
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C4_WriteReg(uint16_t DevAddr, uint16_t Reg,
                             uint16_t MemAddSize, uint8_t *pData,
                             uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hbus_i2c4, DevAddr, Reg, MemAddSize, pData, Length,
                        10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Read a register of the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  Reg        The target register address to read
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C4_ReadReg(uint16_t DevAddr, uint16_t Reg, uint16_t MemAddSize,
                            uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hbus_i2c4, DevAddr, Reg, MemAddSize, pData, Length,
                       10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Receive data from the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be received
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C4_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Receive(&hbus_i2c4, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Send data to the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be sent
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C4_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Transmit(&hbus_i2c4, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Initializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C2_MspInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /*** Configure the GPIOs ***/
  /* Enable SCL GPIO clock */
  BUS_I2C2_SCL_GPIO_CLK_ENABLE();
  /* Enable SDA GPIO clock */
  BUS_I2C2_SDA_GPIO_CLK_ENABLE();

  /* Configure I2C Tx as alternate function */
  gpio_init_structure.Pin = BUS_I2C2_SCL_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C2_SCL_AF;
  HAL_GPIO_Init(BUS_I2C2_SCL_GPIO_PORT, &gpio_init_structure);

  /* Configure I2C Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C2_SDA_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C2_SDA_AF;
  HAL_GPIO_Init(BUS_I2C2_SDA_GPIO_PORT, &gpio_init_structure);

  /*** Configure the I2C peripheral ***/
  /* Enable I2C clock */
  BUS_I2C2_CLK_ENABLE();

  /* Force the I2C peripheral clock reset */
  BUS_I2C2_FORCE_RESET();

  /* Release the I2C peripheral clock reset */
  BUS_I2C2_RELEASE_RESET();
}

/**
 * @brief  DeInitializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C2_MspDeInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /* Configure I2C Tx, Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C2_SCL_PIN;
  HAL_GPIO_DeInit(BUS_I2C2_SCL_GPIO_PORT, gpio_init_structure.Pin);
  gpio_init_structure.Pin = BUS_I2C2_SDA_PIN;
  HAL_GPIO_DeInit(BUS_I2C2_SDA_GPIO_PORT, gpio_init_structure.Pin);

  /* Disable I2C clock */
  BUS_I2C2_CLK_DISABLE();
}

/**
 * @brief  Write a value in a register of the device through BUS.
 * @param  DevAddr    Device address on Bus.
 * @param  Reg        The target register address to write
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C2_WriteReg(uint16_t DevAddr, uint16_t Reg,
                             uint16_t MemAddSize, uint8_t *pData,
                             uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hbus_i2c2, DevAddr, Reg, MemAddSize, pData, Length,
                        10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Read a register of the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  Reg        The target register address to read
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C2_ReadReg(uint16_t DevAddr, uint16_t Reg, uint16_t MemAddSize,
                            uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hbus_i2c2, DevAddr, Reg, MemAddSize, pData, Length,
                       10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Receive data from the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be received
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C2_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Receive(&hbus_i2c2, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Send data to the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be sent
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C2_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Transmit(&hbus_i2c2, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Initializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C3_MspInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /*** Configure the GPIOs ***/
  /* Enable SCL GPIO clock */
  BUS_I2C3_SCL_GPIO_CLK_ENABLE();
  /* Enable SDA GPIO clock */
  BUS_I2C3_SDA_GPIO_CLK_ENABLE();

  /* Configure I2C Tx as alternate function */
  gpio_init_structure.Pin = BUS_I2C3_SCL_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C3_SCL_AF;
  HAL_GPIO_Init(BUS_I2C3_SCL_GPIO_PORT, &gpio_init_structure);

  /* Configure I2C Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C3_SDA_PIN;
  gpio_init_structure.Mode = GPIO_MODE_AF_OD;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Alternate = BUS_I2C3_SDA_AF;
  HAL_GPIO_Init(BUS_I2C3_SDA_GPIO_PORT, &gpio_init_structure);

  /*** Configure the I2C peripheral ***/
  /* Enable I2C clock */
  BUS_I2C3_CLK_ENABLE();

  /* Force the I2C peripheral clock reset */
  BUS_I2C3_FORCE_RESET();

  /* Release the I2C peripheral clock reset */
  BUS_I2C3_RELEASE_RESET();
}

/**
 * @brief  DeInitializes I2C MSP.
 * @param  hI2c  I2C handler
 * @retval None
 */
static void I2C3_MspDeInit(I2C_HandleTypeDef *hI2c) {
  GPIO_InitTypeDef gpio_init_structure;

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hI2c);

  /* Configure I2C Tx, Rx as alternate function */
  gpio_init_structure.Pin = BUS_I2C3_SCL_PIN;
  HAL_GPIO_DeInit(BUS_I2C3_SCL_GPIO_PORT, gpio_init_structure.Pin);
  gpio_init_structure.Pin = BUS_I2C3_SDA_PIN;
  HAL_GPIO_DeInit(BUS_I2C3_SDA_GPIO_PORT, gpio_init_structure.Pin);

  /* Disable I2C clock */
  BUS_I2C3_CLK_DISABLE();
}

/**
 * @brief  Write a value in a register of the device through BUS.
 * @param  DevAddr    Device address on Bus.
 * @param  Reg        The target register address to write
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C3_WriteReg(uint16_t DevAddr, uint16_t Reg,
                             uint16_t MemAddSize, uint8_t *pData,
                             uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hbus_i2c3, DevAddr, Reg, MemAddSize, pData, Length,
                        10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Read a register of the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  Reg        The target register address to read
 * @param  MemAddSize Size of internal memory address
 * @param  pData      The target register value to be written
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C3_ReadReg(uint16_t DevAddr, uint16_t Reg, uint16_t MemAddSize,
                            uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hbus_i2c3, DevAddr, Reg, MemAddSize, pData, Length,
                       10000) == HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Receive data from the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be received
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C3_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Receive(&hbus_i2c3, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @brief  Send data to the device through BUS
 * @param  DevAddr    Device address on BUS
 * @param  pData      The target register value to be sent
 * @param  Length     data length in bytes
 * @retval BSP status
 */
static int32_t I2C3_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Master_Transmit(&hbus_i2c3, DevAddr, pData, Length, 10000) ==
      HAL_OK) {
    return BSP_ERROR_NONE;
  }

  return BSP_ERROR_BUS_FAILURE;
}

/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_BUS_Exported_Functions
 * @{
 */
int32_t BSP_I2C5_Init(void);
int32_t BSP_I2C5_DeInit(void);
int32_t BSP_I2C5_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                          uint16_t Length);
int32_t BSP_I2C5_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData,
                         uint16_t Length);
int32_t BSP_I2C5_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);

int32_t BSP_GetTick(void);

#if (USE_HAL_I2C_REGISTER_CALLBACKS > 0)
int32_t BSP_I2C5_RegisterDefaultMspCallbacks(void);
int32_t BSP_I2C5_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback);
int32_t BSP_I2C4_RegisterDefaultMspCallbacks(void);
int32_t BSP_I2C4_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback);
int32_t BSP_I2C2_RegisterDefaultMspCallbacks(void);
int32_t BSP_I2C2_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback);
int32_t BSP_I2C3_RegisterDefaultMspCallbacks(void);
int32_t BSP_I2C3_RegisterMspCallbacks(BSP_I2C_Cb_t *Callback);
#endif /* USE_HAL_I2C_REGISTER_CALLBACKS */

/**
 * @}
 */
typedef int32_t (*SITRONIX_Write_Func)(void *, uint8_t, uint8_t *, uint16_t);
typedef int32_t (*SITRONIX_Read_Func)(void *, uint8_t, uint8_t *, uint16_t);
typedef int32_t (*SITRONIX_Recv_Func)(void *, uint8_t *, uint16_t);

/** @defgroup SITRONIX_Imported_Globals SITRONIX Imported Globals
 * @{
 */
typedef struct {
  SITRONIX_Write_Func WriteReg;
  SITRONIX_Read_Func ReadReg;
  SITRONIX_Recv_Func ReadData;
  void *handle;
} sitronix_ctx_t;

/*******************************************************************************
 * Function Name : sitronix_read_reg
 * Description   : Generic Reading function. It must be full-filled with either
 *                 I2C or SPI reading functions
 * Input         : Register Address, length of buffer
 * Output        : pdata Read
 *******************************************************************************/
int32_t sitronix_read_reg(sitronix_ctx_t *ctx, uint8_t reg, uint8_t *pdata,
                          uint16_t length) {
  return ctx->ReadReg(ctx->handle, reg, pdata, length);
}

/*******************************************************************************
 * Function Name : sitronix_write_reg
 * Description   : Generic Writing function. It must be full-filled with either
 *                 I2C or SPI writing function
 * Input         : Register Address, pdata to be written, length of buffer
 * Output        : None
 *******************************************************************************/
int32_t sitronix_write_reg(sitronix_ctx_t *ctx, uint8_t reg, uint8_t *pdata,
                           uint16_t length) {
  return ctx->WriteReg(ctx->handle, reg, pdata, length);
}

/*******************************************************************************
 * Function Name : sitronix_read_data
 * Description   : Generic Reading function. It must be full-filled with either
 *                 I2C or SPI reading functions
 * Input         : Register Address, length of buffer
 * Output        : pdata Read
 *******************************************************************************/
int32_t sitronix_read_data(sitronix_ctx_t *ctx, uint8_t *pdata,
                           uint16_t length) {
  return ctx->ReadData(ctx->handle, pdata, length);
}

/* Includes ------------------------------------------------------------------*/
/* Macros --------------------------------------------------------------------*/
/* Exported types ------------------------------------------------------------*/
/* Exported constants --------------------------------------------------------*/
#define SITRONIX_MAX_X_LENGTH 480U
#define SITRONIX_MAX_Y_LENGTH 480U

/** @defgroup SITRONIX_Exported_Constants SITRONIX Exported Constants
 * @{
 */
#define SITRONIX_OK (0)
#define SITRONIX_ERROR (-1)

/* Max detectable simultaneous touches */
#define SITRONIX_MAX_DETECTABLE_TOUCH 10U

/* Touch FT6XX6 IDs */
#define SITRONIX_ID 0x02U

/* Values Pn_XH and Pn_YH related */
#define SITRONIX_TOUCH_EVT_FLAG_PRESS_DOWN 0x20U
#define SITRONIX_TOUCH_EVT_FLAG_LIFT_UP 0x60U
#define SITRONIX_TOUCH_EVT_FLAG_CONTACT 0x80U
#define SITRONIX_TOUCH_EVT_FLAG_NO_EVENT 0x00U
#define SITRONIX_TOUCH_POS_MSB_MASK 0x07U
#define SITRONIX_TOUCH_POS_LSB_MASK 0x70U

/* Point 1 registers */
#define SITRONIX_P1_XH_REG 0x09U
#define SITRONIX_P1_XL_REG 0x0AU
#define SITRONIX_P1_YH_REG 0x0BU
#define SITRONIX_P1_YL_REG 0x0CU

/**
 * @}
 */

/* Exported types ------------------------------------------------------------*/

/** @defgroup SITRONIX_Exported_Types SITRONIX Exported Types
 * @{
 */
typedef struct {
  uint32_t Radian;
  uint32_t OffsetLeftRight;
  uint32_t OffsetUpDown;
  uint32_t DistanceLeftRight;
  uint32_t DistanceUpDown;
  uint32_t DistanceZoom;
} SITRONIX_Gesture_Init_t;

typedef int32_t (*SITRONIX_Init_Func)(void);
typedef int32_t (*SITRONIX_DeInit_Func)(void);
typedef int32_t (*SITRONIX_GetTick_Func)(void);
typedef int32_t (*SITRONIX_Delay_Func)(uint32_t);
typedef int32_t (*SITRONIX_WriteReg_Func)(uint16_t, uint16_t, uint8_t *,
                                          uint16_t);
typedef int32_t (*SITRONIX_ReadReg_Func)(uint16_t, uint16_t, uint8_t *,
                                         uint16_t);
typedef int32_t (*SITRONIX_ReadData_Func)(uint16_t, uint8_t *, uint16_t);

typedef struct {
  SITRONIX_Init_Func Init;
  SITRONIX_DeInit_Func DeInit;
  uint16_t Address;
  SITRONIX_WriteReg_Func WriteReg;
  SITRONIX_ReadReg_Func ReadReg;
  SITRONIX_ReadData_Func ReadData;
  SITRONIX_GetTick_Func GetTick;
} SITRONIX_IO_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX;
  uint32_t TouchY;
} SITRONIX_State_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchY[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchWeight[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchEvent[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchArea[SITRONIX_MAX_DETECTABLE_TOUCH];
} SITRONIX_MultiTouch_State_t;

typedef struct {
  SITRONIX_IO_t IO;
  sitronix_ctx_t Ctx;
  uint8_t IsInitialized;
} SITRONIX_Object_t;

typedef struct {
  uint8_t MultiTouch;
  uint8_t Gesture;
  uint8_t MaxTouch;
  uint32_t MaxXl;
  uint32_t MaxYl;
} SITRONIX_Capabilities_t;

typedef struct {
  int32_t (*Init)(SITRONIX_Object_t *);
  int32_t (*DeInit)(SITRONIX_Object_t *);
  int32_t (*GestureConfig)(SITRONIX_Object_t *, SITRONIX_Gesture_Init_t *);
  int32_t (*ReadID)(SITRONIX_Object_t *, uint32_t *);
  int32_t (*GetState)(SITRONIX_Object_t *, SITRONIX_State_t *);
  int32_t (*GetMultiTouchState)(SITRONIX_Object_t *,
                                SITRONIX_MultiTouch_State_t *);
  int32_t (*GetGesture)(SITRONIX_Object_t *, uint8_t *);
  int32_t (*GetCapabilities)(SITRONIX_Object_t *, SITRONIX_Capabilities_t *);
  int32_t (*EnableIT)(SITRONIX_Object_t *);
  int32_t (*DisableIT)(SITRONIX_Object_t *);
  int32_t (*ClearIT)(SITRONIX_Object_t *);
  int32_t (*ITStatus)(SITRONIX_Object_t *);
} SITRONIX_TS_Drv_t;

int32_t SITRONIX_RegisterBusIO(SITRONIX_Object_t *pObj, SITRONIX_IO_t *pIO);
int32_t SITRONIX_Init(SITRONIX_Object_t *pObj);
int32_t SITRONIX_DeInit(SITRONIX_Object_t *pObj);
int32_t SITRONIX_GestureConfig(SITRONIX_Object_t *pObj,
                               SITRONIX_Gesture_Init_t *GestureInit);
int32_t SITRONIX_ReadID(SITRONIX_Object_t *pObj, uint32_t *Id);
int32_t SITRONIX_GetState(SITRONIX_Object_t *pObj, SITRONIX_State_t *State);
int32_t SITRONIX_GetMultiTouchState(SITRONIX_Object_t *pObj,
                                    SITRONIX_MultiTouch_State_t *State);
int32_t SITRONIX_GetGesture(SITRONIX_Object_t *pObj, uint8_t *GestureId);
int32_t SITRONIX_EnableIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_DisableIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_ITStatus(SITRONIX_Object_t *pObj);
int32_t SITRONIX_ClearIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_GetCapabilities(SITRONIX_Object_t *pObj,
                                 SITRONIX_Capabilities_t *Capabilities);

/* Touch screen driver structure initialization */
SITRONIX_TS_Drv_t SITRONIX_TS_Driver = {
    SITRONIX_Init,       SITRONIX_DeInit,          SITRONIX_GestureConfig,
    SITRONIX_ReadID,     SITRONIX_GetState,        SITRONIX_GetMultiTouchState,
    SITRONIX_GetGesture, SITRONIX_GetCapabilities, SITRONIX_EnableIT,
    SITRONIX_DisableIT,  SITRONIX_ClearIT,         SITRONIX_ITStatus};
/**
 * @}
 */

/** @defgroup SITRONIX_Private_Function_Prototypes SITRONIX Private Function
 * Prototypes
 * @{
 */
#if (SITRONIX_AUTO_CALIBRATION_ENABLED == 1)
static int32_t SITRONIX_TS_Calibration(SITRONIX_Object_t *pObj);
static int32_t SITRONIX_Delay(SITRONIX_Object_t *pObj, uint32_t Delay);
#endif /* SITRONIX_AUTO_CALIBRATION_ENABLED == 1 */
static int32_t SITRONIX_DetectTouch(SITRONIX_Object_t *pObj);
static int32_t ReadRegWrap(void *handle, uint8_t Reg, uint8_t *Data,
                           uint16_t Length);
static int32_t WriteRegWrap(void *handle, uint8_t Reg, uint8_t *Data,
                            uint16_t Length);
static int32_t ReadDataWrap(void *handle, uint8_t *pData, uint16_t Length);

/**
 * @}
 */

/** @defgroup SITRONIX_Exported_Functions SITRONIX Exported Functions
 * @{
 */

/**
 * @brief  Register IO bus to component object
 * @param  Component object pointer
 * @retval error status
 */
int32_t SITRONIX_RegisterBusIO(SITRONIX_Object_t *pObj, SITRONIX_IO_t *pIO) {
  int32_t ret;

  if (pObj == NULL) {
    ret = SITRONIX_ERROR;
  } else {
    pObj->IO.Init = pIO->Init;
    pObj->IO.DeInit = pIO->DeInit;
    pObj->IO.Address = pIO->Address;
    pObj->IO.WriteReg = pIO->WriteReg;
    pObj->IO.ReadReg = pIO->ReadReg;
    pObj->IO.ReadData = pIO->ReadData;
    pObj->IO.GetTick = pIO->GetTick;

    pObj->Ctx.ReadReg = ReadRegWrap;
    pObj->Ctx.WriteReg = WriteRegWrap;
    pObj->Ctx.ReadData = ReadDataWrap;
    pObj->Ctx.handle = pObj;

    if (pObj->IO.Init != NULL) {
      ret = pObj->IO.Init();
    } else {
      ret = SITRONIX_ERROR;
    }
  }

  return ret;
}

/**
 * @brief  Get SITRONIX sensor capabilities
 * @param  pObj Component object pointer
 * @param  Capabilities pointer to SITRONIX sensor capabilities
 * @retval Component status
 */
int32_t SITRONIX_GetCapabilities(SITRONIX_Object_t *pObj,
                                 SITRONIX_Capabilities_t *Capabilities) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Store component's capabilities */
  Capabilities->MultiTouch = 1;
  Capabilities->Gesture =
      0; /* Gesture feature is currently not activated on FW chipset */
  Capabilities->MaxTouch = SITRONIX_MAX_DETECTABLE_TOUCH;
  Capabilities->MaxXl = SITRONIX_MAX_X_LENGTH;
  Capabilities->MaxYl = SITRONIX_MAX_Y_LENGTH;

  return SITRONIX_OK;
}

/**
 * @brief  Initialize the SITRONIX communication bus
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_Init(SITRONIX_Object_t *pObj) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28U];

  if (pObj->IsInitialized == 0U) {
    /* Initialize IO BUS layer */
    pObj->IO.Init();

    if (sitronix_read_data(&pObj->Ctx, data, (uint16_t)sizeof(data)) !=
        SITRONIX_OK) {
      ret = SITRONIX_ERROR;
    }

    pObj->IsInitialized = 1;
  }

  if (ret != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  }

  return ret;
}

/**
 * @brief  De-Initialize the SITRONIX communication bus
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_DeInit(SITRONIX_Object_t *pObj) {
  if (pObj->IsInitialized == 1U) {
    pObj->IsInitialized = 0;
  }

  return SITRONIX_OK;
}

/**
 * @brief  Configure the SITRONIX gesture
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj  Component object pointer
 * @param  GestureInit Gesture init structure
 * @retval Component status
 */
int32_t SITRONIX_GestureConfig(SITRONIX_Object_t *pObj,
                               SITRONIX_Gesture_Init_t *GestureInit) {
  return SITRONIX_ERROR;
}

/**
 * @brief  Read the SITRONIX device ID, pre initialize I2C in case of need to be
 *         able to read the SITRONIX device ID, and verify this is a SITRONIX.
 * @param  pObj Component object pointer
 * @param  Id Pointer to component's ID
 * @retval Component status
 */
int32_t SITRONIX_ReadID(SITRONIX_Object_t *pObj, uint32_t *Id) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28];
  uint8_t trial = 0;

  for (trial = 0; trial < 10; trial++) {
    if (sitronix_read_data(&pObj->Ctx, data, 28) != SITRONIX_OK) {
      ret = SITRONIX_ERROR;
    } else {
      if ((uint32_t)data[0] == SITRONIX_ID) {
        *Id = (uint32_t)data[0];
        return ret;
      }
    }
  }
  return ret;
}

uint8_t sitronix_touching = 0;

/**
 * @brief  Get the touch screen X and Y positions values
 * @param  pObj Component object pointer
 * @param  State Single Touch structure pointer
 * @retval Component status.
 */
int32_t SITRONIX_GetState(SITRONIX_Object_t *pObj, SITRONIX_State_t *State) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[64];

  State->TouchDetected = (uint32_t)SITRONIX_DetectTouch(pObj);
  if (sitronix_read_data(&pObj->Ctx, data, (uint16_t)sizeof(data)) !=
      SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    if ((uint32_t)data[2] & 0x80) {
      sitronix_touching = 1;
    } else {
      sitronix_touching = 0;
    }

    State->TouchX = (((uint32_t)data[2] & SITRONIX_TOUCH_POS_LSB_MASK) << 4);

    /* Send back first ready X position to caller */
    State->TouchX = ((((uint32_t)data[2] & SITRONIX_TOUCH_POS_LSB_MASK) << 4) |
                     ((uint32_t)data[3]));
    /* Send back first ready Y position to caller */
    State->TouchY = (((uint32_t)data[2] & SITRONIX_TOUCH_POS_MSB_MASK) << 8) |
                    ((uint32_t)data[4]);
  }

  return ret;
}

/**
 * @brief  Get the touch screen Xn and Yn positions values in multi-touch mode
 * @param  pObj Component object pointer
 * @param  State Multi Touch structure pointer
 * @retval Component status.
 */
int32_t SITRONIX_GetMultiTouchState(SITRONIX_Object_t *pObj,
                                    SITRONIX_MultiTouch_State_t *State) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28];

  State->TouchDetected = (uint32_t)SITRONIX_DetectTouch(pObj);

  if (sitronix_read_reg(&pObj->Ctx, SITRONIX_P1_XH_REG, data,
                        (uint16_t)sizeof(data)) != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    /* To be implemented */
  }

  return ret;
}

/**
 * @brief  Get Gesture ID
 * @param  pObj Component object pointer
 * @param  GestureId gesture ID
 * @retval Component status
 */
int32_t SITRONIX_GetGesture(SITRONIX_Object_t *pObj, uint8_t *GestureId) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Configure the SITRONIX device to generate IT on given INT pin
 *         connected to MCU as EXTI.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_EnableIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Configure the SITRONIX device to stop generating IT on the given INT
 * pin connected to MCU as EXTI.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_DisableIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Get IT status from SITRONIX interrupt status registers
 *         Should be called Following an EXTI coming to the MCU to know the
 * detailed reason of the interrupt.
 *         @note : This feature is not supported by SITRONIX.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_ITStatus(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Clear IT status in SITRONIX interrupt status clear registers
 *         Should be called Following an EXTI coming to the MCU.
 *         @note : This feature is not supported by SITRONIX.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_ClearIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @}
 */

/** @defgroup SITRONIX_Private_Functions SITRONIX Private Functions
 * @{
 */

/**
 * @brief  Return if there is touches detected or not.
 *         Try to detect new touches and forget the old ones (reset internal
 * global variables).
 * @param  pObj Component object pointer
 * @retval Number of active touches detected (can be between 0 and10) or
 * SITRONIX_ERROR in case of error
 */
__attribute__((optimize("-O0"))) int32_t SITRONIX_DetectTouch(
    SITRONIX_Object_t *pObj) {
  int32_t ret;
  uint8_t nb_touch = 0;
  static uint8_t first_event = 0;
  uint8_t data[28];

  if (sitronix_read_data(&pObj->Ctx, (uint8_t *)&data, 28) != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    if (first_event == 0) {
      if ((data[0] == 0x09)) {
        nb_touch = 1;
        first_event = 1;
      } else {
        nb_touch = 0;
      }
    } else {
      if (data[8] == 0x60) {
        nb_touch = 0;
      } else {
        nb_touch = 1;
      }
    }
    ret = (int32_t)nb_touch;
  }

  return ret;
}

/**
 * @brief  Wrap IO bus read function to component register red function
 * @param  handle Component object handle
 * @param  Reg The target register address to read
 * @param  pData The target register value to be read
 * @param  Length buffer size to be read
 * @retval Component status.
 */
static int32_t ReadRegWrap(void *handle, uint8_t Reg, uint8_t *pData,
                           uint16_t Length) {
  SITRONIX_Object_t *pObj = (SITRONIX_Object_t *)handle;

  return pObj->IO.ReadReg(pObj->IO.Address, Reg, pData, Length);
}

/**
 * @brief  Wrap IO bus write function to component register write function
 * @param  handle Component object handle
 * @param  Reg The target register address to write
 * @param  pData The target register value to be written
 * @param  Length buffer size to be written
 * @retval Component status.
 */
static int32_t WriteRegWrap(void *handle, uint8_t Reg, uint8_t *pData,
                            uint16_t Length) {
  SITRONIX_Object_t *pObj = (SITRONIX_Object_t *)handle;

  return pObj->IO.WriteReg(pObj->IO.Address, Reg, pData, Length);
}

/**
 * @brief  Wrap IO bus read function to component register red function
 * @param  handle Component object handle
 * @param  pData The target register value to be read
 * @param  Length buffer size to be read
 * @retval Component status.
 */
static int32_t ReadDataWrap(void *handle, uint8_t *pData, uint16_t Length) {
  SITRONIX_Object_t *pObj = (SITRONIX_Object_t *)handle;

  return pObj->IO.ReadData(pObj->IO.Address, pData, Length);
}

/**
  ******************************************************************************
  * @file    stm32u5x9j_discovery_ts.c
  * @author  MCD Application Team
  * @brief   This file provides a set of functions needed to manage the Touch
  *          Screen on STM32U5x9J-DISCOVERY board.
  @verbatim
  1. How To use this driver:
  --------------------------
   - This driver is used to drive the touch screen module of the
  STM32U5x9J-DISCOVERY board on the LCD mounted on MB1829A daughter board. The
  touch screen driver IC is a SITRONIX.

  2. Driver description:
  ---------------------
    + Initialization steps:
       o Initialize the TS using the BSP_TS_Init() function. You can select
         display orientation with "Orientation" parameter of TS_Init_t structure
         (portrait, landscape, portrait with 180 degrees rotation or landscape
         with 180 degrees rotation). The LCD size properties (width and height)
         are also parameters of TS_Init_t and depend on the orientation
  selected.

    + Touch screen use
       o Call BSP_TS_EnableIT() (BSP_TS_DisableIT()) to enable (disable) touch
         screen interrupt. BSP_TS_Callback() is called when TS interrupt occurs.
       o Call BSP_TS_GetState() to get the current touch status (detection and
         coordinates).
       o Call BSP_TS_Set_Orientation() to change the current orientation.
         Call BSP_TS_Get_Orientation() to get the current orientation.
       o Call BSP_TS_GetCapabilities() to get the SITRONIX capabilities.
       o SITRONIX doesn't support multi touch and gesture features.
         BSP_TS_Get_MultiTouchState(), BSP_TS_GestureConfig() and
         BSP_TS_GetGestureId() functions will return
  BSP_ERROR_FEATURE_NOT_SUPPORTED.

    + De-initialization steps:
       o De-initialize the touch screen using the BSP_TS_DeInit() function.

  @endverbatim
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2023 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* TS instances */
#define TS_INSTANCES_NBR 1U
#define TS_TOUCH_NBR 10U

/* TS orientations */
#define TS_ORIENTATION_PORTRAIT 0U
#define TS_ORIENTATION_LANDSCAPE 1U
#define TS_ORIENTATION_PORTRAIT_ROT180 2U
#define TS_ORIENTATION_LANDSCAPE_ROT180 3U

/* TS I2C address */
#define TS_I2C_ADDRESS 0xE0U

/** @defgroup STM32U5x9J_DISCOVERY_TS_Exported_Types TS Exported Types
 * @{
 */
typedef struct {
  uint32_t Width;       /* Screen width */
  uint32_t Height;      /* Screen height */
  uint32_t Orientation; /* Touch screen orientation */
  uint32_t Accuracy;    /* Expressed in pixel and means the x or y difference vs
                         old    position to consider the new values valid */
} TS_Init_t;

typedef struct {
  uint8_t MultiTouch;
  uint8_t Gesture;
  uint8_t MaxTouch;
  uint32_t MaxXl;
  uint32_t MaxYl;
} TS_Capabilities_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX;
  uint32_t TouchY;
} TS_State_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX[2];
  uint32_t TouchY[2];
  uint32_t TouchWeight[2];
  uint32_t TouchEvent[2];
  uint32_t TouchArea[2];
} TS_MultiTouch_State_t;

typedef struct {
  uint32_t Radian;
  uint32_t OffsetLeftRight;
  uint32_t OffsetUpDown;
  uint32_t DistanceLeftRight;
  uint32_t DistanceUpDown;
  uint32_t DistanceZoom;
} TS_Gesture_Config_t;

typedef struct {
  uint32_t Width;
  uint32_t Height;
  uint32_t Orientation;
  uint32_t Accuracy;
  uint32_t MaxX;
  uint32_t MaxY;
  uint32_t PreviousX[TS_TOUCH_NBR];
  uint32_t PreviousY[TS_TOUCH_NBR];
} TS_Ctx_t;

typedef struct {
  int32_t (*Init)(void *);
  int32_t (*DeInit)(void *);
  int32_t (*GestureConfig)(void *, void *);
  int32_t (*ReadID)(void *, uint32_t *);
  int32_t (*GetState)(void *, void *);
  int32_t (*GetMultiTouchState)(void *, void *);
  int32_t (*GetGesture)(void *, void *);
  int32_t (*GetCapabilities)(void *, void *);
  int32_t (*EnableIT)(void *);
  int32_t (*DisableIT)(void *);
  int32_t (*ClearIT)(void *);
  int32_t (*ITStatus)(void *);
} TS_Drv_t;

/* DSI TS INT pin */
#define TS_INT_PIN GPIO_PIN_8
#define TS_INT_GPIO_PORT GPIOE
#define TS_INT_GPIO_CLK_ENABLE() __HAL_RCC_GPIOE_CLK_ENABLE()
#define TS_INT_GPIO_CLK_DISABLE() __HAL_RCC_GPIOE_CLK_DISABLE()
#define TS_INT_EXTI_IRQn EXTI8_IRQn

/* Includes ------------------------------------------------------------------*/
//#include "stm32u5x9j_discovery_ts.h"
//#include "stm32u5x9j_discovery.h"

/** @addtogroup BSP
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS TS
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_Defines TS Private Defines
 * @{
 */
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_TypesDefinitions TS Private
 * TypesDefinitions
 * @{
 */
typedef void (*BSP_EXTI_LineCallback)(void);
/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_TS_Exported_Variables TS Exported Variables
 * @{
 */
void *Ts_CompObj[TS_INSTANCES_NBR] = {0};
TS_Drv_t *Ts_Drv[TS_INSTANCES_NBR] = {0};
TS_Ctx_t Ts_Ctx[TS_INSTANCES_NBR] = {0};
EXTI_HandleTypeDef hts_exti[TS_INSTANCES_NBR];
IRQn_Type Ts_IRQn[TS_INSTANCES_NBR] = {EXTI15_IRQn};

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_FunctionPrototypes TS Private
 * Function Prototypes
 * @{
 */
static int32_t SITRONIX_Probe(uint32_t Instance);

/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_TS_Exported_Functions
 * @{
 */
/**
 * @brief  Initialize the TS.
 * @param  Instance TS Instance.
 * @param  TS_Init  Pointer to TS initialization structure.
 * @retval BSP status.
 */
int32_t BSP_TS_Init(uint32_t Instance, TS_Init_t *TS_Init) {
  int32_t status = BSP_ERROR_NONE;

  if ((TS_Init == NULL) || (Instance >= TS_INSTANCES_NBR)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Probe the TS driver */
    if (SITRONIX_Probe(Instance) != BSP_ERROR_NONE) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } else {
      TS_Capabilities_t Capabilities;
      uint32_t i;
      /* Store parameters on TS context */
      Ts_Ctx[Instance].Width = TS_Init->Width;
      Ts_Ctx[Instance].Height = TS_Init->Height;
      Ts_Ctx[Instance].Orientation = TS_Init->Orientation;
      Ts_Ctx[Instance].Accuracy = TS_Init->Accuracy;
      /* Get capabilities to retrieve maximum values of X and Y */
      if (Ts_Drv[Instance]->GetCapabilities(Ts_CompObj[Instance],
                                            &Capabilities) < 0) {
        status = BSP_ERROR_COMPONENT_FAILURE;
      } else {
        /* Store maximum X and Y on context */
        Ts_Ctx[Instance].MaxX = Capabilities.MaxXl;
        Ts_Ctx[Instance].MaxY = Capabilities.MaxYl;
        /* Initialize previous position in order to always detect first touch */
        for (i = 0; i < TS_TOUCH_NBR; i++) {
          Ts_Ctx[Instance].PreviousX[i] =
              TS_Init->Width + TS_Init->Accuracy + 1U;
          Ts_Ctx[Instance].PreviousY[i] =
              TS_Init->Height + TS_Init->Accuracy + 1U;
        }
      }
    }
  }

  return status;
}

/**
 * @brief  De-Initialize the TS.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_DeInit(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* De-Init the TS driver */
    if (Ts_Drv[Instance]->DeInit(Ts_CompObj[Instance]) < 0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    }
  }

  return status;
}

/**
 * @brief  Enable the TS interrupt.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_EnableIT(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  GPIO_InitTypeDef gpio_init_structure;

  __HAL_RCC_GPIOE_CLK_ENABLE();

  /* Configure Interrupt mode for TS detection pin */
  gpio_init_structure.Pin = TS_INT_PIN;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Mode = GPIO_MODE_IT_FALLING;
  HAL_GPIO_Init(TS_INT_GPIO_PORT, &gpio_init_structure);

  /* Enable and set Touch screen EXTI Interrupt to the lowest priority */
  HAL_NVIC_SetPriority((IRQn_Type)(TS_INT_EXTI_IRQn), 0x0F, 0x00);
  HAL_NVIC_EnableIRQ((IRQn_Type)(TS_INT_EXTI_IRQn));

  return BSP_ERROR_NONE;
}

/**
 * @brief  Disable the TS interrupt.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_DisableIT(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* To be Implemented */
  return BSP_ERROR_NONE;
}

/**
 * @brief  Set the TS orientation.
 * @param  Instance TS Instance.
 * @param  Orientation TS orientation.
 * @retval BSP status.
 */
int32_t BSP_TS_Set_Orientation(uint32_t Instance, uint32_t Orientation) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t temp;
  uint32_t i;

  if ((Instance >= TS_INSTANCES_NBR) ||
      (Orientation > TS_ORIENTATION_LANDSCAPE_ROT180)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Update TS context if orientation is changed from/to portrait to/from
     * landscape */
    if ((((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)) &&
         ((Orientation == TS_ORIENTATION_PORTRAIT) ||
          (Orientation == TS_ORIENTATION_PORTRAIT_ROT180))) ||
        (((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_PORTRAIT) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_PORTRAIT_ROT180)) &&
         ((Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)))) {
      /* Invert width and height */
      temp = Ts_Ctx[Instance].Width;
      Ts_Ctx[Instance].Width = Ts_Ctx[Instance].Height;
      Ts_Ctx[Instance].Height = temp;
      /* Invert MaxX and MaxY */
      temp = Ts_Ctx[Instance].MaxX;
      Ts_Ctx[Instance].MaxX = Ts_Ctx[Instance].MaxY;
      Ts_Ctx[Instance].MaxY = temp;
    }
    /* Store orientation on TS context */
    Ts_Ctx[Instance].Orientation = Orientation;
    /* Reset previous position */
    for (i = 0; i < TS_TOUCH_NBR; i++) {
      Ts_Ctx[Instance].PreviousX[i] =
          Ts_Ctx[Instance].Width + Ts_Ctx[Instance].Accuracy + 1U;
      Ts_Ctx[Instance].PreviousY[i] =
          Ts_Ctx[Instance].Height + Ts_Ctx[Instance].Accuracy + 1U;
    }
  }

  return status;
}

/**
 * @brief  Get the TS orientation.
 * @param  Instance TS Instance.
 * @param  Orientation Pointer to TS orientation.
 * @retval BSP status.
 */
int32_t BSP_TS_Get_Orientation(uint32_t Instance, uint32_t *Orientation) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= TS_INSTANCES_NBR) || (Orientation == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get orientation from TS context */
    *Orientation = Ts_Ctx[Instance].Orientation;
  }

  return status;
}

/**
 * @brief  Get position of a single touch.
 * @param  Instance TS Instance.
 * @param  TS_State Pointer to single touch structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GetState(uint32_t Instance, TS_State_t *TS_State) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t x_oriented;
  uint32_t y_oriented;
  uint32_t x_diff;
  uint32_t y_diff;

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    SITRONIX_State_t state;

    /* Get each touch coordinates */
    if (Ts_Drv[Instance]->GetState(Ts_CompObj[Instance], &state) < 0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } /* Check and update the number of touches active detected */
    else if (state.TouchDetected != 0U) {
      x_oriented = /*Ts_Ctx[Instance].MaxX -*/ state.TouchX;
      y_oriented = /*Ts_Ctx[Instance].MaxY -*/ state.TouchY;

      /* Apply boundary */
      TS_State->TouchX =
          (x_oriented * Ts_Ctx[Instance].Width) / (Ts_Ctx[Instance].MaxX);
      TS_State->TouchY =
          (y_oriented * Ts_Ctx[Instance].Height) / (Ts_Ctx[Instance].MaxY);
      /* Store Current TS state */
      TS_State->TouchDetected = state.TouchDetected;

      /* Check accuracy */
      x_diff = (TS_State->TouchX > Ts_Ctx[Instance].PreviousX[0])
                   ? (TS_State->TouchX - Ts_Ctx[Instance].PreviousX[0])
                   : (Ts_Ctx[Instance].PreviousX[0] - TS_State->TouchX);

      y_diff = (TS_State->TouchY > Ts_Ctx[Instance].PreviousY[0])
                   ? (TS_State->TouchY - Ts_Ctx[Instance].PreviousY[0])
                   : (Ts_Ctx[Instance].PreviousY[0] - TS_State->TouchY);

      if ((x_diff > Ts_Ctx[Instance].Accuracy) ||
          (y_diff > Ts_Ctx[Instance].Accuracy)) {
        /* New touch detected */
        Ts_Ctx[Instance].PreviousX[0] = TS_State->TouchX;
        Ts_Ctx[Instance].PreviousY[0] = TS_State->TouchY;
      } else {
        TS_State->TouchX = Ts_Ctx[Instance].PreviousX[0];
        TS_State->TouchY = Ts_Ctx[Instance].PreviousY[0];
      }
    } else {
      TS_State->TouchDetected = 0U;
      TS_State->TouchX = Ts_Ctx[Instance].PreviousX[0];
      TS_State->TouchY = Ts_Ctx[Instance].PreviousY[0];
    }
  }

  return status;
}

/**
 * @brief  Get positions of multiple touch.
 * @param  Instance TS Instance.
 * @param  TS_State Pointer to multiple touch structure.
 * @retval BSP status.
 */
int32_t BSP_TS_Get_MultiTouchState(const uint32_t Instance,
                                   TS_MultiTouch_State_t *TS_State) {
  int32_t status;

  UNUSED(TS_State);

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported in this release */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Configure gesture on TS.
 * @param  Instance TS Instance.
 * @param  GestureConfig Pointer to gesture configuration structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GestureConfig(const uint32_t Instance,
                             TS_Gesture_Config_t *GestureConfig) {
  int32_t status;

  if ((Instance >= TS_INSTANCES_NBR) || (GestureConfig == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get gesture.
 * @param  Instance TS Instance.
 * @param  GestureId Pointer to gesture.
 * @retval BSP status.
 */
int32_t BSP_TS_GetGestureId(const uint32_t Instance, uint32_t *GestureId) {
  int32_t status;

  if ((Instance >= TS_INSTANCES_NBR) || (GestureId == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get the TS capabilities.
 * @param  Instance TS Instance.
 * @param  Capabilities Pointer to TS capabilities structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GetCapabilities(uint32_t Instance,
                               TS_Capabilities_t *Capabilities) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= TS_INSTANCES_NBR) || (Capabilities == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get the TS driver capabilities */
    if (Ts_Drv[Instance]->GetCapabilities(Ts_CompObj[Instance], Capabilities) <
        0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } else {
      /* Update maximum X and Y according orientation */
      if ((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)) {
        uint32_t tmp;
        tmp = Capabilities->MaxXl;
        Capabilities->MaxXl = Capabilities->MaxYl;
        Capabilities->MaxYl = tmp;
      }
    }
  }

  return status;
}

/**
 * @brief  TS Callback.
 * @param  Instance TS Instance.
 * @retval None.
 */
__weak void BSP_TS_Callback(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* This function should be implemented by the user application.
     It is called into this driver when an event on TS touch detection */
}

/**
 * @brief  BSP TS interrupt handler.
 * @param  Instance TS Instance.
 * @retval None.
 */
void BSP_TS_IRQHandler(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* To be implemented */
}
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_Functions TS Private Functions
 * @{
 */
/**
 * @brief  Probe the SITRONIX TS driver.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
static int32_t SITRONIX_Probe(uint32_t Instance) {
  int32_t status;
  SITRONIX_IO_t IOCtx;
  static SITRONIX_Object_t SITRONIXObj;

  /* Configure the TS driver */
  IOCtx.Address = TS_I2C_ADDRESS;
  IOCtx.Init = BSP_I2C5_Init;
  IOCtx.DeInit = BSP_I2C5_DeInit;
  IOCtx.ReadReg = BSP_I2C5_ReadReg;
  IOCtx.WriteReg = BSP_I2C5_WriteReg;
  IOCtx.ReadData = BSP_I2C5_Recv;
  IOCtx.GetTick = BSP_GetTick;

  if (SITRONIX_RegisterBusIO(&SITRONIXObj, &IOCtx) != SITRONIX_OK) {
    status = BSP_ERROR_BUS_FAILURE;
  } else {
    Ts_CompObj[Instance] = &SITRONIXObj;
    Ts_Drv[Instance] = (TS_Drv_t *)&SITRONIX_TS_Driver;
    if (Ts_Drv[Instance]->Init(Ts_CompObj[Instance]) < 0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } else {
      status = BSP_ERROR_NONE;
    }
  }

  return status;
}

/**
 * @}
 */

/**
 * @}
 */

/**
 * @}
 */

/**
 * @}
 */

#include <string.h>
#include "touch.h"

void touch_init(void) {
  TS_Init_t TsInit;

  /* Initialize the TouchScreen */
  TsInit.Width = 480;
  TsInit.Height = 480;
  TsInit.Orientation = 0;
  TsInit.Accuracy = 10;

  BSP_TS_Init(0, &TsInit);
}
void touch_power_on(void) {}
void touch_power_off(void) {}
void touch_sensitivity(uint8_t value) {}

uint32_t touch_is_detected(void) { return sitronix_touching != 0; }

uint32_t touch_read(void) {
  TS_State_t state = {0};
  static uint32_t xy = 0;
  static TS_State_t state_last = {0};
  // static uint16_t first = 1;
  static uint16_t touching = 0;

  BSP_TS_GetState(0, &state);

  state.TouchDetected = touch_is_detected();
  state.TouchY = state.TouchY > 120 ? state.TouchY - 120 : 0;
  state.TouchX = state.TouchX > 120 ? state.TouchX - 120 : 0;

  if (!touch_is_detected()) {
    // if (state.TouchDetected == 0) {
    if (touching) {
      // touch end
      memcpy(&state_last, &state, sizeof(state));
      touching = 0;
      return TOUCH_END | xy;
    }
    return 0;
  }

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

  xy = touch_pack_xy(state.TouchX, state.TouchY);

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
