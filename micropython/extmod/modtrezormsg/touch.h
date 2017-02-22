extern I2C_HandleTypeDef I2CHandle1;
extern void i2c_init(I2C_HandleTypeDef *i2c);
extern HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint8_t *pData, uint16_t Size, uint32_t Timeout);

void touch_init(void)
{
    I2C_InitTypeDef *init = &(I2CHandle1.Init);
    init->OwnAddress1 = 0xFE; // master
    init->ClockSpeed = 400000;
    init->DutyCycle = I2C_DUTYCYCLE_16_9;
    init->AddressingMode  = I2C_ADDRESSINGMODE_7BIT;
    init->DualAddressMode = I2C_DUALADDRESS_DISABLED;
    init->GeneralCallMode = I2C_GENERALCALL_DISABLED;
    init->NoStretchMode   = I2C_NOSTRETCH_DISABLED;
    init->OwnAddress2     = 0;
    i2c_init(&I2CHandle1);
}

uint32_t touch_read(void)
{
    static uint8_t data[16], old_data[16];
    if (HAL_OK != HAL_I2C_Master_Receive(&I2CHandle1, 56 << 1, data, 16, 1)) {
        return 0; // read failure
    }
    if (0 == memcmp(data, old_data, 16)) {
        return 0; // no new event
    }
    uint32_t r = 0;
    if (old_data[2] == 0 && data[2] == 1) {
        r = 0x00010000 + (data[4] << 8) + data[6]; // touch start
    } else
    if (old_data[2] == 1 && data[2] == 1) {
        r = 0x00020000 + (data[4] << 8) + data[6]; // touch move
    }
    if (old_data[2] == 1 && data[2] == 0) {
        r = 0x00040000 + (data[4] << 8) + data[6]; // touch end
    }
    memcpy(old_data, data, 16);
    return r;
}
