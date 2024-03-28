# STM32U5 Clock Configuration for T3T1, rev E.

## Overview

No HSE nor LSE is used.

We use 16 MHz HSI as PLL source.

160 MHz PLLCLK is used as system clock SYSCLK, which is not divided further, so HCLK is also 160 MHz.

APB1, APB2 and APB3 are also not divided, so PCLK1, PCLK2 and PCLK3 are all 160 MHz

CLK48 is derived from HSI48, which is 48 MHz.

## Peripherals

### USB FS
USB FS is clocked from CLK48, and CRS is used for clock synchronization.

### RNG
RNG is clocked from CLK48.

### SDMMC
SDMMC is clocked from CLK48.

### I2C1
I2C1 is clocked from PCLK1, 160 MHz

### I2C2
I2C2 is clocked from PCLK1, 160 MHz

### I2C3
I2C3 is clocked from PCLK3, 160 MHz

### SAES
SAES is clocked from SHSI, 48 MHz
