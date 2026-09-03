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
#include <pthread.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <sys/sysevent_source.h>
#include <time.h>
#include <unistd.h>

#include <io/unix/sock.h>
#include <io/usb.h>
#include <io/usb_hid.h>
#include <io/usb_vcp.h>
#include <io/usb_webusb.h>
#include <sys/profile.h>

#include "memzero.h"

#define USBD_MAX_NUM_INTERFACES 8

#define USB_RX_BUFFER_SIZE 64

// These applies only to the USB VCP interface
#define USB_TX_BUFFER_SIZE 128
#define USB_FLUSH_INTERVAL_MS 10

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
  emu_sock_t sock;
  uint8_t rx_buf[USB_RX_BUFFER_SIZE];
  int rx_len;
  pthread_mutex_t tx_lock;
  uint8_t tx_buf[USB_TX_BUFFER_SIZE];
  size_t tx_len;
  pthread_t flush_thread;
  bool flush_thread_running;
} usb_iface_t;

static usb_iface_t usb_ifaces[USBD_MAX_NUM_INTERFACES];

// forward declaration
static const syshandle_vmt_t usb_iface_handle_vmt;
static void *usb_flush_thread(void *arg);
static void usb_flush(usb_iface_t *iface);

secbool usb_init(const usb_dev_info_t *dev_info) {
  UNUSED(dev_info);
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];
    iface->handle = 0;
    iface->type = USB_IFACE_TYPE_DISABLED;
    iface->port = 0;
    sock_init(&iface->sock);
    memzero(&iface->rx_buf, sizeof(usb_ifaces[i].rx_buf));
    iface->rx_len = 0;
    pthread_mutex_init(&iface->tx_lock, NULL);
    iface->tx_len = 0;
    iface->flush_thread_running = false;
  }
  return sectrue;
}

void usb_deinit(void) { usb_stop(); }

secbool usb_start(const usb_start_params_t *params) {
  const char *ip = getenv("TREZOR_UDP_IP");

  // iterate interfaces
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];
    // skip if not HID or WebUSB interface
    if (iface->type != USB_IFACE_TYPE_HID &&
        iface->type != USB_IFACE_TYPE_WEBUSB &&
        iface->type != USB_IFACE_TYPE_VCP) {
      continue;
    }

    sock_start(&iface->sock, ip, iface->port);

    ensure(sectrue *
               syshandle_register(iface->handle, &usb_iface_handle_vmt, iface),
           NULL);

    if (iface->type == USB_IFACE_TYPE_VCP) {
      iface->flush_thread_running = true;
      pthread_create(&iface->flush_thread, NULL, usb_flush_thread, iface);
    }
  }

  return sectrue;
}

void usb_stop(void) {
  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &usb_ifaces[i];

    if (iface->flush_thread_running) {
      pthread_mutex_lock(&iface->tx_lock);
      iface->flush_thread_running = false;
      pthread_mutex_unlock(&iface->tx_lock);

      pthread_join(iface->flush_thread, NULL);

      pthread_mutex_lock(&iface->tx_lock);
      usb_flush(iface);
      pthread_mutex_unlock(&iface->tx_lock);
    }

    sock_stop(&iface->sock);
    syshandle_unregister(iface->handle);
  }
}

secbool usb_hid_add(const usb_hid_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES) {
    usb_iface_t *iface = &usb_ifaces[info->iface_num];
    if (iface->type == USB_IFACE_TYPE_DISABLED) {
      iface->type = USB_IFACE_TYPE_HID;
      iface->port = info->emu_port;
      iface->handle = info->handle;
      return sectrue;
    }
  }
  return secfalse;
}

secbool usb_webusb_add(const usb_webusb_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES) {
    usb_iface_t *iface = &usb_ifaces[info->iface_num];
    if (iface->type == USB_IFACE_TYPE_DISABLED) {
      iface->type = USB_IFACE_TYPE_WEBUSB;
      iface->port = info->emu_port;
      iface->handle = info->handle;
      return sectrue;
    }
  }
  return secfalse;
}

secbool usb_vcp_add(const usb_vcp_info_t *info) {
  if (info->iface_num < USBD_MAX_NUM_INTERFACES) {
    usb_iface_t *iface = &usb_ifaces[info->iface_num];
    if (iface->type == USB_IFACE_TYPE_DISABLED) {
      iface->type = USB_IFACE_TYPE_VCP;
      iface->port = info->emu_port;
      iface->handle = info->handle;
      return sectrue;
    }
  }
  return secfalse;
}

static secbool usb_emulated_poll_read(usb_iface_t *iface) {
  if (iface->rx_len > 0) {
    return sectrue;
  }

  if (!sock_can_recv(&iface->sock)) {
    return secfalse;
  }

  size_t len =
      sock_recvfrom(&iface->sock, iface->rx_buf, sizeof(iface->rx_buf));
  if (!len) {
    return secfalse;
  }

  static const char *ping_req = "PINGPING";
  static const char *ping_resp = "PONGPONG";
  if (len == strlen(ping_req) &&
      0 == memcmp(ping_req, iface->rx_buf, strlen(ping_req))) {
    sock_sendto(&iface->sock, (const uint8_t *)ping_resp, strlen(ping_resp));
    memzero(iface->rx_buf, sizeof(iface->rx_buf));
    return secfalse;
  }

  iface->rx_len = len;

  return sectrue;
}

static secbool usb_emulated_poll_write(usb_iface_t *iface) {
  return sectrue * sock_can_send(&iface->sock);
}

static int usb_emulated_read(usb_iface_t *iface, uint8_t *buf, uint32_t len) {
  if (iface->rx_len > 0) {
    if (iface->rx_len < len) {
      len = iface->rx_len;
    }
    memcpy(buf, iface->rx_buf, len);

    if (iface->type == USB_IFACE_TYPE_VCP) {
      iface->rx_len -= len;
      memmove(iface->rx_buf, iface->rx_buf + len, iface->rx_len);
    } else {
      iface->rx_len = 0;
      memzero(iface->rx_buf, sizeof(iface->rx_buf));
    }
    return len;
  }

  return 0;
}

static void usb_flush(usb_iface_t *iface) {
  if (iface->tx_len > 0) {
    sock_sendto(&iface->sock, iface->tx_buf, iface->tx_len);
    iface->tx_len = 0;
  }
}

static void *usb_flush_thread(void *arg) {
  usb_iface_t *iface = (usb_iface_t *)arg;

  while (true) {
    usleep(USB_FLUSH_INTERVAL_MS * 1000);

    pthread_mutex_lock(&iface->tx_lock);
    if (!iface->flush_thread_running) {
      pthread_mutex_unlock(&iface->tx_lock);
      break;
    }
    usb_flush(iface);
    pthread_mutex_unlock(&iface->tx_lock);
  }

  return NULL;
}

static ssize_t usb_emulated_write(usb_iface_t *iface, const uint8_t *buf,
                                  uint32_t len) {
  if (iface->type != USB_IFACE_TYPE_VCP) {
    return sock_sendto(&iface->sock, buf, len);
  }

  pthread_mutex_lock(&iface->tx_lock);

  size_t written = 0;
  while (written < len) {
    size_t space = sizeof(iface->tx_buf) - iface->tx_len;
    size_t chunk = MIN(space, (size_t)len - written);

    memcpy(&iface->tx_buf[iface->tx_len], buf + written, chunk);
    iface->tx_len += chunk;
    written += chunk;

    if (iface->tx_len == sizeof(iface->tx_buf)) {
      usb_flush(iface);
    }
  }

  pthread_mutex_unlock(&iface->tx_lock);

  return (ssize_t)written;
}

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

static ssize_t on_read(void *context, void *buffer, size_t buffer_size) {
  usb_iface_t *iface = (usb_iface_t *)context;

  return usb_emulated_read(iface, (uint8_t *)buffer, buffer_size);
}

static ssize_t on_write(void *context, const void *data, size_t data_size) {
  usb_iface_t *iface = (usb_iface_t *)context;

  return usb_emulated_write(iface, (const uint8_t *)data, data_size);
}

static const syshandle_vmt_t usb_iface_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = on_check_write_ready,
    .poll = on_event_poll,
    .read = on_read,
    .write = on_write,
};
