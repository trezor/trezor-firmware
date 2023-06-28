#include "common.h"

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }

void MemManage_Handler(void) { error_shutdown("INTERNAL ERROR", "(MM)"); }

void MemManage_Handler_SO(void) { error_shutdown("INTERNAL ERROR", "(SO)"); }

void BusFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(BF)"); }

void UsageFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(UF)"); }

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("INTERNAL ERROR", "(CS)");
  }
}
