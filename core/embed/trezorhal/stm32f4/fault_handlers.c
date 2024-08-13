#include TREZOR_BOARD

#include "common.h"
#include "mpu.h"

#ifdef KERNEL_MODE

void fault_handlers_init(void) {
  // Enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
}

void HardFault_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(HF)");
}

void MemManage_Handler_MM(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(MM)");
}

void MemManage_Handler_SO(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(SO)");
}

void BusFault_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(BF)");
}

void UsageFault_Handler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
  error_shutdown("(UF)");
}

void NMI_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("(CS)");
  }
  mpu_restore(mpu_mode);
}

// from util.s
extern void shutdown_privileged(void);

void PVD_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
#ifdef BACKLIGHT_PWM_TIM
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = 0;  // turn off display backlight
#endif
  shutdown_privileged();
}

#endif  // KERNEL_MODE
