#include <trezor_rtl.h>


#include <sys/systick.h>

typedef struct {
  uint64_t start;
  uint64_t end;

  uint64_t num_samples;
  uint64_t total;
  uint64_t average;

  uint64_t last;


  }profiler_t;

  volatile profiler_t g_profiler;

void profiler_init(void){

  memset((uint8_t*)&g_profiler, 0, sizeof(g_profiler));

  }

void profiler_start(void){

        g_profiler.start = systick_us();

  }
void profiler_end(void){

        g_profiler.end = systick_us();
        g_profiler.num_samples++;
        g_profiler.last = g_profiler.end - g_profiler.start;
        g_profiler.total += g_profiler.last;
        g_profiler.average = g_profiler.total / g_profiler.num_samples;

  }
