#include "common.h"
#include "mpu.h"

#ifdef KERNEL_MODE

void fault_handlers_init(void) {
  // Enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
}

void HardFault_Handler(void) {
  // A HardFault may also be caused by exception escalation.
  // To ensure we have enough space to handle the exception,
  // we set the stack pointer to the end of the stack.
  extern uint8_t _estack;  // linker script symbol
  // Fix stack pointer
  __set_MSP((uint32_t)&_estack);

  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(HF)");
}

void MemManage_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(MM)");
}

void BusFault_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(BF)");
}

void UsageFault_Handler(void) {
  if (SCB->CFSR & SCB_CFSR_STKOF_Msk) {
    // Stack overflow
    extern uint8_t _estack;  // linker script symbol
    // Fix stack pointer
    __set_MSP((uint32_t)&_estack);
    mpu_reconfig(MPU_MODE_DEFAULT);
    error_shutdown("(SO)");
  } else {
    // Other error
    mpu_reconfig(MPU_MODE_DEFAULT);
    error_shutdown("(UF)");
  }
}

void SecureFault_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(SF)");
}

void GTZC_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(IA)");
}

void NMI_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  // Clock Security System triggered NMI
  if ((RCC->CIFR & RCC_CIFR_CSSF) != 0) {
    error_shutdown("(CS)");
  }
  mpu_restore(mpu_mode);
}

// from util.s
extern void shutdown_privileged(void);

void PVD_PVM_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  TIM1->CCR1 = 0;  // turn off display backlight
  shutdown_privileged();
}

#endif  // KERNEL_MODE
