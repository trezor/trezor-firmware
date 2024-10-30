#ifndef INT_COMM__
#define INT_COMM__

#include <stdint.h>

void process_command(uint8_t *data, uint16_t len);

void send_status_event(void);

void send_pairing_request_event(uint8_t * data, uint16_t len);

void int_comm_start(void);

void int_comm_thread(void);

void send_packet(uint8_t message_type, const uint8_t *tx_data, uint16_t len);

void pb_msg_ack(void);

#endif
