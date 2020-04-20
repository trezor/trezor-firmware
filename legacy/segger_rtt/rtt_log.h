#ifndef __RTT_LOG_H__
#define __RTT_LOG_H__

#include "SEGGER_RTT.h"
#include "SEGGER_RTT_Conf.h"

#ifndef RTT_DEFAULT_LOG_LEVEL
#define RTT_DEFAULT_LOG_LEVEL RTT_LOG_DEBUG
#endif

#define RAW_ONLY 0

typedef enum _rtt_log_level {
  RTT_LOG_ERROR = 1,
  RTT_LOG_WARN = 2,
  RTT_LOG_INFO = 3,
  RTT_LOG_DEBUG = 4,
} rtt_log_level;

void rtt_log_init(void);

#define rtt_log_print(sFormat, ...) \
  if (DEBUG_RTT) SEGGER_RTT_printf(0, sFormat, ##__VA_ARGS__)

#if RAW_ONLY
#define rtt_log_fomate(log_level, sFormat, ...)              \
  {                                                          \
    if (DEBUG_RTT && (log_level <= RTT_DEFAULT_LOG_LEVEL)) { \
      switch (log_level) {                                   \
        case RTT_LOG_DEBUG:                                  \
          SEGGER_RTT_printf(0, "DEBUG ");                    \
          break;                                             \
        case RTT_LOG_WARN:                                   \
          SEGGER_RTT_printf(0, "WARN ");                     \
          break;                                             \
        case RTT_LOG_INFO:                                   \
          SEGGER_RTT_printf(0, "INFO ");                     \
          break;                                             \
        case RTT_LOG_ERROR:                                  \
          SEGGER_RTT_printf(0, "ERROR ");                    \
          break;                                             \
        default:                                             \
          break;                                             \
      }                                                      \
      SEGGER_RTT_printf(0, sFormat, ##__VA_ARGS__);          \
    }                                                        \
  }

#define rtt_log_debug(sFormat, ...) \
  rtt_log_fomate(RTT_LOG_DEBUG, sFormat, ##__VA_ARGS__)
#define rtt_log_warn(sFormat, ...) \
  rtt_log_fomate(RTT_LOG_WARN, sFormat, ##__VA_ARGS__)
#define rtt_log_info(sFormat, ...) \
  rtt_log_fomate(RTT_LOG_INFO, sFormat, ##__VA_ARGS__)
#define rtt_log_error(sFormat, ...) \
  rtt_log_fomate(RTT_LOG_ERROR, sFormat, ##__VA_ARGS__)
#endif

#endif
