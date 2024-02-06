
#define PB_BUF_SIZE 64

typedef enum {
    COMPARISON_REQUEST = 0,
    AUTH_KEY_REQUEST = 1,
    REPAIR_REQUEST = 2,
    PASSKEY_DISPLAY = 3,
}pb_comm_cmd_t;

void pb_comm_start(void);

void pb_comm_enqueue(pb_comm_cmd_t cmd, uint8_t *data, uint16_t len);

void send_error_response(void);
