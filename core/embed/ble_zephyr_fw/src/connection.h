

#include <stdint.h>
#include <stdbool.h>

#include <zephyr/types.h>
#include <zephyr/kernel.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>

void connected(struct bt_conn *conn, uint8_t err);

void disconnect(void);

void disconnected(struct bt_conn *conn, uint8_t reason);

bool is_connected(void);

void num_comp_reply(bool accept);
void auth_passkey_display(struct bt_conn *conn, unsigned int passkey);
void auth_passkey_confirm(struct bt_conn *conn, unsigned int passkey);
void auth_cancel(struct bt_conn *conn);
void pairing_complete(struct bt_conn *conn, bool bonded);
void pairing_failed(struct bt_conn *conn, enum bt_security_err reason);

void num_comp_reply(bool accept);
struct bt_conn * conn_get_current(void);
