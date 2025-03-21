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

#include <arpa/inet.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <sys/sysevent_source.h>
#include <time.h>
#include <unistd.h>

#include <io/usb.h>
#include "profile.h"

#include "memzero.h"

// emulator opens UDP server and emulates HID/WebUSB interfaces
// gracefully ignores all other USB interfaces

#define USBD_MAX_NUM_INTERFACES 8

typedef enum {
  USB_IFACE_TYPE_DISABLED = 0,
  USB_IFACE_TYPE_VCP = 1,
  USB_IFACE_TYPE_HID = 2,
  USB_IFACE_TYPE_WEBUSB = 3,
} usb_iface_type_t;

typedef struct {
  syshandle_t handle;
  usb_iface_type_t type;
  uint16_t port;
  int sock;
  struct sockaddr_in si_me, si_other;
  socklen_t slen;
  uint8_t msg[64];
  int msg_len;
} usb_iface_t;

static usb_iface_t usb_ifaces[USBD_MAX_NUM_INTERFACES];

// forward declaration
static const syshandle_vmt_t usb_iface_handle_vmt;

secbool usb_init(const usb_dev_info_t *dev_info) {
  UNUSED(dev_info);
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];
    iface->handle = SYSHANDLE_USB_IFACE_0 + i;
    iface->type = USB_IFACE_TYPE_DISABLED;
    iface->port = 0;
    iface->sock = -1;
    memzero(&iface->si_me, sizeof(struct sockaddr_in));
    memzero(&iface->si_other, sizeof(struct sockaddr_in));
    memzero(&iface->msg, sizeof(usb_ifaces[i].msg));
    iface->slen = 0;
    iface->msg_len = 0;
  }
  return sectrue;
}

void usb_deinit(void) { usb_stop(); }

secbool usb_start(void) {
  const char *ip = getenv("TREZOR_UDP_IP");

  // iterate interfaces
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];
    // skip if not HID or WebUSB interface
    if (iface->type != USB_IFACE_TYPE_HID &&
        iface->type != USB_IFACE_TYPE_WEBUSB) {
      continue;
    }

    iface->sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    ensure(sectrue * (iface->sock >= 0), NULL);

    fcntl(iface->sock, F_SETFL, O_NONBLOCK);

    iface->si_me.sin_family = AF_INET;
    if (ip) {
      iface->si_me.sin_addr.s_addr = inet_addr(ip);
    } else {
      iface->si_me.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    }
    iface->si_me.sin_port = htons(iface->port);

    ensure(sectrue * (0 == bind(iface->sock, (struct sockaddr *)&iface->si_me,
                                sizeof(struct sockaddr_in))),
           NULL);

    ensure(sectrue * syshandle_register(SYSHANDLE_USB_IFACE_0 + i,
                                        &usb_iface_handle_vmt, iface),
           NULL);
  }

  return sectrue;
}

void usb_stop(void) {
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];
    if (iface->sock >= 0) {
      close(iface->sock);
      iface->sock = -1;
      syshandle_unregister(SYSHANDLE_USB_IFACE_0 + i);
    }
  }
}

secbool usb_hid_add(const usb_hid_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES &&
      usb_ifaces[info->iface_num].type == USB_IFACE_TYPE_DISABLED) {
    usb_ifaces[info->iface_num].type = USB_IFACE_TYPE_HID;
    usb_ifaces[info->iface_num].port = info->emu_port;
  }
  return sectrue;
}

secbool usb_webusb_add(const usb_webusb_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES &&
      usb_ifaces[info->iface_num].type == USB_IFACE_TYPE_DISABLED) {
    usb_ifaces[info->iface_num].type = USB_IFACE_TYPE_WEBUSB;
    usb_ifaces[info->iface_num].port = info->emu_port;
  }
  return sectrue;
}

secbool usb_vcp_add(const usb_vcp_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES &&
      usb_ifaces[info->iface_num].type == USB_IFACE_TYPE_DISABLED) {
    usb_ifaces[info->iface_num].type = USB_IFACE_TYPE_VCP;
    usb_ifaces[info->iface_num].port = info->emu_port;
  }
  return sectrue;
}

static secbool usb_emulated_poll_read(usb_iface_t *iface) {
  if (iface->msg_len > 0) {
    return sectrue;
  }

  struct pollfd fds[] = {
      {iface->sock, POLLIN, 0},
  };
  int res = poll(fds, 1, 0);

  if (res <= 0) {
    return secfalse;
  }

  struct sockaddr_in si;
  socklen_t sl = sizeof(si);
  ssize_t r = recvfrom(iface->sock, iface->msg, sizeof(iface->msg),
                       MSG_DONTWAIT, (struct sockaddr *)&si, &sl);
  if (r <= 0) {
    return secfalse;
  }

  iface->si_other = si;
  iface->slen = sl;
  static const char *ping_req = "PINGPING";
  static const char *ping_resp = "PONGPONG";
  if (r == strlen(ping_req) &&
      0 == memcmp(ping_req, iface->msg, strlen(ping_req))) {
    if (iface->slen > 0) {
      sendto(iface->sock, ping_resp, strlen(ping_resp), MSG_DONTWAIT,
             (const struct sockaddr *)&iface->si_other, iface->slen);
    }
    memzero(iface->msg, sizeof(iface->msg));
    return secfalse;
  }

  iface->msg_len = r;

  return sectrue;
}

static secbool usb_emulated_poll_write(usb_iface_t *iface) {
  struct pollfd fds[] = {
      {iface->sock, POLLOUT, 0},
  };
  int r = poll(fds, 1, 0);
  return sectrue * (r > 0);
}

static int usb_emulated_read(usb_iface_t *iface, uint8_t *buf, uint32_t len) {
  if (iface->msg_len > 0) {
    if (iface->msg_len < len) {
      len = iface->msg_len;
    }
    memcpy(buf, iface->msg, len);
    iface->msg_len = 0;
    memzero(iface->msg, sizeof(iface->msg));
    return len;
  }

  return 0;
}

static int usb_emulated_write(usb_iface_t *iface, const uint8_t *buf,
                              uint32_t len) {
  ssize_t r = len;
  if (iface->slen > 0) {
    r = sendto(iface->sock, buf, len, MSG_DONTWAIT,
               (const struct sockaddr *)&iface->si_other, iface->slen);
  }
  return r;
}

secbool usb_hid_can_read(uint8_t iface_num) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
    return secfalse;
  }
  return usb_emulated_poll_read(&usb_ifaces[iface_num]);
}

secbool usb_webusb_can_read(uint8_t iface_num) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_WEBUSB) {
    return secfalse;
  }
  return usb_emulated_poll_read(&usb_ifaces[iface_num]);
}

secbool usb_hid_can_write(uint8_t iface_num) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
    return secfalse;
  }
  return usb_emulated_poll_write(&usb_ifaces[iface_num]);
}

secbool usb_webusb_can_write(uint8_t iface_num) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_WEBUSB) {
    return secfalse;
  }
  return usb_emulated_poll_write(&usb_ifaces[iface_num]);
}

int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
    return 0;
  }
  return usb_emulated_read(&usb_ifaces[iface_num], buf, len);
}

int usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_WEBUSB) {
    return 0;
  }
  return usb_emulated_read(&usb_ifaces[iface_num], buf, len);
}

int usb_webusb_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                             int timeout) {
  const uint32_t start = clock();
  while (sectrue != usb_webusb_can_read(iface_num)) {
    if (timeout >= 0 &&
        (1000 * (clock() - start)) / CLOCKS_PER_SEC >= timeout) {
      return 0;  // Timeout
    }
  }
  return usb_webusb_read(iface_num, buf, len);
}

int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
    return 0;
  }
  return usb_emulated_write(&usb_ifaces[iface_num], buf, len);
}

int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len,
                           int timeout) {
  const uint32_t start = clock();
  while (sectrue != usb_hid_can_write(iface_num)) {
    if (timeout >= 0 &&
        (1000 * (clock() - start)) / CLOCKS_PER_SEC >= timeout) {
      return 0;  // Timeout
    }
  }
  return usb_hid_write(iface_num, buf, len);
}

int usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  if (iface_num >= USBD_MAX_NUM_INTERFACES ||
      usb_ifaces[iface_num].type != USB_IFACE_TYPE_WEBUSB) {
    return 0;
  }
  return usb_emulated_write(&usb_ifaces[iface_num], buf, len);
}

int usb_webusb_write_blocking(uint8_t iface_num, const uint8_t *buf,
                              uint32_t len, int timeout) {
  const uint32_t start = clock();
  while (sectrue != usb_webusb_can_write(iface_num)) {
    if (timeout >= 0 &&
        (1000 * (clock() - start)) / CLOCKS_PER_SEC >= timeout) {
      return 0;  // Timeout
    }
  }
  return usb_webusb_write(iface_num, buf, len);
}

void mp_hal_set_vcp_iface(int iface_num) {}

secbool usb_configured(void) {
  if (access(profile_usb_disconnect_path(), F_OK) == 0) {
    return secfalse;
  }

  return sectrue;
}

usb_event_t usb_get_event(void) { return USB_EVENT_NONE; }

void usb_get_state(usb_state_t *state) {
  state->configured = usb_configured() == sectrue;
}

static void on_event_poll(void *context, bool read_awaited,
                          bool write_awaited) {
  usb_iface_t *iface = (usb_iface_t *)context;

  // Only one task can read or write at a time. Therefore, we can
  // assume that only one task is waiting for events and keep the
  // logic simple.

  if (read_awaited) {
    if (sectrue == usb_emulated_poll_read(iface)) {
      syshandle_signal_read_ready(iface->handle, NULL);
    }
  }

  if (write_awaited) {
    if (sectrue == usb_emulated_poll_write(iface)) {
      syshandle_signal_write_ready(iface->handle, NULL);
    }
  }
}

static bool on_check_read_ready(void *context, systask_id_t task_id,
                                void *param) {
  usb_iface_t *iface = (usb_iface_t *)context;

  UNUSED(task_id);
  UNUSED(param);

  return (sectrue == usb_emulated_poll_read(iface));
}

static bool on_check_write_ready(void *context, systask_id_t task_id,
                                 void *param) {
  usb_iface_t *iface = (usb_iface_t *)context;

  UNUSED(task_id);
  UNUSED(param);

  return usb_emulated_poll_write(iface);
}

static const syshandle_vmt_t usb_iface_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = on_check_write_ready,
    .poll = on_event_poll,
};
