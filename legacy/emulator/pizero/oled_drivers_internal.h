/*
 * Modified Copyright (C) 2018, 2019 Yannick Heneault <yheneaul@gmail.com>
 * original code taken from : https://github.com/hallard/ArduiPi_OLED (ArduiPi_OLED.h)
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
All text above, and the splash screen must be included in any redistribution

02/18/2013  Charles-Henri Hallard (http://hallard.me)
            Modified for compiling and use on Raspberry ArduiPi Board
            LCD size and connection are now passed as arguments on 
            the command line (no more #define on compilation needed)
            ArduiPi project documentation http://hallard.me/arduipi
            
07/26/2013  Charles-Henri Hallard (http://hallard.me)
            modified name for generic library using different OLED type
 
*********************************************************************/

#ifndef __OLED_DRIVERS_INTERNAL_H__
#define __OLED_DRIVERS_INTERNAL_H__

// OLED type I2C Address
#define ADAFRUIT_I2C_ADDRESS   0x3C	/* 011110+SA0+RW - 0x3C or 0x3D */
#define SEEED_I2C_ADDRESS   0x3C	/* 011110+SA0+RW - 0x3C or 0x3D */
#define SH1106_I2C_ADDRESS   0x3C

/*=========================================================================
    SSDxxxx Common Displays
    -----------------------------------------------------------------------
    Common values to all displays
=========================================================================*/

#define SSD_Command_Mode      0x00	/* C0 and DC bit are 0         */
#define SSD_Data_Mode         0x40	/* C0 bit is 0 and DC bit is 1 */

#define SSD_Set_Segment_Remap   0xA0
#define SSD_Inverse_Display     0xA7
#define SSD_Set_Muliplex_Ratio  0xA8

#define SSD_Display_Off         0xAE
#define SSD_Display_On          0xAF

#define SSD_Set_ContrastLevel 0x81

#define SSD_External_Vcc      0x01
#define SSD_Internal_Vcc      0x02

#define SSD_Set_Column_Address  0x21
#define SSD_Set_Page_Address    0x22


/*=========================================================================
    SSD1306 Displays
    -----------------------------------------------------------------------
    The driver is used in multiple displays (128x64, 128x32, etc.).
=========================================================================*/

#define SSD1306_Entire_Display_Resume 0xA4
#define SSD1306_Entire_Display_On     0xA5

#define SSD1306_Normal_Display  0xA6

#define SSD1306_Set_Display_Offset      0xD3
#define SSD1306_Set_Com_Pins        0xDA
#define SSD1306_Set_Vcomh_Deselect_Level      0xDB
#define SSD1306_Set_Display_Clock_Div 0xD5
#define SSD1306_Set_Precharge_Period    0xD9
#define SSD1306_Set_Lower_Column_Start_Address        0x00
#define SSD1306_Set_Higher_Column_Start_Address       0x10
#define SSD1306_Set_Start_Line      0x40
#define SSD1306_Set_Memory_Mode     0x20
#define SSD1306_Set_Com_Output_Scan_Direction_Normal  0xC0
#define SSD1306_Set_Com_Output_Scan_Direction_Remap   0xC8
#define SSD1306_Charge_Pump_Setting 0x8D


/*=========================================================================
    SH1106 Displays
    -----------------------------------------------------------------------
    The driver is used in multiple displays (128x64, 128x32, etc.).
=========================================================================*/
#define SH1106_Set_Page_Address 0xB0

#endif
