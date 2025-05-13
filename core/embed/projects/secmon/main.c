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
#include <trezor_model.h>

#include <sec/entropy.h>
#include <sec/optiga_config.h>
#include <sec/random_delays.h>
#include <sec/secure_aes.h>
#include <sys/bootutils.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/sysutils.h>
#include <sys/trustzone.h>
#include <util/board_capabilities.h>
#include <util/unit_properties.h>

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

static void drivers_init(void) {
  parse_boardloader_capabilities();
  unit_properties_init();

#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
  entropy_init();

  random_delays_init();
#ifdef RDI
  random_delays_start_rdi();
#endif

#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif

#ifdef USE_TROPIC
  tropic_init();
#endif
}

static void setup_aircr_register() {
  uint32_t reg_value = SCB->AIRCR;

  reg_value &= ~SCB_AIRCR_VECTKEY_Msk;
  reg_value |= 0x5FAUL << SCB_AIRCR_VECTKEY_Pos;

  // Prioritize secure world interrupts over non-secure world
  reg_value |= SCB_AIRCR_PRIS_Msk;
  // System reset request available only in secure monitor
  reg_value |= SCB_AIRCR_SYSRESETREQS_Msk;
  // NMI, BusFault, HardFault are handled in both secure and non-secure worlds
  reg_value |= SCB_AIRCR_BFHFNMINS_Msk;

  SCB->AIRCR = reg_value;
}

static void isolate_nonsecure_world(void) {
  // Configure unprivileged access for the coreapp
  tz_init_secmon();

  tz_set_flash_unsecure(KERNEL_START, FIRMWARE_MAXSIZE - SECMON_MAXSIZE, true);
  tz_set_flash_unsecure(ASSETS_START, ASSETS_MAXSIZE, true);
  tz_set_sram_unsecure(SRAM1_BASE, SECMON_RAM_START - SRAM1_BASE, true);

  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_NSEC | GTZC_TZSC_PERIPH_PRIV);

  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_RNG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_SAES, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_I2C4, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  for (int i = 0; i < 512; i++) {
    NVIC_SetTargetState(i);
  }

  NVIC_ClearTargetState(GTZC_IRQn);

  // Make Backup SRAM accessible in non-secure mode

  GTZC_TZSC1->MPCWM4ACFGR =
      (GTZC_TZSC1->MPCWM4ACFGR & ~GTZC_TZSC_MPCWM_CFGR_SEC) |
      (GTZC_TZSC_MPCWM_CFGR_PRIV | GTZC_TZSC_MPCWM_CFGR_SREN);

  GTZC_TZSC1->MPCWM4AR =
      (GTZC_TZSC1->MPCWM4AR &
       (~GTZC_TZSC_MPCWMR_SUBZ_START | ~GTZC_TZSC_MPCWMR_SUBZ_LENGTH)) |
      (0 << GTZC_TZSC_MPCWMR_SUBZ_START_Pos) |
      ((2048 / 32) << GTZC_TZSC_MPCWMR_SUBZ_LENGTH_Pos);

  // Make GPDMA1 accessible in non-secure mode

  __HAL_RCC_GPDMA1_CLK_ENABLE();
  GPDMA1->SECCFGR &= ~0xFFFF;
  GPDMA1->PRIVCFGR |= 0xFFFF;

  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOI_CLK_ENABLE();
  __HAL_RCC_GPIOJ_CLK_ENABLE();

  GPIOA->SECCFGR &= ~0xFFFF;
  GPIOB->SECCFGR &= ~0xFFFF;
  GPIOC->SECCFGR &= ~0xFFFF;
  GPIOD->SECCFGR &= ~0xFFFF;
  GPIOE->SECCFGR &= ~0xFFFF;
  GPIOF->SECCFGR &= ~0xFFFF;
  GPIOG->SECCFGR &= ~0xFFFF;
  GPIOH->SECCFGR &= ~0xFFFF;
  GPIOI->SECCFGR &= ~0xFFFF;
  GPIOJ->SECCFGR &= ~0xFFFF;

#ifdef USE_OPTIGA
  OPTIGA_RST_PORT->SECCFGR |= OPTIGA_RST_PIN;
  OPTIGA_PWR_PORT->SECCFGR |= OPTIGA_PWR_PIN;
  I2C_INSTANCE_3_SCL_PORT->SECCFGR |= I2C_INSTANCE_3_SCL_PIN;
  I2C_INSTANCE_3_SDA_PORT->SECCFGR |= I2C_INSTANCE_3_SDA_PIN;
  NVIC_ClearTargetState(I2C_INSTANCE_3_EV_IRQn);  // !@#
  NVIC_ClearTargetState(I2C_INSTANCE_3_ER_IRQn);  // !@# use OPTIGA_INSTANCE
#endif

  setup_aircr_register();
}

// Secure monitor panic handler
// (may be called from interrupt context)
static void secmon_panic(const systask_postmortem_t *pminfo) {
  // Since the system state is unreliable, enter emergency mode,
  // store the postmortem info into bootargs and reboot.
  system_emergency_rescue(NULL, pminfo);
}

int main(void) {
  // Initialize system's core services
  system_init(secmon_panic);

  // Isolate hardware resources
  isolate_nonsecure_world();

  // Initialize secure monitor drivers
  drivers_init();

  // Jump to the kernel (non-secure world)
  jump_to_vectbl_ns(KERNEL_START + 0x800);
}
