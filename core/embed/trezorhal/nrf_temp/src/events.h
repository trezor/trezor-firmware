

#include <zephyr/kernel.h>

#define INT_COMM_EVENT_NUM 3

void events_poll(void);

void events_init(void);

struct k_poll_event * events_get(int idx);
