

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>

void auth_oob_data_request(struct bt_conn *conn,
                           struct bt_conn_oob_info *info);


void oob_init(void);

void oob_signal(void);

void oob_process(void);

void oob_fetch_addr(void);
