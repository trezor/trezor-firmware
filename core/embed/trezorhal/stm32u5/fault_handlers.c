#include "common.h"

void fault_handlers_init(void) {
  // Enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }

void MemManage_Handler(void) { error_shutdown("INTERNAL ERROR", "(MM)"); }

void BusFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(BF)"); }

void UsageFault_Handler(void) {
  if (SCB->CFSR & SCB_CFSR_STKOF_Msk) {
    // Stack overflow
    extern uint8_t _estack;  // linker script symbol
    // Fix stack pointer
    __set_MSP((uint32_t)&_estack);
    error_shutdown("INTERNAL ERROR", "(SO)");
  } else {
    // Other error
    error_shutdown("INTERNAL ERROR", "(UF)");
  }
}

void SecureFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(SF)"); }

void GTZC_IRQHandler(void) { error_shutdown("INTERNAL ERROR", "(IA)"); }

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIFR & RCC_CIFR_CSSF) != 0) {
    error_shutdown("INTERNAL ERROR", "(CS)");
  }
}
