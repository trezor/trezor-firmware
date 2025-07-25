/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/net_buf.h>
#include <zephyr/bluetooth/hci_types.h>
#include <zephyr/sys/byteorder.h>

#include "dtm_transport.h"
#include "hci_uart.h"

#ifndef CONFIG_DTM_TRANSPORT_LOG_LEVEL
#define CONFIG_DTM_TRANSPORT_LOG_LEVEL CONFIG_LOG_DEFAULT_LEVEL
#endif

#ifdef CONFIG_DTM_TRANSPORT_HCI
#define QUEUE_COUNT CONFIG_DTM_HCI_QUEUE_COUNT
#define QUEUE_SIZE CONFIG_DTM_HCI_QUEUE_SIZE
#define TX_THREAD_STACK_SIZE CONFIG_DTM_HCI_TX_THREAD_STACK_SIZE
#define TX_THREAD_PRIORITY CONFIG_DTM_HCI_TX_THREAD_PRIORITY
#else
#define QUEUE_COUNT CONFIG_REMOTE_HCI_QUEUE_COUNT
#define QUEUE_SIZE CONFIG_REMOTE_HCI_QUEUE_SIZE
#define TX_THREAD_STACK_SIZE CONFIG_REMOTE_HCI_TX_THREAD_STACK_SIZE
#define TX_THREAD_PRIORITY CONFIG_REMOTE_HCI_TX_THREAD_PRIORITY
#endif

#define UART_DMA_BUF_SIZE 128
#define UART_TIMEOUT_US 10000

LOG_MODULE_REGISTER(dtm_hci_uart, CONFIG_DTM_TRANSPORT_LOG_LEVEL);

#define DTM_UART DT_CHOSEN(ncs_dtm_uart)
static const struct device *hci_uart_dev = DEVICE_DT_GET(DTM_UART);

NET_BUF_POOL_DEFINE(hci_tx_buf, QUEUE_COUNT, QUEUE_SIZE, 0, NULL);
static K_FIFO_DEFINE(hci_tx_queue);

NET_BUF_POOL_DEFINE(hci_rx_buf, QUEUE_COUNT, QUEUE_SIZE, sizeof(uint8_t), NULL);

enum h4_state {
	S_TYPE,
	S_HEADER,
	S_PAYLOAD
};

static hci_uart_read_cb dtm_hci_put;

static size_t hci_hdr_len(uint8_t type)
{
	switch (type) {
	case H4_TYPE_CMD:
		return sizeof(struct bt_hci_cmd_hdr);

	case H4_TYPE_ACL:
		return sizeof(struct bt_hci_acl_hdr);

	case H4_TYPE_EVT:
		return sizeof(struct bt_hci_evt_hdr);

	case H4_TYPE_ISO:
		return sizeof(struct bt_hci_iso_hdr);

	default:
		return 0;
	}
}

static size_t hci_pld_len(uint8_t type, uint8_t *hdr)
{
	switch (type) {
	case H4_TYPE_CMD:
		return ((struct bt_hci_cmd_hdr *)hdr)->param_len;

	case H4_TYPE_ACL:
		return sys_le16_to_cpu(((struct bt_hci_acl_hdr *)hdr)->len);

	case H4_TYPE_ISO:
		return sys_le16_to_cpu(((struct bt_hci_iso_hdr *)hdr)->len);

	default:
		return 0;
	}
}

static bool h4_rx_type(uint8_t type)
{
	return ((type == H4_TYPE_CMD) | (type == H4_TYPE_ACL) | (type == H4_TYPE_ISO));
}

static size_t buf_read(struct net_buf *buf, const uint8_t *src, size_t src_len, size_t req_len)
{
	size_t len;

	if (req_len > src_len) {
		len = src_len;
	} else {
		len = req_len;
	}

	if (net_buf_tailroom(buf) < len) {
		__ASSERT_NO_MSG(false);
	}
	net_buf_add_mem(buf, src, len);

	return len;
}

static void h4_read(const uint8_t *data, size_t offset, size_t len)
{
	static enum h4_state state = S_TYPE;
	static struct net_buf *buf;
	static uint8_t type;
	static size_t rem;
	size_t read;

	while (len > 0) {
		switch (state) {
		case S_TYPE:
			type = data[offset];
			offset += sizeof(type);
			len -= sizeof(type);

			if (h4_rx_type(type)) {
				rem = hci_hdr_len(type);
				buf = net_buf_alloc(&hci_rx_buf, K_NO_WAIT);
				if (!buf) {
					__ASSERT_NO_MSG(false);
					/* Out of buffers condition */
				}

				*(uint8_t *)net_buf_user_data(buf) = type;
				state = S_HEADER;
			} else {
				/* TODO: Sync failure */
			}
			break;

		case S_HEADER:
			read = buf_read(buf, &data[offset], len, rem);
			offset += read;
			len -= read;
			rem -= read;
			if (rem == 0) {
				rem = hci_pld_len(type, buf->data);
				state = S_PAYLOAD;
				if (rem == 0) {
					if (dtm_hci_put) {
						dtm_hci_put(buf);
					} else {
						LOG_ERR("Callback dtm_hci_put is not assigned.");
					}
					state = S_TYPE;
				}
			}
			break;

		case S_PAYLOAD:
			read = buf_read(buf, &data[offset], len, rem);
			offset += read;
			len -= read;
			rem -= read;
			if (rem == 0) {
				if (dtm_hci_put) {
					dtm_hci_put(buf);
				} else {
					LOG_ERR("Callback dtm_hci_put is not assigned.");
				}
				state = S_TYPE;
			}
			break;

		default:
			state = S_TYPE;
			break;
		}
	}
}

static uint8_t *uart_buf(void)
{
	static uint32_t cur;
	static uint8_t buf1[UART_DMA_BUF_SIZE];
	static uint8_t buf2[UART_DMA_BUF_SIZE];

	cur = (cur + 1) % 2;

	if (cur == 0) {
		return buf1;
	} else {
		return buf2;
	}
}

static void uart_cb(const struct device *dev, struct uart_event *evt, void *user_data)
{
	struct net_buf *buf;

	switch (evt->type) {
	case UART_TX_DONE:
		LOG_DBG("Uart TX done");
		/* The pointer to net_buf is the first datum before the uart TX pointer */
		buf = *(struct net_buf **)(evt->data.tx.buf - sizeof(buf));
		net_buf_unref(buf);
		break;

	case UART_TX_ABORTED:
		LOG_DBG("Uart TX aborted");
		/* The pointer to net_buf is the first datum before the uart TX pointer */
		buf = *(struct net_buf **)(evt->data.tx.buf - sizeof(buf));
		net_buf_unref(buf);
		break;

	case UART_RX_RDY:
		LOG_DBG("Uart RX ready");
		h4_read(evt->data.rx.buf, evt->data.rx.offset, evt->data.rx.len);
		break;

	case UART_RX_BUF_REQUEST:
		LOG_DBG("Uart rx buf request");
		uart_rx_buf_rsp(dev, uart_buf(), UART_DMA_BUF_SIZE);
		break;

	case UART_RX_BUF_RELEASED:
		LOG_DBG("Uart rx buf released");
		break;

	case UART_RX_DISABLED:
		LOG_DBG("Uart rx disabled");
		break;

	case UART_RX_STOPPED:
		LOG_DBG("Uart rx stopped");
		break;
	}
}

static void tx_thread(void)
{
	struct net_buf *buf;

	for (;;) {
		/* The first pointer is discarded as it serves internal purpose
		 * and it's not supposed to be sent over uart.
		 * The pointer is an address to the associated net_buf.
		 */
		buf = k_fifo_get(&hci_tx_queue, K_FOREVER);
		uart_tx(hci_uart_dev, &buf->data[sizeof(buf)],
			buf->len - sizeof(buf), SYS_FOREVER_US);
	}
}
K_THREAD_DEFINE(tx_thread_id, TX_THREAD_STACK_SIZE, tx_thread,
		NULL, NULL, NULL,
		TX_THREAD_PRIORITY, 0, 0);

int hci_uart_init(hci_uart_read_cb cb)
{
	int err;

	dtm_hci_put = cb;

	if (!device_is_ready(hci_uart_dev)) {
		LOG_ERR("UART device not ready");
		return -EIO;
	}

	err = uart_callback_set(hci_uart_dev, uart_cb, NULL);
	if (err) {
		LOG_ERR("UART callback not set %d", err);
		return err;
	}

	err = uart_rx_enable(hci_uart_dev, uart_buf(), UART_DMA_BUF_SIZE, UART_TIMEOUT_US);
	if (err) {
		LOG_ERR("UART rx not enabled %d", err);
		return err;
	}

	return 0;
}

int hci_uart_write(uint8_t type, const uint8_t *hdr, size_t hdr_len, const uint8_t *pld, size_t len)
{
	struct net_buf *buf;

	buf = net_buf_alloc(&hci_tx_buf, K_NO_WAIT);
	if (!buf) {
		return -ENOMEM;
	}

	if (net_buf_tailroom(buf) < (len + hdr_len + sizeof(type) + sizeof(buf))) {
		net_buf_unref(buf);
		return -ENOMEM;
	}

	/* Pointer to net_buf is saved in order to unref it in uart callback. */
	net_buf_add_mem(buf, (uint8_t *)&buf, sizeof(buf));
	net_buf_add_u8(buf, type);
	net_buf_add_mem(buf, hdr, hdr_len);
	net_buf_add_mem(buf, pld, len);

	k_fifo_put(&hci_tx_queue, buf);
	return 0;
}
