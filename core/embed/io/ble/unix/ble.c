#include <io/ble.h>
#include <trezor_rtl.h>

#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static const uint16_t DATA_PORT_OFFSET = 4;  // see usb.py
static const uint16_t EVENT_PORT_OFFSET = 5;

typedef enum {
  BLE_MODE_OFF,
  BLE_MODE_CONNECTABLE,
  BLE_MODE_PAIRING,
} ble_mode_t;

typedef struct {
  ble_mode_t mode_requested;
  ble_mode_t mode_current;
  bool connected;
  uint8_t peer_count;
  bool initialized;
  bool accept_msgs;
  bool pairing_requested;

  ble_adv_start_cmd_data_t adv_cmd;
  uint8_t mac[6];
  bool mac_ready;

  uint16_t data_port;
  int data_sock;
  struct sockaddr_in data_si_me, data_si_other;
  socklen_t data_slen;

  uint16_t event_port;
  int event_sock;
  struct sockaddr_in event_si_me, event_si_other;
  socklen_t event_slen;
} ble_driver_t;

static ble_driver_t g_ble_driver = {0};

// These are called from the kernel only, emulator doesn't have a kernel.
bool ble_init(void) { return true; }

void ble_deinit(void) {}

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
  drv->event_sock =
      socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK,
             IPPROTO_UDP);  // FIXME TCP might make more sense here

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

bool ble_issue_command(ble_command_t *command) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized) {
    return false;
  }

  bool result = false;

  switch (command->cmd_type) {
    case BLE_SWITCH_OFF:
      drv->mode_requested = BLE_MODE_OFF;
      result = true;
      break;
    case BLE_SWITCH_ON:
      memcpy(&drv->adv_cmd, &command->data.adv_start, sizeof(drv->adv_cmd));
      drv->mode_requested = BLE_MODE_CONNECTABLE;
      result = true;
      break;
    case BLE_PAIRING_MODE:
      memcpy(&drv->adv_cmd, &command->data.adv_start, sizeof(drv->adv_cmd));
      drv->mode_requested = BLE_MODE_PAIRING;
      result = true;
      break;
    case BLE_DISCONNECT:
      // result = ble_send_disconnect(drv);
      break;
    case BLE_ERASE_BONDS:
      // result = ble_send_erase_bonds(drv);
      break;
    case BLE_ALLOW_PAIRING:
      // result = ble_send_pairing_accept(drv);
      break;
    case BLE_REJECT_PAIRING:
      // result = ble_send_pairing_reject(drv);
      break;
    default:
      break;
  }

  return result;
}

bool ble_get_event(ble_event_t *event) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized /* || !drv->accept_msgs */) {
    return false;
  }
  struct sockaddr_in si;
  socklen_t sl = sizeof(si);
  uint8_t buf[sizeof(ble_event_t)] = {0};
  ssize_t r = recvfrom(drv->event_sock, buf, sizeof(buf), MSG_DONTWAIT,
                       (struct sockaddr *)&si, &sl);
  if (r <= 0) {
    return false;
  } else if (r != sizeof(ble_event_t)) {
    // TODO log error
    return false;
  }

  drv->event_si_other = si;
  drv->event_slen = sl;
  memcpy(event, buf, sizeof(ble_event_t));
  return true;
}

void ble_get_state(ble_state_t *state) {}

bool ble_can_write(void) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized || !drv->connected || !drv->accept_msgs) {
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
  if (!drv->initialized || !drv->connected || !drv->accept_msgs) {
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
  if (!drv->initialized || !drv->connected || !drv->accept_msgs) {
    return false;
  }

  struct pollfd fds[] = {
      {drv->data_sock, POLLIN, 0},
  };
  int r = poll(fds, 1, 0);
  return (r > 0);
  // FIXME emulated USB also handles PINGPING here
}

uint32_t ble_read(uint8_t *data, uint16_t max_len) {
  ble_driver_t *drv = &g_ble_driver;
  if (!drv->initialized || !drv->connected || !drv->accept_msgs) {
    return 0;
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

bool ble_get_mac(uint8_t *mac, size_t max_len) {
  // TODO
  return false;
}
