# TREZOR Core Hardware

## TREZOR v2 Open Source Hardware Reference Documentation

### Photo Front
TODO

### Photo Back
TODO

### Bill of Materials / BOM
TODO

### Eagle Schematic
TODO

### Eagle Board
TODO

## Developer Kit

* 1 x [STM32F407G-DISC1](http://www.st.com/en/evaluation-tools/stm32f4discovery.html)
* 1 x USB Cable Type A Plug/Male to Type Mini-B Plug/Male
* 1 x USB Cable Type A Plug/Male to Type Micro-B Plug/Male
* 1 x [ER-TFTM028-4 Display + Capacitive Touch Panel Module](http://www.ebay.com/itm/302049581340) (Note: specify 40-Pin Header, 8080 8-bit Parallel, VDD=3.3V, Capacitive Touch Panel)
* 1 x [microSD Board](https://www.waveshare.com/product/modules/storage/sd-tf-storage/micro-sd-storage-board.htm)
* 32 x Female to female jumper wires with 0.1" header contacts

#### Display

* Resolution: 240px x 240px -OR- 240px x 320px
* Driver IC: ST7789V or ILI9341V (on-chip display data RAM of 240x320x18 bits)
* 18-bit (262,144) RGB color graphic type TFT-LCD
* Bus/Interface: 8-bit parallel

##### Pinout

|Description|MCU Pin|Notes|
|-----------|-------|-----|
|LCD_RST|PC14||
|LCD_FMARK|PD12|tearing effect input|
|LCD_PWM|PA7|backlight control (brightness)|
|LCD_CS|PD7||
|LCD_RS|PD11|register select aka command/data|
|LCD_RD|PD4||
|LCD_WR|PD5||
|LCD_D0|PD14||
|LCD_D1|PD15||
|LCD_D2|PD0||
|LCD_D3|PD1||
|LCD_D4|PE7||
|LCD_D5|PE8||
|LCD_D6|PE9||
|LCD_D7|PE10||

#### Capacitive Touch Panel / Sensor

* Bus/Interface: I2C
* Driver IC: FT6206
* single touch

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|I2C1_SCL|PB6|
|I2C1_SDA|PB7|

#### microSD Socket

* Bus/Interface: 4-bit

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|SDIO_D0|PC8|
|SDIO_D1|PC9|
|SDIO_D2|PC10|
|SDIO_D3|PC11|
|SDIO_CK|PC12|
|SDIO_CMD|PD2|
|SD_CARDDETECT|PC13|

#### USB Socket

* USB HS (high-speed) peripheral in FS (full-speed) mode

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|OTG_HS_VBUS|PB13|
|OTG_HS_ID|PB12|
|OTG_HS_DM|PB14|
|OTG_HS_DP|PB15|

#### Dev Board

* [STM32F407VGT6](http://www.st.com/content/st_com/en/products/microcontrollers/stm32-32-bit-arm-cortex-mcus/stm32-high-performance-mcus/stm32f4-series/stm32f407-417/stm32f407vg.html)
* HSE / High-Speed External Crystal: 8 MHz
* Integrated STMicroelectronics ST-LINK/V2.1 debugger

Minimum MCU requirements:
* STM32F4 family [STM32F405VGT6](http://www.st.com/content/st_com/en/products/microcontrollers/stm32-32-bit-arm-cortex-mcus/stm32-high-performance-mcus/stm32f4-series/stm32f405-415/stm32f405vg.html)
* 168 MHz, 8 MHz HSE
* 1024 KB Flash memory
* 128 KB SRAM
* 64 KB CCMRAM
* FSMC controller
* TRNG

