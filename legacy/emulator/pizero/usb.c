/*
 * Copyright (C) 2018, 2019 Yannick Heneault <yheneaul@gmail.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <poll.h>
#include <sys/sysmacros.h>
#include <pthread.h>

#include <libopencm3/usb/usbd.h>

struct usb_ctrlrequest; // forward declare to avoid including ch9.h

#include "usb-gadget.h"

#define MAX_ENDPOINT 8
#define MAX_USER_CONTROL_CALLBACK 4
#define MAX_USER_SET_CONFIG_CALLBACK    4
#define MAX_CONFIG_DESCRIPTOR 64

#define USB_TRANSACTION_IN 0
#define USB_TRANSACTION_OUT 1

#define USB_ENDPOINT_ADDRESS_MASK	0x0f
#define USB_ENDPOINT_DIR_MASK		0x80

struct usbd_endpoint {
	struct usb_gadget_endpoint *gadget_ep;
	usbd_endpoint_callback endpoint_callback;
	char *buf;
	size_t len;
	size_t max_len;
	pthread_mutex_t mutex;
	pthread_cond_t cond;
	pthread_t thread;
};

struct user_control_callback {
	usbd_control_callback cb;
	uint8_t type;
	uint8_t type_mask;
};

struct _usbd_device {
	usb_gadget_dev_handle *gadget;
	struct usbd_endpoint ep[MAX_ENDPOINT][2];
	struct user_control_callback user_control_callback[MAX_USER_CONTROL_CALLBACK];
	  usbd_set_config_callback user_callback_set_config[MAX_USER_SET_CONFIG_CALLBACK];
	uint8_t *control_buffer;
	uint16_t control_buffer_size;
};

const struct _usbd_driver {} otgfs_usb_driver = {};

uint16_t usbd_ep_read_packet(usbd_device *usbd_dev, uint8_t addr, void *buf, uint16_t len)
{
	struct usbd_endpoint *ep = &usbd_dev->ep[addr & USB_ENDPOINT_ADDRESS_MASK][USB_TRANSACTION_OUT];

	pthread_mutex_lock(&ep->mutex);
	if (ep->len < len) {
		len = ep->len;
	}
	memcpy(buf, ep->buf, len);
	ep->len = 0;
	pthread_cond_signal(&ep->cond);
	pthread_mutex_unlock(&ep->mutex);
	return len;
}

void usbd_poll(usbd_device *usbd_dev)
{
	emulatorPoll();

	struct pollfd fds;

	fds.fd = usb_gadget_control_fd(usbd_dev->gadget);
	fds.events = POLLIN;
	if (poll(&fds, 1, 1) == 1) {
		usb_gadget_handle_control_event(usbd_dev->gadget);
	}

	for (int i = 1; i < MAX_ENDPOINT; i++) {
		struct usbd_endpoint *ep = &usbd_dev->ep[i][USB_TRANSACTION_OUT];

		if (ep->endpoint_callback) {
			pthread_mutex_lock(&ep->mutex);
			size_t len = ep->len;
			pthread_mutex_unlock(&ep->mutex);
			if (len == 0) {
				continue;
			} else {
				ep->endpoint_callback(usbd_dev, i);
				return;
			}
		}
	}
}

uint16_t usbd_ep_write_packet(usbd_device *usbd_dev, uint8_t addr, const void *buf, uint16_t len)
{
	struct usbd_endpoint *ep = &usbd_dev->ep[addr & USB_ENDPOINT_ADDRESS_MASK][USB_TRANSACTION_IN];
	return usb_gadget_endpoint_write(ep->gadget_ep, buf, len);
}

void usbd_ep_setup(usbd_device *usbd_dev, uint8_t addr, uint8_t type, uint16_t max_size, usbd_endpoint_callback cb)
{
	(void) type;

	int dir = addr & USB_ENDPOINT_DIR_MASK ? USB_TRANSACTION_IN : USB_TRANSACTION_OUT;
	addr &= USB_ENDPOINT_ADDRESS_MASK;
	struct usbd_endpoint *ep = &usbd_dev->ep[addr][dir];

	ep->max_len = max_size;

	if (cb) {
		ep->endpoint_callback = cb;
	}
}

int usbd_register_control_callback(usbd_device *usbd_dev, uint8_t type, uint8_t type_mask, usbd_control_callback callback)
{
	for (int i = 0; i < MAX_USER_CONTROL_CALLBACK; i++) {
		struct user_control_callback *callback_entry = &usbd_dev->user_control_callback[i];
		if (callback_entry->cb) {
			continue;
		}

		callback_entry->type = type;
		callback_entry->type_mask = type_mask;
		callback_entry->cb = callback;
		return 0;
	}
	return -1;
}

static void *usbd_read_thread(void *data)
{
	struct usbd_endpoint *ep = (struct usbd_endpoint *) data;
	char *buf = malloc(ep->max_len);

	while (1) {
		ssize_t ret = usb_gadget_endpoint_read(ep->gadget_ep, buf, ep->max_len);

		if (ret < 0) {
			perror("usb_gadget_endpoint_read");
			break;
		}

		pthread_mutex_lock(&ep->mutex);
		while (ep->len != 0) {
			pthread_cond_wait(&ep->cond, &ep->mutex);
		}
		memcpy(ep->buf, buf, ep->max_len);
		ep->len = ret;
		pthread_mutex_unlock(&ep->mutex);
	}

	free(buf);
	return NULL;
}

static int usbd_event_dispatch(usb_gadget_dev_handle *gadget, struct usb_gadget_event *event, void *arg)
{
	usbd_device *usbd_dev = (usbd_device *) arg;

	switch (event->type) {
		case USG_EVENT_CONTROL_REQUEST:{
				/* Call user command hook function. */
				struct usb_setup_data *request = (struct usb_setup_data *) event->u.req;

				for (int i = 0; i < MAX_USER_CONTROL_CALLBACK; i++) {
					struct user_control_callback *callback_entry = &usbd_dev->user_control_callback[i];
					if (callback_entry->cb == NULL) {
						break;
					}

					if ((request->bmRequestType & callback_entry->type_mask) == callback_entry->type) {
						usbd_control_complete_callback complete;
						uint8_t *buf = usbd_dev->control_buffer;
						uint16_t len = usbd_dev->control_buffer_size;
						int ret = callback_entry->cb(usbd_dev, request, &buf, &len, &complete);
						if (ret == USBD_REQ_HANDLED) {
							write(usb_gadget_control_fd(gadget), buf, len);
							return ret;
						}
					}
				}

				return USBD_REQ_NOTSUPP;
			}

		case USG_EVENT_SET_CONFIG:
			/*
			 * Flush control callbacks. These will be reregistered
			 * by the user handler.
			 */
			for (int i = 0; i < MAX_USER_CONTROL_CALLBACK; i++) {
				usbd_dev->user_control_callback[i].cb = NULL;
			}

			for (int i = 0; i < MAX_USER_SET_CONFIG_CALLBACK; i++) {
				if (usbd_dev->user_callback_set_config[i]) {
					usbd_dev->user_callback_set_config[i] (usbd_dev, event->u.number);
				}
			}
			break;

		case USG_EVENT_ENDPOINT_ENABLE:{
				int dir = event->u.number & USB_ENDPOINT_DIR_MASK ? USB_TRANSACTION_IN : USB_TRANSACTION_OUT;
				int addr = event->u.number & USB_ENDPOINT_ADDRESS_MASK;
				struct usbd_endpoint *ep = &usbd_dev->ep[addr][dir];

				ep->gadget_ep = usb_gadget_endpoint(gadget, event->u.number);
				ep->buf = malloc(ep->max_len);

				if (ep->endpoint_callback != NULL && dir == USB_TRANSACTION_OUT) {
					pthread_create(&ep->thread, NULL, usbd_read_thread, ep);
				}
			}
			break;

		case USG_EVENT_ENDPOINT_DISABLE:{
				int dir = event->u.number & USB_ENDPOINT_DIR_MASK ? USB_TRANSACTION_IN : USB_TRANSACTION_OUT;
				int addr = event->u.number & USB_ENDPOINT_ADDRESS_MASK;
				struct usbd_endpoint *ep = &usbd_dev->ep[addr][dir];

				if (ep->gadget_ep) {
					usb_gadget_endpoint_close(ep->gadget_ep);
					ep->gadget_ep = NULL;
				}

				if (ep->thread) {
					pthread_join(ep->thread, NULL);
					ep->thread = 0;
				}

				free(ep->buf);
				ep->buf = NULL;
			}
			break;

		case USG_EVENT_DISCONNECT:
			for (int addr = 0; addr < MAX_ENDPOINT; addr++) {
				for (int dir = 0; dir < 2; dir++) {
					struct usbd_endpoint *ep = &usbd_dev->ep[addr][dir];

					if (ep->gadget_ep) {
						usb_gadget_endpoint_close(ep->gadget_ep);
						ep->gadget_ep = NULL;
					}

					if (ep->thread) {
						pthread_join(ep->thread, NULL);
						ep->thread = 0;
					}

					free(ep->buf);
					ep->buf = NULL;
				}
			}
			break;

		case USG_EVENT_CONNECT:
		case USG_EVENT_SUSPEND:
			break;
	}

	return 0;
}

usbd_device *usbd_init(const usbd_driver *driver, const struct usb_device_descriptor *device_descriptor,
                       const struct usb_config_descriptor *config_descriptor, const char * const * strings, int num_strings,
                       uint8_t *control_buffer, uint16_t control_buffer_size)
{
	(void) driver;

	struct _usbd_device *usbd_dev = calloc(sizeof(struct _usbd_device), 1);

	usbd_dev->control_buffer = control_buffer;
	usbd_dev->control_buffer_size = control_buffer_size;

	for (int addr = 0; addr < MAX_ENDPOINT; addr++) {
		for (int dir = 0; dir < 2; dir++) {
			struct usbd_endpoint *ep = &usbd_dev->ep[addr][dir];

			pthread_mutex_init(&ep->mutex, NULL);
			pthread_cond_init(&ep->cond, NULL);
		}
	}

	struct usb_gadget_strings *usb_gadget_strings = calloc(sizeof(struct usb_gadget_strings), 1);

	usb_gadget_strings->language = 0x409;	// USB_LANGID_ENGLISH_US
	usb_gadget_strings->strings = calloc(sizeof(struct usb_gadget_string), num_strings);

	for (int i = 0; i < num_strings; i++) {
		usb_gadget_strings->strings[i].id = i + 1;
		usb_gadget_strings->strings[i].s = strings[i];
	}

	int config_index = 0;
	struct usb_descriptor_header **config = calloc(sizeof(struct usb_descriptor_header *), MAX_CONFIG_DESCRIPTOR);

	config[config_index++] = (struct usb_descriptor_header *) config_descriptor;

	/* For each interface... */
	for (int i = 0; i < config_descriptor->bNumInterfaces; i++) {
		/* For each alternate setting... */
		for (int j = 0; j < config_descriptor->interface[i].num_altsetting; j++) {
			const struct usb_interface_descriptor *iface = &config_descriptor->interface[i].altsetting[j];
			config[config_index++] = (struct usb_descriptor_header *) iface;
			/* Copy extra bytes (function descriptors). */
			if (iface->extra) {
				config[config_index++] = (struct usb_descriptor_header *) iface->extra;
			}
			/* For each endpoint... */
			for (int k = 0; k < iface->bNumEndpoints; k++) {
				const struct usb_endpoint_descriptor *ep = &iface->endpoint[k];

				config[config_index++] = (struct usb_descriptor_header *) ep;

				/* Copy extra bytes (class specific). */
				if (ep->extra) {
					config[config_index++] = (struct usb_descriptor_header *) ep->extra;
				}
			}
		}
	}

	config[config_index++] = NULL;

	struct usb_gadget_device *gadget_description = calloc(sizeof(struct usb_gadget_device), 1);

	gadget_description->device = (struct usb_device_descriptor *) device_descriptor;
	gadget_description->config = config;
	gadget_description->hs_config = config;
	gadget_description->strings = usb_gadget_strings;

	usb_gadget_dev_handle *gadget = usb_gadget_open(gadget_description);

	if (!gadget) {
		fprintf(stderr, "Error with usb_gadget_open\n");
		exit(1);
	}

	usbd_dev->gadget = gadget;
	usb_gadget_set_event_cb(gadget, usbd_event_dispatch, usbd_dev);

	usb_gadget_set_debug_level(gadget, 999);

	return usbd_dev;
}

int usbd_register_set_config_callback(usbd_device *usbd_dev, usbd_set_config_callback callback)
{
	for (int i = 0; i < MAX_USER_SET_CONFIG_CALLBACK; i++) {
		if (usbd_dev->user_callback_set_config[i]) {
			continue;
		}

		usbd_dev->user_callback_set_config[i] = callback;
		return 0;
	}

	return -1;
}

void usbd_disconnect(usbd_device *usbd_dev, bool disconnected)
{
	(void) usbd_dev;
	(void) disconnected;
	//not used
}
