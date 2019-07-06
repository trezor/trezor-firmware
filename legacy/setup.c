/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include <libopencm3/cm3/mpu.h>
#include <libopencm3/cm3/nvic.h>
#include <libopencm3/cm3/scb.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/rng.h>
#include <libopencm3/stm32/spi.h>

#include "layout.h"
#include "rng.h"
#include "util.h"

uint32_t __stack_chk_guard;

static inline void __attribute__((noreturn)) fault_handler(const char *line1) {
  layoutDialog(&bmp_icon_error, NULL, NULL, NULL, line1, "detected.", NULL,
               "Please unplug", "the device.", NULL);
  shutdown();
}

void __attribute__((noreturn)) __stack_chk_fail(void) {
  fault_handler("Stack smashing");
}

void nmi_handler(void) {
  // Clock Security System triggered NMI
  if ((RCC_CIR & RCC_CIR_CSSF) != 0) {
    fault_handler("Clock instability");
  }
}

void hard_fault_handler(void) { fault_handler("Hard fault"); }

void mem_manage_handler(void) { fault_handler("Memory fault"); }

void setup(void) {
  // set SCB_CCR STKALIGN bit to make sure 8-byte stack alignment on exception
  // entry is in effect. This is not strictly necessary for the current Trezor
  // system. This is here to comply with guidance from section 3.3.3 "Binary
  // compatibility with other Cortex processors" of the ARM Cortex-M3 Processor
  // Technical Reference Manual. According to section 4.4.2 and 4.4.7 of the
  // "STM32F10xxx/20xxx/21xxx/L1xxxx Cortex-M3 programming manual", STM32F2
  // series MCUs are r2p0 and always have this bit set on reset already.
  SCB_CCR |= SCB_CCR_STKALIGN;

  // setup clock
  struct rcc_clock_scale clock = rcc_hse_8mhz_3v3[RCC_CLOCK_3V3_120MHZ];
  rcc_clock_setup_hse_3v3(&clock);

  // enable GPIO clock - A (oled), B(oled), C (buttons)
  rcc_periph_clock_enable(RCC_GPIOA);
  rcc_periph_clock_enable(RCC_GPIOB);
  rcc_periph_clock_enable(RCC_GPIOC);

  // enable SPI clock
  rcc_periph_clock_enable(RCC_SPI1);

  // enable RNG
  rcc_periph_clock_enable(RCC_RNG);
  RNG_CR |= RNG_CR_RNGEN;
  // to be extra careful and heed the STM32F205xx Reference manual,
  // Section 20.3.1 we don't use the first random number generated after setting
  // the RNGEN bit in setup
  random32();

  // enable CSS (Clock Security System)
  RCC_CR |= RCC_CR_CSSON;

  // set GPIO for buttons
  gpio_mode_setup(GPIOC, GPIO_MODE_INPUT, GPIO_PUPD_PULLUP, GPIO2 | GPIO5);

  // set GPIO for OLED display
  gpio_mode_setup(GPIOA, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, GPIO4);
  gpio_mode_setup(GPIOB, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, GPIO0 | GPIO1);

  // enable SPI 1 for OLED display
  gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO5 | GPIO7);
  gpio_set_af(GPIOA, GPIO_AF5, GPIO5 | GPIO7);

  //	spi_disable_crc(SPI1);
  spi_init_master(
      SPI1, SPI_CR1_BAUDRATE_FPCLK_DIV_8, SPI_CR1_CPOL_CLK_TO_0_WHEN_IDLE,
      SPI_CR1_CPHA_CLK_TRANSITION_1, SPI_CR1_DFF_8BIT, SPI_CR1_MSBFIRST);
  spi_enable_ss_output(SPI1);
  //	spi_enable_software_slave_management(SPI1);
  //	spi_set_nss_high(SPI1);
  //	spi_clear_mode_fault(SPI1);
  spi_enable(SPI1);

  // enable OTG_FS
  gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_PULLUP, GPIO10);
  gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO11 | GPIO12);
  gpio_set_af(GPIOA, GPIO_AF10, GPIO10 | GPIO11 | GPIO12);

  // enable OTG FS clock
  rcc_periph_clock_enable(RCC_OTGFS);
  // clear USB OTG_FS peripheral dedicated RAM
  memset_reg((void *)0x50020000, (void *)0x50020500, 0);
}

void setupApp(void) {
  // for completeness, disable RNG peripheral interrupts for old bootloaders
  // that had enabled them in RNG control register (the RNG interrupt was never
  // enabled in the NVIC)
  RNG_CR &= ~RNG_CR_IE;
  // the static variables in random32 are separate between the bootloader and
  // firmware. therefore, they need to be initialized here so that we can be
  // sure to avoid dupes. this is to try to comply with STM32F205xx Reference
  // manual - Section 20.3.1: "Each subsequent generated random number has to be
  // compared with the previously generated number. The test fails if any two
  // compared numbers are equal (continuous random number generator test)."
  random32();

  // enable CSS (Clock Security System)
  RCC_CR |= RCC_CR_CSSON;

  // hotfix for old bootloader
  gpio_mode_setup(GPIOA, GPIO_MODE_INPUT, GPIO_PUPD_NONE, GPIO9);
  spi_init_master(
      SPI1, SPI_CR1_BAUDRATE_FPCLK_DIV_8, SPI_CR1_CPOL_CLK_TO_0_WHEN_IDLE,
      SPI_CR1_CPHA_CLK_TRANSITION_1, SPI_CR1_DFF_8BIT, SPI_CR1_MSBFIRST);

  gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_PULLUP, GPIO10);
  gpio_set_af(GPIOA, GPIO_AF10, GPIO10);
}

#define MPU_RASR_SIZE_32B (0x04UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_1KB (0x09UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_4KB (0x0BUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_8KB (0x0CUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_16KB (0x0DUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_32KB (0x0EUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_64KB (0x0FUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_128KB (0x10UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_256KB (0x11UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_512KB (0x12UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_1MB (0x13UL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_512MB (0x1CUL << MPU_RASR_SIZE_LSB)
#define MPU_RASR_SIZE_4GB (0x1FUL << MPU_RASR_SIZE_LSB)

// http://infocenter.arm.com/help/topic/com.arm.doc.dui0552a/BABDJJGF.html
#define MPU_RASR_ATTR_FLASH (MPU_RASR_ATTR_C)
#define MPU_RASR_ATTR_SRAM (MPU_RASR_ATTR_C | MPU_RASR_ATTR_S)
#define MPU_RASR_ATTR_PERIPH (MPU_RASR_ATTR_B | MPU_RASR_ATTR_S)

#define FLASH_BASE (0x08000000U)
#define SRAM_BASE (0x20000000U)

void mpu_config_off(void) {
  // Disable MPU
  MPU_CTRL = 0;

  __asm__ volatile("dsb");
  __asm__ volatile("isb");
}

void mpu_config_bootloader(void) {
  // Disable MPU
  MPU_CTRL = 0;

  // Note: later entries overwrite previous ones

  // Everything (0x00000000 - 0xFFFFFFFF, 4 GiB, read-write)
  MPU_RBAR = 0 | MPU_RBAR_VALID | (0 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_FLASH | MPU_RASR_SIZE_4GB |
             MPU_RASR_ATTR_AP_PRW_URW;

  // Flash (0x8007FE0 - 0x08007FFF, 32 B, no-access)
  MPU_RBAR =
      (FLASH_BASE + 0x7FE0) | MPU_RBAR_VALID | (1 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_FLASH | MPU_RASR_SIZE_32B |
             MPU_RASR_ATTR_AP_PNO_UNO;

  // SRAM (0x20000000 - 0x2001FFFF, read-write, execute never)
  MPU_RBAR = SRAM_BASE | MPU_RBAR_VALID | (2 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_SRAM | MPU_RASR_SIZE_128KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;

  // Peripherals (0x40000000 - 0x4001FFFF, read-write, execute never)
  MPU_RBAR = PERIPH_BASE | MPU_RBAR_VALID | (3 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_128KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;
  // Peripherals (0x40020000 - 0x40023FFF, read-write, execute never)
  MPU_RBAR = 0x40020000 | MPU_RBAR_VALID | (4 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_16KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;
  // Don't enable DMA controller access
  // Peripherals (0x50000000 - 0x5007ffff, read-write, execute never)
  MPU_RBAR = 0x50000000 | MPU_RBAR_VALID | (5 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_512KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;

  // Enable MPU
  MPU_CTRL = MPU_CTRL_ENABLE | MPU_CTRL_HFNMIENA;

  // Enable memory fault handler
  SCB_SHCSR |= SCB_SHCSR_MEMFAULTENA;

  __asm__ volatile("dsb");
  __asm__ volatile("isb");
}

// Never use in bootloader! Disables access to PPB (including MPU, NVIC, SCB)
void mpu_config_firmware(void) {
#if MEMORY_PROTECT
  // Disable MPU
  MPU_CTRL = 0;

  // Note: later entries overwrite previous ones

  // Flash (0x08000000 - 0x0807FFFF, 1 MiB, read-only)
  MPU_RBAR = FLASH_BASE | MPU_RBAR_VALID | (0 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_FLASH | MPU_RASR_SIZE_1MB |
             MPU_RASR_ATTR_AP_PRO_URO;

  // Metadata in Flash is read-write when unlocked
  // (0x08008000 - 0x0800FFFF, 32 KiB, read-write, execute never)
  MPU_RBAR =
      (FLASH_BASE + 0x8000) | MPU_RBAR_VALID | (1 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_FLASH | MPU_RASR_SIZE_32KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;

  // SRAM (0x20000000 - 0x2001FFFF, read-write, execute never)
  MPU_RBAR = SRAM_BASE | MPU_RBAR_VALID | (2 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_SRAM | MPU_RASR_SIZE_128KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;

  // Peripherals (0x40000000 - 0x4001FFFF, read-write, execute never)
  MPU_RBAR = PERIPH_BASE | MPU_RBAR_VALID | (3 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_128KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;
  // Peripherals (0x40020000 - 0x40023FFF, read-write, execute never)
  MPU_RBAR = 0x40020000 | MPU_RBAR_VALID | (4 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_16KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;
  // Flash controller is protected
  // (0x40023C00 - 0x40023FFF, privileged read-write, user no, execute never)
  MPU_RBAR = 0x40023c00 | MPU_RBAR_VALID | (5 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_1KB |
             MPU_RASR_ATTR_AP_PRW_UNO | MPU_RASR_ATTR_XN;
  // Don't enable DMA controller access
  // Peripherals (0x50000000 - 0x5007ffff, read-write, execute never)
  MPU_RBAR = 0x50000000 | MPU_RBAR_VALID | (6 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_512KB |
             MPU_RASR_ATTR_AP_PRW_URW | MPU_RASR_ATTR_XN;
  // SYSCFG_* registers are disabled
  // (0x40013800 - 0x40013BFF, read-only, execute never)
  MPU_RBAR = 0x40013800 | MPU_RBAR_VALID | (7 << MPU_RBAR_REGION_LSB);
  MPU_RASR = MPU_RASR_ENABLE | MPU_RASR_ATTR_PERIPH | MPU_RASR_SIZE_1KB |
             MPU_RASR_ATTR_AP_PRO_URO | MPU_RASR_ATTR_XN;

  // Enable MPU
  MPU_CTRL = MPU_CTRL_ENABLE | MPU_CTRL_HFNMIENA;

  // Enable memory fault handler
  SCB_SHCSR |= SCB_SHCSR_MEMFAULTENA;

  __asm__ volatile("dsb");
  __asm__ volatile("isb");

  // Switch to unprivileged software execution to prevent access to MPU
  set_mode_unprivileged();
#endif
}
