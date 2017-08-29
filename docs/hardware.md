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

* 1 x [Waveshare Core405R Dev Board](http://www.waveshare.com/core405r.htm)
* 1 x USB Cable Type A Plug/Male to Type Mini-B Plug/Male
* 1 x ST-LINK V2 STM32 USB Debug Adapter
* Female to female jumper wires with 0.1" header contacts
* 1 x Display
* 1 x Capacitive Touch Panel / Sensor
* 1 x microSD Socket
* TODO

### Component Notes

#### Display
* Resolution: 240px x 240px -OR- 240px x 320px
* Driver IC: ST7789V or ILI9341V (on-chip display data RAM of 240x320x18 bits)
* 18-bit (262,144) RGB color graphic type TFT-LCD
* Bus/Interface: 8-bit parallel

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|LCD_RST|PC14|
|LCD_FMARK|PD12 [TODO: what is this for?]|
|LCD_PWM|PB13 [TODO: what is this for?]|
|LCD_CS|PD7|
|LCD_RS|PD11|
|LCD_RD|PD4|
|LCD_WR|PD5|
|LCD_D0|PD14|
|LCD_D1|PD15|
|LCD_D2|PD0|
|LCD_D3|PD1|
|LCD_D4|PE7|
|LCD_D5|PE8|
|LCD_D6|PE9|
|LCD_D7|PE10|

#### Capacitive Touch Panel / Sensor
* Bus/Interface: I2C
* Driver IC: FT6206 [TODO: does this matter]
* single touch

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|I2C1_SCL|PB6|
|I2C1_SDA|PB7|
|CTP_IRQ|[TODO: missing?]|

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

##### Pinout

|Description|MCU Pin|
|-----------|-------|
|OTG_FS_VBUS|PA9|
|OTG_FS_ID|PA10|
|OTG_FS_DM|PA11|
|OTG_FS_DP|PA12|

#### Dev Board
* [Schematic](http://www.waveshare.com/w/upload/0/05/CorexxxR-Schematic.pdf)
* [STM32F405RGT6](http://www.st.com/en/microcontrollers/stm32f405rg.html)
* HSE / High-Speed External Crystal: 8 MHz

