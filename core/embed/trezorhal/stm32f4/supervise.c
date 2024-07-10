#include STM32_HAL_H

#include <model.h>

#include "../mpu.h"
#include "common.h"
#include "display.h"
#include "supervise.h"

#ifdef ARM_USER_MODE

#ifdef STM32U5
extern uint32_t g_boot_command;
__attribute__((noreturn)) static void _reboot_to_bootloader(
    boot_command_t boot_command) {
  g_boot_command = boot_command;
  __disable_irq();
  delete_secrets();
  NVIC_SystemReset();
}
#else
__attribute__((noreturn)) static void _reboot_to_bootloader(
    boot_command_t boot_command) {
  mpu_config_bootloader();
  jump_to_with_flag(IMAGE_CODE_ALIGN(BOOTLOADER_START + IMAGE_HEADER_SIZE),
                    boot_command);
  for (;;)
    ;
}
#endif

void svc_reboot_to_bootloader(void) {
  display_finish_actions();
  boot_command_t boot_command = bootargs_get_command();
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register uint32_t r0 __asm__("r0") = boot_command;
    __asm__ __volatile__("svc %0" ::"i"(SVC_REBOOT_TO_BOOTLOADER), "r"(r0)
                         : "memory");
  } else {
    ensure_compatible_settings();
    _reboot_to_bootloader(boot_command);
  }
}

void svc_reboot(void) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    __asm__ __volatile__("svc %0" ::"i"(SVC_REBOOT) : "memory");
  } else {
    NVIC_SystemReset();
  }
}

void SVC_C_Handler(uint32_t *stack) {
  uint8_t svc_number = ((uint8_t *)stack[6])[-2];
  switch (svc_number) {
    case SVC_ENABLE_IRQ:
      HAL_NVIC_EnableIRQ(stack[0]);
      break;
    case SVC_DISABLE_IRQ:
      HAL_NVIC_DisableIRQ(stack[0]);
      break;
    case SVC_SET_PRIORITY:
      NVIC_SetPriority(stack[0], stack[1]);
      break;
#ifdef SYSTEM_VIEW
    case SVC_GET_DWT_CYCCNT:
      cyccnt_cycles = *DWT_CYCCNT_ADDR;
      break;
#endif
    case SVC_SHUTDOWN:
      shutdown_privileged();
      for (;;)
        ;
      break;
    case SVC_REBOOT_TO_BOOTLOADER:
      ensure_compatible_settings();

      __asm__ volatile("msr control, %0" ::"r"(0x0));
      __asm__ volatile("isb");

      // The input stack[0] argument comes from R0 saved when SVC was called
      // from svc_reboot_to_bootloader. The __asm__ directive expects address as
      // argument, hence the & in front of it, otherwise it would try
      // to dereference the value and fault
      __asm__ volatile(
          "mov r0, %[boot_command]" ::[boot_command] "r"(&stack[0]));

      // See stack layout in
      // https://developer.arm.com/documentation/ka004005/latest We are changing
      // return address in PC to land into reboot to avoid any bug with ROP and
      // raising privileges.
      stack[6] = (uintptr_t)_reboot_to_bootloader;
      return;
    case SVC_GET_SYSTICK_VAL:
      systick_val_copy = SysTick->VAL;
      break;
    case SVC_REBOOT:
      NVIC_SystemReset();
      break;
    default:
      stack[0] = 0xffffffff;
      break;
  }
}

__attribute__((naked)) void SVC_Handler(void) {
  __asm volatile(
      " tst lr, #4    \n"    // Test Bit 3 to see which stack pointer we should
                             // use.
      " ite eq        \n"    // Tell the assembler that the nest 2 instructions
                             // are if-then-else
      " mrseq r0, msp \n"    // Make R0 point to main stack pointer
      " mrsne r0, psp \n"    // Make R0 point to process stack pointer
      " b SVC_C_Handler \n"  // Off to C land
  );
}

#endif  // ARM_USER_MODE
