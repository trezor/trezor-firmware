
#ifndef CORE_SYSTEMVIEW_H
#define CORE_SYSTEMVIEW_H

#ifdef SYSTEM_VIEW

#include <stdint.h>
#include "SEGGER_SYSVIEW.h"

#define DWT_CYCCNT_ADDR ((uint32_t*)(0xE0001004));
#define SVC_GET_DWT_CYCCNT 3

extern volatile uint32_t cyccnt_cycles;

void enable_systemview();
uint32_t svc_get_dwt_cyccnt();

#else
#define SEGGER_SYSVIEW_RecordEnterISR()
#define SEGGER_SYSVIEW_RecordExitISR()
#endif

#endif  // CORE_SYSTEMVIEW_H
