/*
 * Modified Copyright (C) 2018, 2019 Yannick Heneault <yheneaul@gmail.com>
 * original code taken from : https://github.com/hallard/ArduiPi_OLED (ArduiPi_OLED.cpp)
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

/*********************************************************************
This is a library for our Monochrome OLEDs based on SSD1306 drivers

  Pick one up today in the adafruit shop!
  ------> http://www.adafruit.com/category/63_98

These displays use SPI to communicate, 4 or 5 pins are required to
interface

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from Adafruit!

Written by Limor Fried/Ladyada  for Adafruit Industries.
BSD license, check license.txt for more information
All text above, and the splash screen below must be included in any redistribution

02/18/2013  Charles-Henri Hallard (http://hallard.me)
            Modified for compiling and use on Raspberry ArduiPi Board
            LCD size and connection are now passed as arguments on
            the command line (no more #define on compilation needed)
            ArduiPi project documentation http://hallard.me/arduipi
07/01/2013  Charles-Henri Hallard
            Reduced code size removed the Adafruit Logo (sorry guys)
            Buffer for OLED is now dynamic to LCD size
            Added support of Seeed OLED 64x64 Display

07/26/2013  Charles-Henri Hallard
            modified name for generic library using different OLED type

02/24/2015  Charles-Henri Hallard
            added support for 1.3" I2C OLED with SH1106 driver

*********************************************************************/

#include <stdlib.h>
#include <unistd.h>

#include "bcm2835.h"

#include "oled_drivers.h"
#include "oled_drivers_internal.h"

// Init all var, and clean
// Command I/O
static uint8_t oled_type;
static int8_t i2c_addr;
static uint8_t vcc_type;
static int8_t dc, rst, cs;
static bool flip;

// Lcd size
#define oled_width 128
#define oled_height 64
#define oled_buff_size (oled_width * oled_height / 8)

static inline bool isSPI(void) {
	return (cs != -1 ? true : false);
}

static inline void fastI2Cwrite(char *tbuf, uint32_t len) {
	bcm2835_i2c_write(tbuf, len);
}

static inline void fastSPIwrite(uint8_t d) {
	bcm2835_spi_transfer(d);
}

static inline void fastSPIwriteBuffer(char *tbuf, uint32_t len) {
	bcm2835_spi_writenb(tbuf, len);
}

static void sendCommandByte(uint8_t c) {
	// Is SPI
	if (isSPI()) {
		// Setup D/C line to low to switch to command mode
		bcm2835_gpio_write(dc, LOW);

		// Write Data on SPI
		fastSPIwrite(c);
	}
	// so I2C
	else {
		char buff[2];

		// Clear D/C to switch to command mode
		buff[0] = SSD_Command_Mode;
		buff[1] = c;

		// Write Data on I2C
		fastI2Cwrite(buff, sizeof(buff));
	}
}

static void sendCommand2Bytes(uint8_t c0, uint8_t c1) {
	char buff[3];
	buff[1] = c0;
	buff[2] = c1;

	// Is SPI
	if (isSPI()) {
		// Setup D/C line to low to switch to command mode
		bcm2835_gpio_write(dc, LOW);

		// Write Data
		fastSPIwriteBuffer(&buff[1], 2);
	}
	// I2C
	else {
		// Clear D/C to switch to command mode
		buff[0] = SSD_Command_Mode;

		// Write Data on I2C
		fastI2Cwrite(buff, 3);
	}
}

static void sendCommand3Bytes(uint8_t c0, uint8_t c1, uint8_t c2) {
	char buff[4];

	buff[1] = c0;
	buff[2] = c1;
	buff[3] = c2;

	// Is SPI
	if (isSPI()) {
		// Setup D/C line to low to switch to command mode
		bcm2835_gpio_write(dc, LOW);

		// Write Data
		fastSPIwriteBuffer(&buff[1], 3);
	}
	// I2C
	else {
		// Clear D/C to switch to command mode
		buff[0] = SSD_Command_Mode;

		// Write Data on I2C
		fastI2Cwrite(buff, sizeof(buff));
	}
}

// initializer for OLED Type
static bool oled_select(uint8_t OLED_TYPE) {
	// Default type
	oled_type = OLED_TYPE;

	// default OLED are using internal boost VCC converter
	vcc_type = SSD_Internal_Vcc;

	// Oled supported display
	// Setup size and I2C address
	switch (OLED_TYPE) {
		case OLED_ADAFRUIT_SPI_128x64:
		case OLED_SH1106_SPI_128x64:
			break;

		case OLED_ADAFRUIT_I2C_128x64:
			i2c_addr = ADAFRUIT_I2C_ADDRESS;
			break;

		case OLED_SEEED_I2C_128x64:
			i2c_addr = SEEED_I2C_ADDRESS;
			vcc_type = SSD_External_Vcc;
			break;

		case OLED_SH1106_I2C_128x64:
			i2c_addr = SH1106_I2C_ADDRESS;
			break;

			// houston, we have a problem
		default:
			return false;
			break;
	}

	return true;
}

static void oled_begin(void) {
	uint8_t multiplex;
	uint8_t chargepump;
	uint8_t compins;
	uint8_t contrast;
	uint8_t precharge;

	if (rst != -1) {
		bcm2835_gpio_write(rst, HIGH);

		// VDD (3.3V) goes high at start, lets just chill for a ms
		usleep(1000);

		// bring reset low
		bcm2835_gpio_write(rst, LOW);

		// wait 10ms
		usleep(10000);

		// bring out of reset
		bcm2835_gpio_write(rst, HIGH);
	}

	multiplex = 0x3F;
	compins = 0x12;

	if (oled_type == OLED_SH1106_I2C_128x64 || oled_type == OLED_SH1106_SPI_128x64) {
		contrast = 0x80;
	} else {
		contrast = (vcc_type == SSD_External_Vcc ? 0x9F : 0xCF);
	}

	if (vcc_type == SSD_External_Vcc) {
		chargepump = 0x10;
		precharge = 0x22;
	} else {
		chargepump = 0x14;
		precharge = 0xF1;
	}

	sendCommandByte(SSD_Display_Off);
	sendCommand2Bytes(SSD_Set_Muliplex_Ratio, multiplex);

	if (oled_type == OLED_SH1106_I2C_128x64 || oled_type == OLED_SH1106_SPI_128x64) {
		sendCommandByte(SSD1306_Set_Lower_Column_Start_Address | 0x02);	/*set lower column address */
		sendCommandByte(SSD1306_Set_Higher_Column_Start_Address);	/*set higher column address */
		sendCommandByte(SSD1306_Set_Start_Line);	/*set display start line */
		sendCommandByte(SH1106_Set_Page_Address);	/*set page address */

		if (flip) {
			sendCommandByte(SSD_Set_Segment_Remap);
			sendCommandByte(SSD1306_Set_Com_Output_Scan_Direction_Normal);
		} else {
			sendCommandByte(SSD_Set_Segment_Remap | 0x1);
			sendCommandByte(SSD1306_Set_Com_Output_Scan_Direction_Remap);
		}

		sendCommandByte(SSD1306_Normal_Display);	/*normal / reverse */
		sendCommandByte(0xad);	/*set charge pump enable */
		sendCommandByte(0x8b);	/*external VCC   */
		sendCommandByte(0x30);	/*0X30---0X33  set VPP   9V liangdu!!!! */
		sendCommandByte(SSD1306_Set_Display_Offset);	/*set display offset */
		sendCommandByte(0x00);	/*   0x20  */
		sendCommandByte(SSD1306_Set_Display_Clock_Div);	/*set osc division */
		sendCommandByte(0x80);
		sendCommandByte(SSD1306_Set_Precharge_Period);	/*set pre-charge period */
		sendCommandByte(0x1f);	/*0x22 */
		sendCommandByte(SSD1306_Set_Com_Pins);	/*set COM pins */
		sendCommandByte(0x12);
		sendCommandByte(SSD1306_Set_Vcomh_Deselect_Level);	/*set vcomh */
		sendCommandByte(0x40);
	} else {
		sendCommand2Bytes(SSD1306_Charge_Pump_Setting, chargepump);
		sendCommand2Bytes(SSD1306_Set_Memory_Mode, 0x00);	// 0x20 0x0 act like ks0108
		sendCommand2Bytes(SSD1306_Set_Display_Clock_Div, 0x80);	// 0xD5 + the suggested ratio 0x80
		sendCommand2Bytes(SSD1306_Set_Display_Offset, 0x00);	// no offset
		sendCommandByte(SSD1306_Set_Start_Line | 0x0);	// line #0

		if (flip) {
			sendCommandByte(SSD_Set_Segment_Remap);
			sendCommandByte(SSD1306_Set_Com_Output_Scan_Direction_Normal);
		} else {
			sendCommandByte(SSD_Set_Segment_Remap | 0x1);
			sendCommandByte(SSD1306_Set_Com_Output_Scan_Direction_Remap);
		}

		sendCommand2Bytes(SSD1306_Set_Com_Pins, compins);
		sendCommand2Bytes(SSD1306_Set_Precharge_Period, precharge);
		sendCommand2Bytes(SSD1306_Set_Vcomh_Deselect_Level, 0x40);	// 0x40 -> unknown value in datasheet
		sendCommandByte(SSD1306_Entire_Display_Resume);
		sendCommandByte(SSD1306_Normal_Display);	// 0xA6

		// Reset to default value in case of
		// no reset pin available on OLED,
		sendCommand3Bytes(SSD_Set_Column_Address, 0, 127);
		sendCommand3Bytes(SSD_Set_Page_Address, 0, 7);
	}

	sendCommand2Bytes(SSD_Set_ContrastLevel, contrast);

	// turn on oled panel
	sendCommandByte(SSD_Display_On);
}

static bool oled_init_spi(uint8_t OLED_TYPE) {
	rst = RPI_V2_GPIO_P1_22;
	dc = RPI_V2_GPIO_P1_18;
	cs = BCM2835_SPI_CS0;

	// Select OLED parameters
	if (!oled_select(OLED_TYPE))
		return false;

	// Init & Configure Raspberry PI SPI
	bcm2835_spi_begin();
	bcm2835_spi_chipSelect(cs);
	bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);
	bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);

	// 16 MHz SPI bus, but Worked at 62 MHz also
	bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_16);

	// Set the pin that will control DC as output
	bcm2835_gpio_fsel(dc, BCM2835_GPIO_FSEL_OUTP);

	// Setup reset pin direction as output
	bcm2835_gpio_fsel(rst, BCM2835_GPIO_FSEL_OUTP);

	oled_begin();

	return (true);
}

static bool oled_init_i2c(uint8_t OLED_TYPE) {
	// Select OLED parameters
	if (!oled_select(OLED_TYPE))
		return false;

	// Init & Configure Raspberry PI I2C
	if (bcm2835_i2c_begin() == 0)
		return false;

	bcm2835_i2c_setSlaveAddress(i2c_addr);

	bcm2835_i2c_set_baudrate(400000);

	oled_begin();

	return (true);
}

bool oled_init(uint8_t OLED_TYPE, bool FLIP) {

	flip = FLIP;
	i2c_addr = rst = dc = cs = -1;

	switch (OLED_TYPE) {
		case OLED_ADAFRUIT_SPI_128x64:
		case OLED_SH1106_SPI_128x64:
			return oled_init_spi(OLED_TYPE);
		case OLED_ADAFRUIT_I2C_128x64:
		case OLED_SEEED_I2C_128x64:
		case OLED_SH1106_I2C_128x64:
			return oled_init_i2c(OLED_TYPE);
	}

	return false;
}

static void oled_display_sh1106(const uint8_t * p) {
	char buff[33];
	uint8_t pixel_offset;

	for (uint8_t k = 0; k < 8; k++) {

		sendCommandByte(0xB0 + k);	//set page addressSSD_Data_Mode;
		sendCommandByte(0x02);	//set lower column address
		sendCommandByte(0x10);	//set higher column address

		if (isSPI()) {
			bcm2835_gpio_write(dc, HIGH);
			pixel_offset = 0;
		} else {
			buff[0] = SSD_Data_Mode;
			pixel_offset = 1;
		}

		for (uint16_t i = 0; i < 4; i++) {
			for (uint8_t x = 0; x < 32; x++)
				buff[x + pixel_offset] = *p++;

			if (isSPI())
				fastSPIwriteBuffer(buff, 32);
			else
				fastI2Cwrite(buff, 33);
		}
	}
}

void oled_display(const uint8_t * p) {
	sendCommandByte(SSD1306_Set_Lower_Column_Start_Address | 0x0);	// low col = 0
	sendCommandByte(SSD1306_Set_Higher_Column_Start_Address | 0x0);	// hi col = 0
	sendCommandByte(SSD1306_Set_Start_Line | 0x0);	// line #0

	if (oled_type == OLED_SH1106_I2C_128x64 || oled_type == OLED_SH1106_SPI_128x64) {
		oled_display_sh1106(p);
		return;
	}

	if (isSPI()) {
		// Setup D/C line to high to switch to data mode
		bcm2835_gpio_write(dc, HIGH);

		// Send all data to OLED
		for (uint16_t i = 0; i < oled_buff_size; i++)
			fastSPIwrite(*p++);
	}
	// I2C
	else {
		char buff[33];
		uint8_t x;

		// Setup D/C to switch to data mode
		buff[0] = SSD_Data_Mode;

		// loop trough all OLED buffer and
		// send a bunch of 32 data byte in one xmission
		for (uint16_t i = 0; i < oled_buff_size; i += 32) {
			for (x = 1; x <= 32; x++)
				buff[x] = *p++;

			fastI2Cwrite(buff, 33);
		}
	}
}
