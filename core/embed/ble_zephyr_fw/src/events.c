


#include <zephyr/kernel.h>

#define K_POOL_EVENTS_CNT (4)


static struct k_poll_event events[K_POOL_EVENTS_CNT];

void events_poll(void){
  k_poll(events, ARRAY_SIZE(events), K_FOREVER);
}

void events_init(void){

}

struct k_poll_event * events_get(int idx){
  return &events[idx];
}
