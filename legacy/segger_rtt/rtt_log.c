#include "rtt_log.h"

void rtt_log_init(void) {
  if (DEBUG_RTT) SEGGER_RTT_Init();
}
