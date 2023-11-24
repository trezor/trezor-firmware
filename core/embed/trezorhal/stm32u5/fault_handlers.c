#include "common.h"

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }

void MemManage_Handler_MM(void) { error_shutdown("INTERNAL ERROR", "(MM)"); }

void MemManage_Handler_SO(void) { error_shutdown("INTERNAL ERROR", "(SO)"); }

void BusFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(BF)"); }

void UsageFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(UF)"); }

void SecureFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(SF)"); }

void GTZC_IRQHandler(void) { error_shutdown("INTERNAL ERROR", "(IA)"); }

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIFR & RCC_CIFR_CSSF) != 0) {
    error_shutdown("INTERNAL ERROR", "(CS)");
  }
}
