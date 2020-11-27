
#ifndef CORE_SYSTEMVIEW_H
#define CORE_SYSTEMVIEW_H

#ifdef SYSTEM_VIEW

#include "SEGGER_SYSVIEW.h"

void enable_systemview();

#else
#define SEGGER_SYSVIEW_RecordEnterISR() do {} while(0)
#define SEGGER_SYSVIEW_RecordExitISR() do {} while(0)
#endif

#endif //CORE_SYSTEMVIEW_H
