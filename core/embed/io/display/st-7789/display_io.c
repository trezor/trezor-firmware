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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/irq.h>
#include <sys/mpu.h>
#include "display_io.h"

__IO DISP_MEM_TYPE *const DISPLAY_CMD_ADDRESS =
    (__IO DISP_MEM_TYPE *const)((uint32_t)DISPLAY_MEMORY_BASE);
__IO DISP_MEM_TYPE *const DISPLAY_DATA_ADDRESS =
    (__IO DISP_MEM_TYPE *const)((uint32_t)DISPLAY_MEMORY_BASE |
                                (DISPLAY_ADDR_SHIFT << DISPLAY_MEMORY_PIN));

#ifdef KERNEL_MODE

void display_io_init_gpio(void) {
  // init peripherals
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  // LCD_RST/PC14
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_14;
  // default to keeping display in reset
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

#ifdef DISPLAY_TE_PIN
  // LCD_FMARK (tearing effect)
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = DISPLAY_TE_PIN;
  HAL_GPIO_Init(DISPLAY_TE_PORT, &GPIO_InitStructure);
#endif

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF12_FMC;
  //                       LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_11 | GPIO_PIN_4 | GPIO_PIN_5;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D0/PD14   LCD_D1/PD15   LCD_D2/PD0   LCD_D3/PD1
  GPIO_InitStructure.Pin = GPIO_PIN_14 | GPIO_PIN_15 | GPIO_PIN_0 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D4/PE7   LCD_D5/PE8   LCD_D6/PE9   LCD_D7/PE10
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
#ifdef DISPLAY_I8080_16BIT_DW
  //                       LCD_D8/PE11   LCD_D9/PE12   LCD_D10/PE13 LCD_D11/PE14
  GPIO_InitStructure.Pin =
      GPIO_PIN_11 | GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
  //                       LCD_D12/PE15
  GPIO_InitStructure.Pin = GPIO_PIN_15;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
  //                       LCD_D13/PD8   LCD_D14/PD9   LCD_D15/PD10
  GPIO_InitStructure.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
#endif
}

void display_io_init_fmc(void) {
  __HAL_RCC_FMC_CLK_ENABLE();

  // Reference UM1725 "Description of STM32F4 HAL and LL drivers",
  // section 64.2.1 "How to use this driver"
  SRAM_HandleTypeDef external_display_data_sram = {0};
  external_display_data_sram.Instance = FMC_NORSRAM_DEVICE;
  external_display_data_sram.Extended = FMC_NORSRAM_EXTENDED_DEVICE;
  external_display_data_sram.Init.NSBank = FMC_NORSRAM_BANK1;
  external_display_data_sram.Init.DataAddressMux = FMC_DATA_ADDRESS_MUX_DISABLE;
  external_display_data_sram.Init.MemoryType = FMC_MEMORY_TYPE_SRAM;
#ifdef DISPLAY_I8080_16BIT_DW
  external_display_data_sram.Init.MemoryDataWidth =
      FMC_NORSRAM_MEM_BUS_WIDTH_16;
#elif DISPLAY_I8080_8BIT_DW
  external_display_data_sram.Init.MemoryDataWidth = FMC_NORSRAM_MEM_BUS_WIDTH_8;
#endif
  external_display_data_sram.Init.BurstAccessMode =
      FMC_BURST_ACCESS_MODE_DISABLE;
  external_display_data_sram.Init.WaitSignalPolarity =
      FMC_WAIT_SIGNAL_POLARITY_LOW;
  external_display_data_sram.Init.WaitSignalActive = FMC_WAIT_TIMING_BEFORE_WS;
  external_display_data_sram.Init.WriteOperation = FMC_WRITE_OPERATION_ENABLE;
  external_display_data_sram.Init.WaitSignal = FMC_WAIT_SIGNAL_DISABLE;
  external_display_data_sram.Init.ExtendedMode = FMC_EXTENDED_MODE_DISABLE;
  external_display_data_sram.Init.AsynchronousWait =
      FMC_ASYNCHRONOUS_WAIT_DISABLE;
  external_display_data_sram.Init.WriteBurst = FMC_WRITE_BURST_DISABLE;
  external_display_data_sram.Init.ContinuousClock =
      FMC_CONTINUOUS_CLOCK_SYNC_ONLY;
  external_display_data_sram.Init.PageSize = FMC_PAGE_SIZE_NONE;

  // reference RM0090 section 37.5 Table 259, 37.5.4, Mode 1 SRAM, and 37.5.6
  FMC_NORSRAM_TimingTypeDef normal_mode_timing = {0};
  normal_mode_timing.AddressSetupTime = 5;
  normal_mode_timing.AddressHoldTime = 1;  // don't care
  normal_mode_timing.DataSetupTime = 6;
  normal_mode_timing.BusTurnAroundDuration = 0;  // don't care
  normal_mode_timing.CLKDivision = 2;            // don't care
  normal_mode_timing.DataLatency = 2;            // don't care
  normal_mode_timing.AccessMode = FMC_ACCESS_MODE_A;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_FSMC_REGS);
  HAL_SRAM_Init(&external_display_data_sram, &normal_mode_timing, NULL);
  mpu_restore(mpu_mode);
}

#ifdef DISPLAY_TE_INTERRUPT_HANDLER
void display_io_init_te_interrupt(void) {
  EXTI_HandleTypeDef EXTI_Handle = {0};
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = DISPLAY_TE_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = DISPLAY_TE_INTERRUPT_EXTI_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&EXTI_Handle, &EXTI_Config);

  // setup interrupt for tearing effect pin
  NVIC_SetPriority(DISPLAY_TE_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(DISPLAY_TE_INTERRUPT_NUM);
}
#endif

#endif  // KERNEL_MODE
