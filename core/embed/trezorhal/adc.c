

#include STM32_HAL_H

#include "adc.h"
#include <string.h>
#include "common.h"
#include "mini_printf.h"


ADC_HandleTypeDef adc;

void adc_init(void){
  __HAL_RCC_ADC1_CLK_ENABLE();

  adc.Instance = ADC1;
  adc.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV8;
  adc.Init.ContinuousConvMode = DISABLE;
  adc.Init.DMAContinuousRequests = DISABLE;
  adc.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  adc.Init.DiscontinuousConvMode = DISABLE;
  adc.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  adc.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  adc.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  adc.Init.NbrOfConversion = 1;
  adc.Init.ScanConvMode = DISABLE;
  adc.Init.NbrOfDiscConversion = 1;
  adc.Init.Resolution = ADC_RESOLUTION_12B;
  HAL_ADC_Init(&adc);

}

volatile uint16_t adc_result = 0;

void adc_set_vrefint(){
  ADC_ChannelConfTypeDef channel;
  channel.Channel = ADC_CHANNEL_VREFINT;
  channel.Offset = 0;
  channel.Rank = 1;
  channel.SamplingTime = ADC_SAMPLETIME_480CYCLES;
  HAL_ADC_ConfigChannel(&adc, &channel);

  ADC->CCR &= ~ADC_CCR_VBATE;
}

void adc_set_vbat(){
  ADC_ChannelConfTypeDef channel;
  channel.Channel = ADC_CHANNEL_VBAT;
  channel.Offset = 0;
  channel.Rank = 1;
  channel.SamplingTime = ADC_SAMPLETIME_480CYCLES;
  HAL_ADC_ConfigChannel(&adc, &channel);
}

void adc_set_temp(){
  ADC->CCR &= (~ADC_CCR_VBATE);
  ADC_ChannelConfTypeDef channel;
  channel.Channel = ADC_CHANNEL_TEMPSENSOR;
  channel.Offset = 0;
  channel.Rank = 1;
  channel.SamplingTime = ADC_SAMPLETIME_480CYCLES;
  HAL_ADC_ConfigChannel(&adc, &channel);
}

float adc_read(){

  HAL_ADC_Start(&adc);

  HAL_ADC_PollForConversion(&adc, 10);

  adc_result = HAL_ADC_GetValue(&adc);

  double res_f = ((double)adc_result / (double)4096) * (double)3.3;

  return res_f;
}


void adc_format(float val, char * buffer, size_t buffer_len, const char * name, const char * unit) {

  memset(buffer, 0, buffer_len);
  uint16_t p = (uint16_t)val;
  uint16_t d1 = ((uint16_t)(val * 10)) - (p * 10);
  uint16_t d2 = ((uint16_t)(val * 100)) - d1 * 10 - p * 100;
  uint16_t d3 = ((uint16_t)(val * 1000)) - d2 * 10 - d1 * 100 - p * 1000;

  mini_snprintf(buffer, buffer_len, "%s: %d.%d%d%d %s", name, p, d1, d2, d3, unit);

}
size_t adc_get_vrefint(char * buffer, size_t buffer_len){
  adc_set_vrefint();
  float val = adc_read();

  adc_format(val, buffer, buffer_len, "VrefInt", "V");

  return strlen(buffer);


}

size_t adc_get_vbat(char * buffer, size_t buffer_len){
  adc_set_vbat();
  float val = adc_read() * 4.0;

  adc_format(val, buffer, buffer_len, "Vbat", "V");

  return strlen(buffer);
}

size_t adc_get_temp(char * buffer, size_t buffer_len){
  adc_set_temp();
  float val = ((adc_read() - 0.76) / 0.0025) + 25;

  adc_format(val, buffer, buffer_len, "Temp", "°C");

  return strlen(buffer);
}
