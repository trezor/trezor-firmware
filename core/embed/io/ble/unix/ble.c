#include <io/ble.h>
#include <sys/sysevent_source.h>
#include <trezor_rtl.h>

#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static const uint16_t DATA_PORT_OFFSET = 4;  // see usb_config.c
static const uint16_t EVENT_PORT_OFFSET = 5;

typedef struct {
  ble_mode_t mode_current;
  bool initialized;
  bool enabled;
  bool pairing_requested;
  uint8_t adv_name[BLE_ADV_NAME_LEN];
  bool connected;
  bt_le_addr_t connected_addr;
  bt_le_addr_t bonds[BLE_MAX_BONDS];
  size_t bonds_len;

  uint16_t data_port;
  int data_sock;
  struct sockaddr_in data_si_me, data_si_other;
  socklen_t data_slen;

  uint16_t event_port;
  int event_sock;
  struct sockaddr_in event_si_me, event_si_other;
  socklen_t event_slen;
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
  return (drv->initialized && drv->enabled);
}

bool ble_init(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!syshandle_register(SYSHANDLE_BLE, &ble_handle_vmt, drv)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_BLE_IFACE_0, &ble_iface_handle_vmt, drv)) {
    goto cleanup;
  }
  return true;

cleanup:
  memset(drv, 0, sizeof(ble_driver_t));
  printf("unix/ble: init failed\n");
  return false;
}

void ble_deinit(void) {
  syshandle_unregister(SYSHANDLE_BLE_IFACE_0);
  syshandle_unregister(SYSHANDLE_BLE);
}

void ble_start(void) {
  ble_driver_t *drv = &g_ble_driver;
  memset(drv, 0, sizeof(*drv));
  drv->data_sock = -1;
  drv->event_sock = -1;

  const char *ip = getenv("TREZOR_UDP_IP");
  const char *port_base_str = getenv("TREZOR_UDP_PORT");
  uint16_t port_base = port_base_str ? atoi(port_base_str) : 21324;

  drv->data_port = port_base + DATA_PORT_OFFSET;
  drv->event_port = port_base + EVENT_PORT_OFFSET;
  drv->data_sock = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, IPPROTO_UDP);
  drv->event_sock = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, IPPROTO_UDP);

  ensure(sectrue * (drv->data_sock >= 0), NULL);
  ensure(sectrue * (drv->event_sock >= 0), NULL);

  drv->data_si_me.sin_family = drv->event_si_me.sin_family = AF_INET;
  drv->data_si_me.sin_addr.s_addr = ip ? inet_addr(ip) : htonl(INADDR_LOOPBACK);
  drv->event_si_me.sin_addr.s_addr =
      ip ? inet_addr(ip) : htonl(INADDR_LOOPBACK);
  drv->data_si_me.sin_port = htons(drv->data_port);
  drv->event_si_me.sin_port = htons(drv->event_port);

  int ret = -1;
  ret = bind(drv->data_sock, (struct sockaddr *)&(drv->data_si_me),
             sizeof(struct sockaddr_in));
  ensure(sectrue * (ret == 0), NULL);
  ret = bind(drv->event_sock, (struct sockaddr *)&(drv->event_si_me),
             sizeof(struct sockaddr_in));
  ensure(sectrue * (ret == 0), NULL);

  drv->initialized = true;
}

void ble_stop(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return;
  }

  if (drv->data_sock >= 0) {
    close(drv->data_sock);
    drv->data_sock = -1;
  }
  if (drv->event_sock >= 0) {
    close(drv->event_sock);
    drv->event_sock = -1;
  }
  drv->initialized = false;
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

  ssize_t r = -2;
  if (drv->event_slen > 0) {
    r = sendto(drv->event_sock, &command, sizeof(command), MSG_DONTWAIT,
               (const struct sockaddr *)&(drv->event_si_other),
               drv->event_slen);
  }
  if (r != sizeof(command)) {
    printf("unix/ble: failed to write command %c: %d\n", cmdtype, (int)r);
  }

  return true;
}

bool ble_switch_off(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }
  drv->mode_current = BLE_MODE_OFF;
  drv->connected = false;
  return send_to_emu(' ');
}

bool ble_switch_on(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
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
  if (!is_enabled(drv)) {
    return false;
  }
  drv->connected = false;
  drv->mode_current = BLE_MODE_CONNECTABLE;  // more complicated in real driver
  return send_to_emu('d');
}

bool ble_erase_bonds(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }
  printf("unix/ble: erase bonds\n");
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
  if (!is_enabled(drv)) {
    return false;
  }
  drv->pairing_requested = false;
  drv->connected = false;
  drv->mode_current = BLE_MODE_CONNECTABLE;
  return send_to_emu('r');
}

bool ble_keep_connection(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }
  drv->mode_current = BLE_MODE_KEEP_CONNECTION;
  return send_to_emu(' ');
}

bool ble_get_event(ble_event_t *event) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }
  struct sockaddr_in si;
  socklen_t sl = sizeof(si);
  uint8_t buf[sizeof(ble_event_t)] = {0};
  ssize_t r = recvfrom(drv->event_sock, buf, sizeof(buf), MSG_DONTWAIT,
                       (struct sockaddr *)&si, &sl);
  if (r <= 0) {
    return false;
  } else if (r > sizeof(ble_event_t)) {
    printf("unix/ble: event packet too long: %zd\n", r);
    return false;
  }

  drv->event_si_other = si;
  drv->event_slen = sl;

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
      printf("unix/ble: CONNECTION_CHANGED not implemented\n");
      break;
    case BLE_EMULATOR_PING:
      send_to_emu(' ');
      return ble_get_event(event);  // do not forward to app
      break;
    default:
      printf("unix/ble: unknown event type\n");
      break;
  }

  memcpy(event, buf, sizeof(ble_event_t));
  return true;
}

void ble_get_state(ble_state_t *state) {
  const ble_driver_t *drv = &g_ble_driver;
  memset(state, 0, sizeof(ble_state_t));

  if (!is_enabled(drv)) {
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

  if (!is_enabled(drv)) {
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

  struct pollfd fds[] = {
      {drv->data_sock, POLLOUT, 0},
  };
  int r = poll(fds, 1, 0);
  return (r > 0);
}

bool ble_write(const uint8_t *data, uint16_t len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return false;
  }

  if (!drv->connected) {
    printf("unix/ble: ble_write while disconnected\n");
    return false;
  }

  ssize_t r = len;
  if (drv->data_slen > 0) {
    r = sendto(drv->data_sock, data, len, MSG_DONTWAIT,
               (const struct sockaddr *)&(drv->data_si_other), drv->data_slen);
  }
  return r;
}

bool ble_can_read(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv) || !drv->connected) {
    return false;
  }

  struct pollfd fds[] = {
      {drv->data_sock, POLLIN, 0},
  };
  int r = poll(fds, 1, 0);
  return (r > 0);
}

uint32_t ble_read(uint8_t *data, uint16_t max_len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!is_enabled(drv)) {
    return 0;
  }

  if (!drv->connected) {
    printf("unix/ble: ble_read while disconnected\n");
    return false;
  }

  struct sockaddr_in si;
  socklen_t sl = sizeof(si);
  uint8_t buf[max_len];
  memset(buf, 0, max_len);
  ssize_t r = recvfrom(drv->data_sock, buf, sizeof(buf), MSG_DONTWAIT,
                       (struct sockaddr *)&si, &sl);
  if (r <= 0) {
    return 0;
  }

  drv->data_si_other = si;
  drv->data_slen = sl;
  memcpy(data, buf, r);
  return r;
}

bool ble_get_mac(bt_le_addr_t *addr) {
  ble_driver_t *drv = &g_ble_driver;

  if (!is_enabled(drv)) {
    memset(addr, 0, sizeof(*addr));
    return false;
  }

  printf("unix/ble: ble_get_mac not implemented\n");
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
  printf("unix/ble: set_high_speed not implemented\n");
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
  printf("unix/ble: ble_notify not implemented\n");
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
      struct pollfd fds[] = {
          {drv->event_sock, POLLIN, 0},
      };
      int r = poll(fds, 1, 0);
      ready = (r > 0);
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
