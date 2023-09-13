#include "haptic.h"

#include STM32_HAL_H

#include "i2c.h"
#include TREZOR_BOARD

#define I2C_ADDRESS (0x5A << 1)

#define DRV2625_REG_CHIPID 0x00
#define DRV2625_REG_STATUS 0x01
#define DRV2625_REG_MODE 0x07
#define DRV2625_REG_LRAERM 0x08

#define DRV2625_REG_LIBRARY 0x0D  ///< Waveform library selection register

#define DRV2625_REG_WAVESEQ1 0x0F  ///< Waveform sequence register 1
#define DRV2625_REG_WAVESEQ2 0x10  ///< Waveform sequence register 2
#define DRV2625_REG_WAVESEQ3 0x11  ///< Waveform sequence register 3
#define DRV2625_REG_WAVESEQ4 0x12  ///< Waveform sequence register 4
#define DRV2625_REG_WAVESEQ5 0x13  ///< Waveform sequence register 5
#define DRV2625_REG_WAVESEQ6 0x14  ///< Waveform sequence register 6
#define DRV2625_REG_WAVESEQ7 0x15  ///< Waveform sequence register 7
#define DRV2625_REG_WAVESEQ8 0x16  ///< Waveform sequence register 8

#define DRV2625_REG_GO 0x0C  ///< Go register

volatile uint8_t status;
volatile uint8_t chip_id;
uint8_t waveform = 1;

void set_reg(uint8_t addr, uint8_t value) {
  uint8_t data[] = {addr, value};
  i2c_transmit(HAPTIC_I2C_NUM, I2C_ADDRESS, data, sizeof(data), 1);
}

void read_reg(uint8_t addr, uint8_t *value) {
  i2c_transmit(0, I2C_ADDRESS, &addr, 1, 1);
  i2c_receive(0, I2C_ADDRESS, value, 1, 1);
}

void haptic_init(void) {
  HAL_Delay(1);
  set_reg(DRV2625_REG_MODE, 0x03);

  HAL_Delay(1);
  set_reg(DRV2625_REG_LRAERM, 0x08);

  HAL_Delay(1);
  set_reg(DRV2625_REG_GO, 0x01);

  HAL_Delay(1000);
  HAL_Delay(1000);

  // wafeform playback select
  set_reg(DRV2625_REG_MODE, 0x41);

  HAL_Delay(1);

  // select library
  // set_reg(DRV2625_REG_LIBRARY, 0x40);//erm
  set_reg(DRV2625_REG_LIBRARY, 0x00);  // lra

  HAL_Delay(1);
  set_reg(DRV2625_REG_WAVESEQ1, 1);
  HAL_Delay(1);
  set_reg(DRV2625_REG_WAVESEQ2, 0);

  HAL_Delay(1);
  set_reg(DRV2625_REG_GO, 0x01);

  read_reg(DRV2625_REG_STATUS, (uint8_t *)&status);
  read_reg(DRV2625_REG_CHIPID, (uint8_t *)&chip_id);
}

void haptic_play(uint16_t effect) {
  if (effect > 123) {
    return;
  }
  if (effect == 0) {
    effect = 1;
  }
  set_reg(DRV2625_REG_WAVESEQ1, effect);
  set_reg(DRV2625_REG_GO, 0x01);
}
