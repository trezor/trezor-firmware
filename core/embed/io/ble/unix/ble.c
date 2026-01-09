/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <trezor_rtl.h>

#include <io/ble.h>
#include <io/unix/sock.h>
#include <sys/logging.h>
#include <sys/sysevent_source.h>

#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

LOG_DECLARE(ble_driver)

static const uint16_t DATA_PORT_OFFSET = 4;  // see usb_config.c
static const uint16_t EVENT_PORT_OFFSET = 5;

typedef struct {
  ble_mode_t mode_current;
  bool initialized;
  bool comm_running;
  bool enabled;
  bool pairing_requested;
  uint8_t adv_name[BLE_ADV_NAME_LEN];
  bool connected;
  bt_le_addr_t connected_addr;
  bt_le_addr_t bonds[BLE_MAX_BONDS];
  size_t bonds_len;
  emu_sock_t data_sock;
  emu_sock_t event_sock;
} ble_driver_t;

typedef struct {
  uint8_t cmd;
  uint8_t mode;
  uint8_t connected;
  uint8_t adv_name[BLE_ADV_NAME_LEN];
  uint8_t bonds_len;
  uint8_t bonds[6 * BLE_MAX_BONDS];
} emu_cmd_t;

static ble_driver_t g_ble_driver = {0};

static const syshandle_vmt_t ble_handle_vmt;
static const syshandle_vmt_t ble_iface_handle_vmt;

static bool bonds_lookup(const ble_driver_t *drv, const bt_le_addr_t *addr,
                         size_t *out_index) {
  for (size_t i = 0; i < drv->bonds_len; i++) {
    if (0 == memcmp(&addr->addr, &drv->bonds[i].addr, sizeof(addr->addr))) {
      if (out_index) {
        *out_index = i;
      }
      return true;
    }
  }
  return false;
}

static bool bonds_add(ble_driver_t *drv, const bt_le_addr_t *addr) {
  if (bonds_lookup(drv, addr, NULL)) {
    return true;
  }
  size_t len = drv->bonds_len;
  if (len >= BLE_MAX_BONDS) {
    return false;
  }
  drv->bonds[len] = *addr;
  drv->bonds_len++;
  return true;
}

static void bonds_remove(ble_driver_t *drv, const bt_le_addr_t *addr) {
  size_t i;
  bool found = bonds_lookup(drv, addr, &i);
  if (!found) {
    return;
  }
  size_t last = drv->bonds_len - 1;
  if (i != last) {
    drv->bonds[i] = drv->bonds[last];
  }
  drv->bonds_len--;
}

static bool is_enabled(const ble_driver_t *drv) {
  return (drv->initialized && drv->enabled && drv->comm_running);
}

bool ble_init(void) {
  ble_driver_t *drv = &g_ble_driver;
  memset(drv, 0, sizeof(*drv));
  sock_init(&drv->data_sock);
  sock_init(&drv->event_sock);
  if (!syshandle_register(SYSHANDLE_BLE, &ble_handle_vmt, drv)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_BLE_IFACE_0, &ble_iface_handle_vmt, drv)) {
    goto cleanup;
  }

  const char *ip = getenv("TREZOR_UDP_IP");
  const char *port_base_str = getenv("TREZOR_UDP_PORT");
  uint16_t port_base = port_base_str ? atoi(port_base_str) : 21324;

  sock_start(&drv->data_sock, ip, port_base + DATA_PORT_OFFSET);
  sock_start(&drv->event_sock, ip, port_base + EVENT_PORT_OFFSET);

  drv->initialized = true;
  drv->enabled = true;
  return true;

cleanup:
  memset(drv, 0, sizeof(ble_driver_t));
  LOG_ERR("init failed");
  return false;
}

void ble_deinit(void) {
  ble_driver_t *drv = &g_ble_driver;

  memset(drv, 0, sizeof(ble_driver_t));

  sock_stop(&drv->data_sock);
  sock_stop(&drv->event_sock);

  syshandle_unregister(SYSHANDLE_BLE_IFACE_0);
  syshandle_unregister(SYSHANDLE_BLE);
}

void ble_start(void) {
  ble_driver_t *drv = &g_ble_driver;
  drv->comm_running = true;
}

void ble_stop(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  drv->comm_running = false;
}

static bool send_to_emu(char cmdtype) {
  ble_driver_t *drv = &g_ble_driver;
  emu_cmd_t command = {
      .cmd = cmdtype,
      .mode = drv->mode_current,
      .connected = drv->connected,
      .bonds_len = drv->bonds_len,
  };
  for (size_t i = 0; i < drv->bonds_len; i++) {
    memcpy(&command.bonds[6 * i], drv->bonds[i].addr, 6);
  }
  memcpy(&command.adv_name, drv->adv_name, BLE_ADV_NAME_LEN);

  ssize_t r = sock_sendto(&drv->event_sock, &command, sizeof(command));
  if (r != sizeof(command)) {
    LOG_ERR("failed to write command %c: %zd", cmdtype, r);
  }

  return true;
}

bool ble_switch_off(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  drv->mode_current = BLE_MODE_OFF;
  drv->connected = false;
  return send_to_emu(' ');
}

bool ble_switch_on(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  if (drv->connected) {
    drv->mode_current = BLE_MODE_KEEP_CONNECTION;
  } else {
    drv->mode_current = BLE_MODE_CONNECTABLE;
  }
  return send_to_emu(' ');
}

bool ble_enter_pairing_mode(const uint8_t *name, size_t name_len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  drv->mode_current = BLE_MODE_PAIRING;
  memcpy(drv->adv_name, name, MIN(name_len, BLE_ADV_NAME_LEN));
  return send_to_emu('p');
}

bool ble_disconnect(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  drv->connected = false;
  drv->mode_current = BLE_MODE_CONNECTABLE;  // more complicated in real driver
  return send_to_emu('d');
}

bool ble_erase_bonds(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  LOG_INF("erase bonds");
  memset(drv->bonds, 0, sizeof(drv->bonds));
  drv->bonds_len = 0;
  drv->connected = false;
  drv->mode_current = BLE_MODE_OFF;
  return send_to_emu('d');
}

bool ble_allow_pairing(const uint8_t *pairing_code) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }
  drv->pairing_requested = false;
  drv->connected = true;
  // NOTE: pairing code ignored
  return send_to_emu('a');
}

bool ble_reject_pairing(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  drv->pairing_requested = false;
  drv->connected = false;
  drv->mode_current = BLE_MODE_CONNECTABLE;
  return send_to_emu('r');
}

bool ble_keep_connection(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }
  drv->mode_current = BLE_MODE_KEEP_CONNECTION;
  return send_to_emu(' ');
}

bool ble_get_event(ble_event_t *event) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }

  uint8_t buf[sizeof(ble_event_t)] = {0};
  ssize_t r = sock_recvfrom(&drv->event_sock, buf, sizeof(buf));
  if (r <= 0) {
    return false;
  } else if (r > sizeof(ble_event_t)) {
    LOG_ERR("event packet too long: %zd", r);
    return false;
  }

  const ble_event_t *e = (ble_event_t *)buf;

  switch (e->type) {
    case BLE_CONNECTED:
      drv->connected = true;
      if (drv->mode_current != BLE_MODE_PAIRING) {
        drv->mode_current = BLE_MODE_KEEP_CONNECTION;
      }
      if (e->data_len == 6) {
        memcpy(&drv->connected_addr.addr, e->data, 6);
      } else {
        memset(&drv->connected_addr.addr, '\xff', 6);
      }
      drv->pairing_requested = false;
      send_to_emu(' ');
      break;
    case BLE_DISCONNECTED:
      drv->connected = false;
      drv->mode_current = BLE_MODE_CONNECTABLE;
      drv->pairing_requested = false;
      send_to_emu(' ');
      break;
    case BLE_PAIRING_REQUEST:
      drv->pairing_requested = true;
      break;
    case BLE_PAIRING_CANCELLED:
      drv->pairing_requested = false;
      drv->mode_current = BLE_MODE_CONNECTABLE;
      break;
    case BLE_PAIRING_COMPLETED:
      drv->pairing_requested = false;
      drv->mode_current = BLE_MODE_KEEP_CONNECTION;
      bonds_add(drv, &drv->connected_addr);
      send_to_emu(' ');
      break;
    case BLE_CONNECTION_CHANGED:
      LOG_WARN("CONNECTION_CHANGED not implemented");
      break;
    case BLE_EMULATOR_PING:
      send_to_emu(' ');
      return ble_get_event(event);  // do not forward to app
      break;
    default:
      LOG_WARN("unknown event type");
      break;
  }

  memcpy(event, buf, sizeof(ble_event_t));
  return true;
}

void ble_get_state(ble_state_t *state) {
  const ble_driver_t *drv = &g_ble_driver;
  memset(state, 0, sizeof(ble_state_t));

  if (!drv->initialized) {
    return;
  }

  state->connected = drv->connected;
  if (drv->connected) {
    state->connected_addr = drv->connected_addr;
  }
  state->peer_count = drv->bonds_len;
  state->pairing = drv->mode_current == BLE_MODE_PAIRING;
  state->connectable = drv->mode_current == BLE_MODE_CONNECTABLE;
  state->pairing_requested = drv->pairing_requested;

  state->state_known = true;
}

void ble_set_name(const uint8_t *name, size_t len) {
  ble_driver_t *drv = &g_ble_driver;

  memcpy(drv->adv_name, name, MIN(len, BLE_ADV_NAME_LEN));
}

void ble_get_advertising_name(char *name, size_t max_len) {
  ble_driver_t *drv = &g_ble_driver;

  if (max_len < sizeof(drv->adv_name)) {
    memset(name, 0, max_len);
    return;
  }

  if (!drv->initialized) {
    memset(name, 0, max_len);
    return;
  }

  memcpy(name, drv->adv_name, sizeof(drv->adv_name));
}

bool ble_can_write(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv) || !drv->connected) {
    return false;
  }

  return sock_can_send(&drv->data_sock);
}

bool ble_write(const uint8_t *data, uint16_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }

  if (!drv->connected) {
    LOG_ERR("ble_write while disconnected");
    return false;
  }

  ssize_t r = sock_sendto(&drv->data_sock, data, len);
  return r == len;
}

bool ble_can_read(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv) || !drv->connected) {
    return false;
  }

  return sock_can_recv(&drv->data_sock);
}

uint32_t ble_read(uint8_t *data, uint16_t max_len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return 0;
  }

  if (!drv->connected) {
    LOG_ERR("ble_read while disconnected");
    return false;
  }

  uint8_t buf[max_len] = {};
  ssize_t r = sock_recvfrom(&drv->data_sock, buf, sizeof(buf));
  if (r <= 0) {
    return 0;
  }

  memcpy(data, buf, r);
  return r;
}

bool ble_get_mac(bt_le_addr_t *addr) {
  ble_driver_t *drv = &g_ble_driver;

  if (drv->initialized) {
    memset(addr, 0, sizeof(*addr));
    return false;
  }

  LOG_WARN("ble_get_mac not implemented");
  for (size_t i = 0; i < sizeof(addr->addr); i++) {
    addr->addr[i] = i + 0xe1;
  }
  addr->type = 0x00;
  return true;
}

bool ble_wait_until_ready(void) { return true; }

uint8_t ble_get_bond_list(bt_le_addr_t *bonds, size_t count) {
  ble_driver_t *drv = &g_ble_driver;
  size_t copied = MIN(count, drv->bonds_len);
  memcpy(bonds, &drv->bonds, sizeof(bonds[0]) * copied);
  return copied;
}

void ble_set_high_speed(bool enable) {
  LOG_WARN("set_high_speed not implemented");
}

bool ble_unpair(const bt_le_addr_t *addr) {
  ble_driver_t *drv = &g_ble_driver;
  if (addr) {
    bonds_remove(drv, addr);
  } else if (drv->connected) {
    bonds_remove(drv, &drv->connected_addr);
  }
  send_to_emu(' ');
  return true;
}

void ble_notify(const uint8_t *data, size_t len) {
  LOG_WARN("ble_notify not implemented");
}

void ble_set_enabled(bool enabled) {
  ble_driver_t *drv = &g_ble_driver;
  if (drv->enabled && !enabled) {
    drv->mode_current = BLE_MODE_OFF;
    drv->connected = false;
    send_to_emu(' ');
  }
  drv->enabled = enabled;
}

bool ble_get_enabled(void) {
  ble_driver_t *drv = &g_ble_driver;
  return drv->enabled;
}

static void on_ble_poll(void *context, bool read_awaited, bool write_awaited) {
  ble_driver_t *drv = (ble_driver_t *)context;

  UNUSED(write_awaited);

  // Until we need to poll BLE events from multiple tasks,
  // the logic here can remain very simple. If this assumption
  // changes, the logic will need to be updated (e.g., task-local storage
  // with an independent queue for each task).

  if (read_awaited) {
    bool ready = false;

    // check if you can read from event socket

    if (is_enabled(drv)) {
      ready = sock_can_recv(&drv->event_sock);
    }

    syshandle_signal_read_ready(SYSHANDLE_BLE, &ready);
  }
}

static bool on_ble_check_read_ready(void *context, systask_id_t task_id,
                                    void *param) {
  UNUSED(context);
  UNUSED(task_id);

  bool ready = *(bool *)param;
  return ready;
}

static const syshandle_vmt_t ble_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_ble_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_ble_poll,
};

static void on_ble_iface_event_poll(void *context, bool read_awaited,
                                    bool write_awaited) {
  UNUSED(context);

  syshandle_t handle = SYSHANDLE_BLE_IFACE_0;

  // Only one task can read or write at a time. Therefore, we can
  // assume that only one task is waiting for events and keep the
  // logic simple.

  if (read_awaited && ble_can_read()) {
    syshandle_signal_read_ready(handle, NULL);
  }

  if (write_awaited && ble_can_write()) {
    syshandle_signal_write_ready(handle, NULL);
  }
}

static bool on_ble_iface_read_ready(void *context, systask_id_t task_id,
                                    void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);

  return true;
}

static bool on_ble_iface_check_write_ready(void *context, systask_id_t task_id,
                                           void *param) {
  UNUSED(context);
  UNUSED(task_id);
  UNUSED(param);

  return true;
}

static const syshandle_vmt_t ble_iface_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_ble_iface_read_ready,
    .check_write_ready = on_ble_iface_check_write_ready,
    .poll = on_ble_iface_event_poll,
};
