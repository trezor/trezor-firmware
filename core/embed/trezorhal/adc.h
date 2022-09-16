
#include "common.h"


void adc_init(void);

size_t adc_get_vrefint(char * buffer, size_t buffer_len);

size_t adc_get_vbat(char * buffer, size_t buffer_len);

size_t adc_get_temp(char * buffer, size_t buffer_len);

float adc_get_last(int idx);
