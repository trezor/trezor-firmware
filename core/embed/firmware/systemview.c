#ifdef SYSTEM_VIEW

#include "systemview.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "irq.h"
#include "mpconfigport.h"
#include "supervise.h"

#include "SEGGER_SYSVIEW.h"
#include "SEGGER_SYSVIEW_Conf.h"

#define SYSTICK ((SYSTICK_REGS *)0xE000E010)
#define SCS ((SCS_REGS *)0xE000ED00)

// for storing DWT CYCCNT from SVC call
volatile uint32_t cyccnt_cycles;

typedef struct {
  volatile unsigned int CSR;
  volatile unsigned int RVR;
  volatile unsigned int CVR;
  volatile unsigned int CALIB;
} SYSTICK_REGS;

typedef struct {
  volatile unsigned int CPUID;  // CPUID Base Register
  volatile unsigned int ICSR;   // Interrupt Control and State Register
  volatile unsigned int VTOR;   // Vector Table Offset Register
  volatile unsigned int
      AIRCR;  // Application Interrupt and Reset Control Register
  volatile unsigned int SCR;    // System Control Register
  volatile unsigned int CCR;    // Configuration and Control Register
  volatile unsigned int SHPR1;  // System Handler Priority Register 1
  volatile unsigned int SHPR2;  // System Handler Priority Register 2
  volatile unsigned int SHPR3;  // System Handler Priority Register 3
  volatile unsigned int SHCSR;  // System Handler Control and State Register
  volatile unsigned int CFSR;   // Configurable Fault Status Register
  volatile unsigned int HFSR;   // HardFault Status Register
  volatile unsigned int DFSR;   // Debug Fault Status Register
  volatile unsigned int MMFAR;  // MemManage Fault Address Register
  volatile unsigned int BFAR;   // BusFault Address Register
  volatile unsigned int AFSR;   // Auxiliary Fault Status Register
  volatile unsigned int aDummy0[4];  // 0x40-0x4C Reserved
  volatile unsigned int aDummy1[4];  // 0x50-0x5C Reserved
  volatile unsigned int aDummy2[4];  // 0x60-0x6C Reserved
  volatile unsigned int aDummy3[4];  // 0x70-0x7C Reserved
  volatile unsigned int aDummy4[2];  // 0x80-0x87 - - - Reserved.
  volatile unsigned int CPACR;       // Coprocessor Access Control Register
} SCS_REGS;

extern uint32_t SystemCoreClock;

uint32_t svc_get_dwt_cyccnt() {
  if (is_mode_unprivileged()) {
    __asm__ __volatile__("svc %0" ::"i"(SVC_GET_DWT_CYCCNT));
  } else {
    cyccnt_cycles = *DWT_CYCCNT_ADDR;
  }
  return cyccnt_cycles;
}

U32 SEGGER_SYSVIEW_X_GetInterruptId() {
  return ((*(U32 *)(0xE000ED04)) & 0x1FF);
}

void enable_systemview() {
  SEGGER_SYSVIEW_Conf();
  SEGGER_SYSVIEW_Start();

  U32 v;
  //
  // Configure SysTick and debug monitor interrupt priorities
  // Low value means high priority
  // A maximum of 8 priority bits and a minimum of 3 bits is implemented per
  // interrupt. How many bits are implemented depends on the actual CPU being
  // used If less than 8 bits are supported, the lower bits of the priority byte
  // are RAZ. In order to make sure that priority of monitor and SysTick always
  // differ, please make sure that the difference is visible in the highest 3
  // bits
  v = SCS->SHPR3;
  v |= (0xFFuL << 24);  // Lowest prio for SysTick so SystemView does not get
                        // interrupted by Systick
  SCS->SHPR3 = v;
  //
  // Configure SysTick interrupt
  // SysTick is running at CPU speed
  // Configure SysTick to fire every ms
  //
  SYSTICK->RVR = (SystemCoreClock / 1000) - 1;  // set reload
  SYSTICK->CVR = 0x00;                          // set counter
  SYSTICK->CSR = 0x07;                          // enable systick
}

#ifdef SYSTEMVIEW_DEST_RTT
size_t _write(int file, const void *ptr, size_t len);
#endif

size_t segger_print(const char *str, size_t len) {
#ifdef SYSTEMVIEW_DEST_SYSTEMVIEW
  static char str_copy[1024];
  size_t copylen = len > 1023 ? 1023 : len;
  memcpy(str_copy, str, copylen);
  str_copy[copylen] = 0;
  SEGGER_SYSVIEW_Print(str_copy);
  return len;
#endif
#ifdef SYSTEMVIEW_DEST_RTT
  _write(0, str, len);
  return len;
#endif
}
#endif
