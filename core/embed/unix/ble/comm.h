
void ble_comm_init(void);

void ble_comm_send(uint8_t *data, uint32_t len);

uint32_t ble_comm_receive(uint8_t *data, uint32_t len);
