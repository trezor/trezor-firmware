#include STM32_HAL_H

#include <model.h>

#include "../mpu.h"
#include "common.h"
#include "supervise.h"

#ifdef ARM_USER_MODE

// Saves extra parameters for the bootloader
static void _copy_boot_args(const void *args, size_t args_size) {
  // symbols imported from the linker script
  extern uint8_t boot_args_start;
  extern uint8_t boot_args_end;

  uint8_t *p = &boot_args_start;

  if (args != NULL && args_size > 0) {
    size_t max_size = &boot_args_end - &boot_args_start;
    size_t copy_size = MIN(args_size, max_size);
    memcpy(p, args, copy_size);
    p += args_size;
  }

  if (p < &boot_args_end) {
    memset(p, 0, &boot_args_end - p);
  }
}

__attribute__((noreturn)) static void _reboot_to_bootloader(
    boot_command_t boot_command) {
  mpu_config_bootloader();
  jump_to_with_flag(BOOTLOADER_START + IMAGE_HEADER_SIZE, boot_command);
  for (;;)
    ;
}

void svc_reboot_to_bootloader(boot_command_t boot_command, const void *args,
                              size_t args_size) {
  _copy_boot_args(args, args_size);
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register uint32_t r0 __asm__("r0") = boot_command;
    __asm__ __volatile__("svc %0" ::"i"(SVC_REBOOT_TO_BOOTLOADER), "r"(r0)
                         : "memory");
  } else {
    ensure_compatible_settings();
    _reboot_to_bootloader(boot_command);
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

      __asm__ volatile(
          "mov r0, %[boot_command]" ::[boot_command] "r"(stack[0]));

      // See stack layout in
      // https://developer.arm.com/documentation/ka004005/latest We are changing
      // return address in PC to land into reboot to avoid any bug with ROP and
      // raising privileges.
      stack[6] = (uintptr_t)_reboot_to_bootloader;
      return;
    case SVC_GET_SYSTICK_VAL:
      systick_val_copy = SysTick->VAL;
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
