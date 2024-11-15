

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "ili9341_spi.h"

/**
 * @brief ILI9341 chip IDs
 */
#define ILI9341_ID 0x9341

/**
 * @brief  ILI9341 Size
 */
#define ILI9341_LCD_PIXEL_WIDTH ((uint16_t)240)
#define ILI9341_LCD_PIXEL_HEIGHT ((uint16_t)320)

/**
 * @brief  ILI9341 Timing
 */
/* Timing configuration  (Typical configuration from ILI9341 datasheet)
  HSYNC=10 (9+1)
  HBP=20 (29-10+1)
  ActiveW=240 (269-20-10+1)
  HFP=10 (279-240-20-10+1)

  VSYNC=2 (1+1)
  VBP=2 (3-2+1)
  ActiveH=320 (323-2-2+1)
  VFP=4 (327-320-2-2+1)
*/

/**
 * @brief  ILI9341 Registers
 */

/* Level 1 Commands */
#define LCD_SWRESET 0x01         /* Software Reset */
#define LCD_READ_DISPLAY_ID 0x04 /* Read display identification information */
#define LCD_RDDST 0x09           /* Read Display Status */
#define LCD_RDDPM 0x0A           /* Read Display Power Mode */
#define LCD_RDDMADCTL 0x0B       /* Read Display MADCTL */
#define LCD_RDDCOLMOD 0x0C       /* Read Display Pixel Format */
#define LCD_RDDIM 0x0D           /* Read Display Image Format */
#define LCD_RDDSM 0x0E           /* Read Display Signal Mode */
#define LCD_RDDSDR 0x0F          /* Read Display Self-Diagnostic Result */
#define LCD_SPLIN 0x10           /* Enter Sleep Mode */
#define LCD_SLEEP_OUT 0x11       /* Sleep out register */
#define LCD_PTLON 0x12           /* Partial Mode ON */
#define LCD_NORMAL_MODE_ON 0x13  /* Normal Display Mode ON */
#define LCD_DINVOFF 0x20         /* Display Inversion OFF */
#define LCD_DINVON 0x21          /* Display Inversion ON */
#define LCD_GAMMA 0x26           /* Gamma register */
#define LCD_DISPLAY_OFF 0x28     /* Display off register */
#define LCD_DISPLAY_ON 0x29      /* Display on register */
#define LCD_COLUMN_ADDR 0x2A     /* Colomn address register */
#define LCD_PAGE_ADDR 0x2B       /* Page address register */
#define LCD_GRAM 0x2C            /* GRAM register */
#define LCD_RGBSET 0x2D          /* Color SET */
#define LCD_RAMRD 0x2E           /* Memory Read */
#define LCD_PLTAR 0x30           /* Partial Area */
#define LCD_VSCRDEF 0x33         /* Vertical Scrolling Definition */
#define LCD_TEOFF 0x34           /* Tearing Effect Line OFF */
#define LCD_TEON 0x35            /* Tearing Effect Line ON */
#define LCD_MAC 0x36             /* Memory Access Control register*/
#define LCD_VSCRSADD 0x37        /* Vertical Scrolling Start Address */
#define LCD_IDMOFF 0x38          /* Idle Mode OFF */
#define LCD_IDMON 0x39           /* Idle Mode ON */
#define LCD_PIXEL_FORMAT 0x3A    /* Pixel Format register */
#define LCD_WRITE_MEM_CONTINUE 0x3C /* Write Memory Continue */
#define LCD_READ_MEM_CONTINUE 0x3E  /* Read Memory Continue */
#define LCD_SET_TEAR_SCANLINE 0x44  /* Set Tear Scanline */
#define LCD_GET_SCANLINE 0x45       /* Get Scanline */
#define LCD_WDB 0x51                /* Write Brightness Display register */
#define LCD_RDDISBV 0x52            /* Read Display Brightness */
#define LCD_WCD 0x53                /* Write Control Display register*/
#define LCD_RDCTRLD 0x54            /* Read CTRL Display */
#define LCD_WRCABC 0x55     /* Write Content Adaptive Brightness Control */
#define LCD_RDCABC 0x56     /* Read Content Adaptive Brightness Control */
#define LCD_WRITE_CABC 0x5E /* Write CABC Minimum Brightness */
#define LCD_READ_CABC 0x5F  /* Read CABC Minimum Brightness */
#define LCD_READ_ID1 0xDA   /* Read ID1 */
#define LCD_READ_ID2 0xDB   /* Read ID2 */
#define LCD_READ_ID3 0xDC   /* Read ID3 */

/* Level 2 Commands */
#define LCD_RGB_INTERFACE 0xB0 /* RGB Interface Signal Control */
#define LCD_FRMCTR1 0xB1       /* Frame Rate Control (In Normal Mode) */
#define LCD_FRMCTR2 0xB2       /* Frame Rate Control (In Idle Mode) */
#define LCD_FRMCTR3 0xB3       /* Frame Rate Control (In Partial Mode) */
#define LCD_INVTR 0xB4         /* Display Inversion Control */
#define LCD_BPC 0xB5           /* Blanking Porch Control register */
#define LCD_DFC 0xB6           /* Display Function Control register */
#define LCD_ETMOD 0xB7         /* Entry Mode Set */
#define LCD_BACKLIGHT1 0xB8    /* Backlight Control 1 */
#define LCD_BACKLIGHT2 0xB9    /* Backlight Control 2 */
#define LCD_BACKLIGHT3 0xBA    /* Backlight Control 3 */
#define LCD_BACKLIGHT4 0xBB    /* Backlight Control 4 */
#define LCD_BACKLIGHT5 0xBC    /* Backlight Control 5 */
#define LCD_BACKLIGHT7 0xBE    /* Backlight Control 7 */
#define LCD_BACKLIGHT8 0xBF    /* Backlight Control 8 */
#define LCD_POWER1 0xC0        /* Power Control 1 register */
#define LCD_POWER2 0xC1        /* Power Control 2 register */
#define LCD_VCOM1 0xC5         /* VCOM Control 1 register */
#define LCD_VCOM2 0xC7         /* VCOM Control 2 register */
#define LCD_NVMWR 0xD0         /* NV Memory Write */
#define LCD_NVMPKEY 0xD1       /* NV Memory Protection Key */
#define LCD_RDNVM 0xD2         /* NV Memory Status Read */
#define LCD_READ_ID4 0xD3      /* Read ID4 */
#define LCD_PGAMMA 0xE0        /* Positive Gamma Correction register */
#define LCD_NGAMMA 0xE1        /* Negative Gamma Correction register */
#define LCD_DGAMCTRL1 0xE2     /* Digital Gamma Control 1 */
#define LCD_DGAMCTRL2 0xE3     /* Digital Gamma Control 2 */
#define LCD_INTERFACE 0xF6     /* Interface control register */

/* Extend register commands */
#define LCD_POWERA 0xCB    /* Power control A register */
#define LCD_POWERB 0xCF    /* Power control B register */
#define LCD_DTCA 0xE8      /* Driver timing control A */
#define LCD_DTCB 0xEA      /* Driver timing control B */
#define LCD_POWER_SEQ 0xED /* Power on sequence register */
#define LCD_3GAMMA_EN 0xF2 /* 3 Gamma enable register */
#define LCD_PRC 0xF7       /* Pump ratio control register */

/* Size of read registers */
#define LCD_READ_ID4_SIZE 3 /* Size of Read ID4 */

/*############################### SPIx #######################################*/
#define DISCOVERY_SPIx SPI5
#define DISCOVERY_SPIx_CLK_ENABLE() __HAL_RCC_SPI5_CLK_ENABLE()
#define DISCOVERY_SPIx_GPIO_PORT GPIOF /* GPIOF */
#define DISCOVERY_SPIx_AF GPIO_AF5_SPI5
#define DISCOVERY_SPIx_GPIO_CLK_ENABLE() __HAL_RCC_GPIOF_CLK_ENABLE()
#define DISCOVERY_SPIx_GPIO_CLK_DISABLE() __HAL_RCC_GPIOF_CLK_DISABLE()
#define DISCOVERY_SPIx_SCK_PIN GPIO_PIN_7  /* PF.07 */
#define DISCOVERY_SPIx_MISO_PIN GPIO_PIN_8 /* PF.08 */
#define DISCOVERY_SPIx_MOSI_PIN GPIO_PIN_9 /* PF.09 */
/* Maximum Timeout values for flags waiting loops. These timeouts are not based
   on accurate values, they just guarantee that the application will not remain
   stuck if the SPI communication is corrupted.
   You may modify these timeout values depending on CPU frequency and
   application conditions (interrupts routines ...). */
#define SPIx_TIMEOUT_MAX ((uint32_t)0x1000)

/*################################ LCD #######################################*/
/* Chip Select macro definition */
#define LCD_CS_LOW() \
  HAL_GPIO_WritePin(LCD_NCS_GPIO_PORT, LCD_NCS_PIN, GPIO_PIN_RESET)
#define LCD_CS_HIGH() \
  HAL_GPIO_WritePin(LCD_NCS_GPIO_PORT, LCD_NCS_PIN, GPIO_PIN_SET)

/* Set WRX High to send data */
#define LCD_WRX_LOW() \
  HAL_GPIO_WritePin(LCD_WRX_GPIO_PORT, LCD_WRX_PIN, GPIO_PIN_RESET)
#define LCD_WRX_HIGH() \
  HAL_GPIO_WritePin(LCD_WRX_GPIO_PORT, LCD_WRX_PIN, GPIO_PIN_SET)

/* Set WRX High to send data */
#define LCD_RDX_LOW() \
  HAL_GPIO_WritePin(LCD_RDX_GPIO_PORT, LCD_RDX_PIN, GPIO_PIN_RESET)
#define LCD_RDX_HIGH() \
  HAL_GPIO_WritePin(LCD_RDX_GPIO_PORT, LCD_RDX_PIN, GPIO_PIN_SET)

/**
 * @brief  LCD Control pin
 */
#define LCD_NCS_PIN GPIO_PIN_2
#define LCD_NCS_GPIO_PORT GPIOC
#define LCD_NCS_GPIO_CLK_ENABLE() __HAL_RCC_GPIOC_CLK_ENABLE()
#define LCD_NCS_GPIO_CLK_DISABLE() __HAL_RCC_GPIOC_CLK_DISABLE()
/**
 * @}
 */
/**
 * @brief  LCD Command/data pin
 */
#define LCD_WRX_PIN GPIO_PIN_13
#define LCD_WRX_GPIO_PORT GPIOD
#define LCD_WRX_GPIO_CLK_ENABLE() __HAL_RCC_GPIOD_CLK_ENABLE()
#define LCD_WRX_GPIO_CLK_DISABLE() __HAL_RCC_GPIOD_CLK_DISABLE()

#define LCD_RDX_PIN GPIO_PIN_12
#define LCD_RDX_GPIO_PORT GPIOD
#define LCD_RDX_GPIO_CLK_ENABLE() __HAL_RCC_GPIOD_CLK_ENABLE()
#define LCD_RDX_GPIO_CLK_DISABLE() __HAL_RCC_GPIOD_CLK_DISABLE()

static SPI_HandleTypeDef SpiHandle;
uint32_t SpixTimeout =
    SPIx_TIMEOUT_MAX; /*<! Value of Timeout when SPI communication fails */

/* SPIx bus function */
static void SPIx_Init(void);
static void ili9341_Write(uint16_t Value);
static uint32_t ili9341_Read(uint8_t ReadSize);
static void ili9341_Error(void);

/**
 * @brief  SPIx Bus initialization
 */
static void SPIx_Init(void) {
  if (HAL_SPI_GetState(&SpiHandle) == HAL_SPI_STATE_RESET) {
    /* SPI configuration -----------------------------------------------------*/
    SpiHandle.Instance = DISCOVERY_SPIx;
    /* SPI baudrate is set to 5.6 MHz (PCLK2/SPI_BaudRatePrescaler = 90/16
       = 5.625 MHz) to verify these constraints:
       - ILI9341 LCD SPI interface max baudrate is 10MHz for write and 6.66MHz
       for read
       - l3gd20 SPI interface max baudrate is 10MHz for write/read
       - PCLK2 frequency is set to 90 MHz
    */
    SpiHandle.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;

    /* On STM32F429I-Discovery, LCD ID cannot be read then keep a common
     * configuration */
    /* for LCD and GYRO (SPI_DIRECTION_2LINES) */
    /* Note: To read a register a LCD, SPI_DIRECTION_1LINE should be set */
    SpiHandle.Init.Direction = SPI_DIRECTION_2LINES;
    SpiHandle.Init.CLKPhase = SPI_PHASE_1EDGE;
    SpiHandle.Init.CLKPolarity = SPI_POLARITY_LOW;
    SpiHandle.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLED;
    SpiHandle.Init.CRCPolynomial = 7;
    SpiHandle.Init.DataSize = SPI_DATASIZE_8BIT;
    SpiHandle.Init.FirstBit = SPI_FIRSTBIT_MSB;
    SpiHandle.Init.NSS = SPI_NSS_SOFT;
    SpiHandle.Init.TIMode = SPI_TIMODE_DISABLED;
    SpiHandle.Init.Mode = SPI_MODE_MASTER;

    HAL_SPI_Init(&SpiHandle);
  }
}

/**
 * @brief  SPIx error treatment function.
 */
static void ili9341_Error(void) {
  /* De-initialize the SPI communication BUS */
  HAL_SPI_DeInit(&SpiHandle);

  /* Re- Initialize the SPI communication BUS */
  SPIx_Init();
}

/**
 * @brief  Reads 4 bytes from device.
 * @param  ReadSize: Number of bytes to read (max 4 bytes)
 * @retval Value read on the SPI
 */
static uint32_t ili9341_Read(uint8_t ReadSize) {
  HAL_StatusTypeDef status = HAL_OK;
  uint32_t readvalue;

  status =
      HAL_SPI_Receive(&SpiHandle, (uint8_t*)&readvalue, ReadSize, SpixTimeout);

  /* Check the communication status */
  if (status != HAL_OK) {
    /* Re-Initialize the BUS */
    ili9341_Error();
  }

  return readvalue;
}

/**
 * @brief  Writes a byte to device.
 * @param  Value: value to be written
 */
static void ili9341_Write(uint16_t Value) {
  HAL_StatusTypeDef status = HAL_OK;

  status = HAL_SPI_Transmit(&SpiHandle, (uint8_t*)&Value, 1, SpixTimeout);

  /* Check the communication status */
  if (status != HAL_OK) {
    /* Re-Initialize the BUS */
    ili9341_Error();
  }
}

void ili9341_spi_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  /* Configure NCS in Output Push-Pull mode */
  LCD_WRX_GPIO_CLK_ENABLE();
  GPIO_InitStructure.Pin = LCD_WRX_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FAST;
  HAL_GPIO_Init(LCD_WRX_GPIO_PORT, &GPIO_InitStructure);

  LCD_RDX_GPIO_CLK_ENABLE();
  GPIO_InitStructure.Pin = LCD_RDX_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FAST;
  HAL_GPIO_Init(LCD_RDX_GPIO_PORT, &GPIO_InitStructure);

  /* Configure the LCD Control pins ----------------------------------------*/
  LCD_NCS_GPIO_CLK_ENABLE();

  /* Configure NCS in Output Push-Pull mode */
  GPIO_InitStructure.Pin = LCD_NCS_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FAST;
  HAL_GPIO_Init(LCD_NCS_GPIO_PORT, &GPIO_InitStructure);

  /* Set or Reset the control line */
  LCD_CS_LOW();
  LCD_CS_HIGH();

  /* Enable SPIx clock */
  DISCOVERY_SPIx_CLK_ENABLE();

  /* Enable DISCOVERY_SPI GPIO clock */
  DISCOVERY_SPIx_GPIO_CLK_ENABLE();

  /* configure SPI SCK, MOSI and MISO */
  GPIO_InitStructure.Pin = (DISCOVERY_SPIx_SCK_PIN | DISCOVERY_SPIx_MOSI_PIN |
                            DISCOVERY_SPIx_MISO_PIN);
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_MEDIUM;
  GPIO_InitStructure.Alternate = DISCOVERY_SPIx_AF;
  HAL_GPIO_Init(DISCOVERY_SPIx_GPIO_PORT, &GPIO_InitStructure);

  SPIx_Init();
}

/**
 * @brief  Writes register value.
 */
void ili9341_WriteData(uint16_t RegValue) {
  /* Set WRX to send data */
  LCD_WRX_HIGH();

  /* Reset LCD control line(/CS) and Send data */
  LCD_CS_LOW();
  ili9341_Write(RegValue);

  /* Deselect: Chip Select high */
  LCD_CS_HIGH();
}

/**
 * @brief  Writes register address.
 */
void ili9341_WriteReg(uint8_t Reg) {
  /* Reset WRX to send command */
  LCD_WRX_LOW();

  /* Reset LCD control line(/CS) and Send command */
  LCD_CS_LOW();
  ili9341_Write(Reg);

  /* Deselect: Chip Select high */
  LCD_CS_HIGH();
}

/**
 * @brief  Reads register value.
 * @param  RegValue Address of the register to read
 * @param  ReadSize Number of bytes to read
 * @retval Content of the register value
 */
uint32_t ili9341_ReadData(uint16_t RegValue, uint8_t ReadSize) {
  uint32_t readvalue = 0;

  /* Select: Chip Select low */
  LCD_CS_LOW();

  /* Reset WRX to send command */
  LCD_WRX_LOW();

  ili9341_Write(RegValue);

  readvalue = ili9341_Read(ReadSize);

  /* Set WRX to send data */
  LCD_WRX_HIGH();

  /* Deselect: Chip Select high */
  LCD_CS_HIGH();

  return readvalue;
}

void ili9341_init(void) {
  /* Initialize ILI9341 low level bus layer ----------------------------------*/
  ili9341_spi_init();

  ili9341_WriteReg(LCD_DISPLAY_OFF);

  /* Configure LCD */
  ili9341_WriteReg(0xCA);
  ili9341_WriteData(0xC3);
  ili9341_WriteData(0x08);
  ili9341_WriteData(0x50);
  ili9341_WriteReg(LCD_POWERB);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0xC1);
  ili9341_WriteData(0x30);
  ili9341_WriteReg(LCD_POWER_SEQ);
  ili9341_WriteData(0x64);
  ili9341_WriteData(0x03);
  ili9341_WriteData(0x12);
  ili9341_WriteData(0x81);
  ili9341_WriteReg(LCD_DTCA);
  ili9341_WriteData(0x85);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x78);
  ili9341_WriteReg(LCD_POWERA);
  ili9341_WriteData(0x39);
  ili9341_WriteData(0x2C);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x34);
  ili9341_WriteData(0x02);
  ili9341_WriteReg(LCD_PRC);
  ili9341_WriteData(0x20);
  ili9341_WriteReg(LCD_DTCB);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x00);
  ili9341_WriteReg(LCD_FRMCTR1);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x1B);
  ili9341_WriteReg(LCD_DFC);
  ili9341_WriteData(0x0A);
  ili9341_WriteData(0xA2);
  ili9341_WriteReg(LCD_POWER1);
  ili9341_WriteData(0x10);
  ili9341_WriteReg(LCD_POWER2);
  ili9341_WriteData(0x10);
  ili9341_WriteReg(LCD_VCOM1);
  ili9341_WriteData(0x45);
  ili9341_WriteData(0x15);
  ili9341_WriteReg(LCD_VCOM2);
  ili9341_WriteData(0x90);
  ili9341_WriteReg(LCD_MAC);
  ili9341_WriteData(0xC8);
  ili9341_WriteReg(LCD_3GAMMA_EN);
  ili9341_WriteData(0x00);
  ili9341_WriteReg(LCD_RGB_INTERFACE);
  ili9341_WriteData(0xC2);
  ili9341_WriteReg(LCD_DFC);
  ili9341_WriteData(0x0A);
  ili9341_WriteData(0xA7);
  ili9341_WriteData(0x27);
  ili9341_WriteData(0x04);

  /* Colomn address set */
  ili9341_WriteReg(LCD_COLUMN_ADDR);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0xEF);
  /* Page address set */
  ili9341_WriteReg(LCD_PAGE_ADDR);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x01);
  ili9341_WriteData(0x3F);
  ili9341_WriteReg(LCD_INTERFACE);
  ili9341_WriteData(0x01);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x06);

  ili9341_WriteReg(LCD_GRAM);
  HAL_Delay(200);

  ili9341_WriteReg(LCD_GAMMA);
  ili9341_WriteData(0x01);

  ili9341_WriteReg(LCD_PGAMMA);
  ili9341_WriteData(0x0F);
  ili9341_WriteData(0x29);
  ili9341_WriteData(0x24);
  ili9341_WriteData(0x0C);
  ili9341_WriteData(0x0E);
  ili9341_WriteData(0x09);
  ili9341_WriteData(0x4E);
  ili9341_WriteData(0x78);
  ili9341_WriteData(0x3C);
  ili9341_WriteData(0x09);
  ili9341_WriteData(0x13);
  ili9341_WriteData(0x05);
  ili9341_WriteData(0x17);
  ili9341_WriteData(0x11);
  ili9341_WriteData(0x00);
  ili9341_WriteReg(LCD_NGAMMA);
  ili9341_WriteData(0x00);
  ili9341_WriteData(0x16);
  ili9341_WriteData(0x1B);
  ili9341_WriteData(0x04);
  ili9341_WriteData(0x11);
  ili9341_WriteData(0x07);
  ili9341_WriteData(0x31);
  ili9341_WriteData(0x33);
  ili9341_WriteData(0x42);
  ili9341_WriteData(0x05);
  ili9341_WriteData(0x0C);
  ili9341_WriteData(0x0A);
  ili9341_WriteData(0x28);
  ili9341_WriteData(0x2F);
  ili9341_WriteData(0x0F);

  ili9341_WriteReg(LCD_SLEEP_OUT);
  HAL_Delay(200);
  ili9341_WriteReg(LCD_DISPLAY_ON);
  /* GRAM start writing */
  ili9341_WriteReg(LCD_GRAM);
}
