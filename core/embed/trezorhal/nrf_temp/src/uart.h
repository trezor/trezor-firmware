#ifndef UART_H
#define UART_H

#define UART_BUF_SIZE 247

typedef struct {
    void *fifo_reserved;
    uint8_t data[UART_BUF_SIZE];
    uint16_t len;
}uart_data_t;

int uart_init(void);

uart_data_t * uart_get_data_ext(void);
uart_data_t * uart_get_data_int(void);
//uart_data_t * uart_get_data_pb(void);
//void uart_data_pb_flush(void);


void uart_send(uart_data_t *data);
void uart_send_ext(uart_data_t *tx);

#endif
