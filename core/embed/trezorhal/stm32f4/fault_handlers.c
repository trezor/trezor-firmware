#include TREZOR_BOARD
#include "common.h"

void fault_handlers_init(void) {
  // Enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
}

void HardFault_Handler(void) { error_shutdown("(HF)"); }

void MemManage_Handler_MM(void) { error_shutdown("(MM)"); }

void MemManage_Handler_SO(void) { error_shutdown("(SO)"); }

void BusFault_Handler(void) { error_shutdown("(BF)"); }

void UsageFault_Handler(void) { error_shutdown("(UF)"); }

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("(CS)");
  }
}

// from util.s
extern void shutdown_privileged(void);

void PVD_IRQHandler(void) {
#ifdef BACKLIGHT_PWM_TIM
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = 0;  // turn off display backlight
#endif
  shutdown_privileged();
}
