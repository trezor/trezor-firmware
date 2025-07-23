/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/net_buf.h>
#include <zephyr/logging/log.h>
#include <nrf_rpc/nrf_rpc_ipc.h>
#include <nrf_rpc_cbor.h>

#include "hci_uart.h"
#include "dtm_serialization.h"

LOG_MODULE_REGISTER(serialization_layer, CONFIG_DTM_REMOTE_HCI_LOG_LEVEL);

NRF_RPC_IPC_TRANSPORT(hci_group_tr, DEVICE_DT_GET(DT_NODELABEL(ipc0)), "dtm_ept");
NRF_RPC_GROUP_DEFINE(hci_group, "hci_remote", &hci_group_tr, NULL, NULL, NULL);

static K_FIFO_DEFINE(dtm_put_queue);

static void dtm_hci_put_wrapper(struct net_buf *buf);

static void rsp_error_code_send(const struct nrf_rpc_group *group, int err_code)
{
	struct nrf_rpc_cbor_ctx ctx;
	size_t buffer_size_max = 5;

	NRF_RPC_CBOR_ALLOC(group, ctx, buffer_size_max);

	if (!zcbor_int32_put(ctx.zs, err_code)) {
		goto error_exit;
	}

	nrf_rpc_cbor_rsp_no_err(group, &ctx);

	return;

error_exit:
	__ASSERT_NO_MSG(false);
}

/* Outgoing event dtm_hci_put to network core (DTM). */
static void dtm_hci_put_remote(struct net_buf *buf)
{
	struct nrf_rpc_cbor_ctx ctx;
	size_t buffer_size_max = 10;

	LOG_DBG("Call to dtm_hci_put");

	buffer_size_max += buf->len;

	NRF_RPC_CBOR_ALLOC(&hci_group, ctx, buffer_size_max);

	if (!zcbor_uint_encode(ctx.zs, &buf->user_data[0], sizeof(buf->user_data[0]))) {
		goto error_exit;
	}

	if (!zcbor_bstr_encode_ptr(ctx.zs, buf->data, buf->len)) {
		goto error_exit;
	}

	nrf_rpc_cbor_evt(&hci_group, RPC_DTM_HCI_PUT_EVT, &ctx);

	return;

error_exit:
	__ASSERT_NO_MSG(false);
}

/* Incoming hci_uart_write command from network core (DTM) */
static void hci_uart_write_handler(const struct nrf_rpc_group *group, struct nrf_rpc_cbor_ctx *ctx,
				  void *handler_data)
{
	int err;
	uint8_t type;
	struct zcbor_string hdr;
	struct zcbor_string pld;

	LOG_DBG("Call from hci_uart_write");

	if (!zcbor_uint_decode(ctx->zs, &type, sizeof(type))) {
		goto error_exit;
	}

	if (!zcbor_bstr_decode(ctx->zs, &hdr)) {
		goto error_exit;
	}

	if (!zcbor_bstr_decode(ctx->zs, &pld)) {
		goto error_exit;
	}

	err = hci_uart_write(type, hdr.value, hdr.len, pld.value, pld.len);
	nrf_rpc_cbor_decoding_done(group, ctx);
	rsp_error_code_send(group, err);

	return;

error_exit:
	__ASSERT_NO_MSG(false);
}

NRF_RPC_CBOR_CMD_DECODER(hci_group, hci_uart_write, RPC_HCI_UART_WRITE_CMD,
			 hci_uart_write_handler, NULL);

/* Incoming command hci_uart_init from network core (DTM). */
static void hci_uart_init_handler(const struct nrf_rpc_group *group, struct nrf_rpc_cbor_ctx *ctx,
				  void *handler_data)
{
	int err;

	LOG_DBG("Call from hci_uart_init");
	nrf_rpc_cbor_decoding_done(group, ctx);

	err = hci_uart_init(dtm_hci_put_wrapper);
	rsp_error_code_send(group, err);
}

NRF_RPC_CBOR_CMD_DECODER(hci_group, hci_uart_init, RPC_HCI_UART_INIT_CMD,
			 hci_uart_init_handler, NULL);

static void dtm_hci_put_wrapper(struct net_buf *buf)
{
	k_fifo_put(&dtm_put_queue, buf);
}

static void dtm_put_thread(void)
{
	struct net_buf *buf;

	for (;;) {
		buf = k_fifo_get(&dtm_put_queue, K_FOREVER);

		__ASSERT_NO_MSG(buf != NULL);

		dtm_hci_put_remote(buf);
		net_buf_unref(buf);
	}
}

K_THREAD_DEFINE(dtm_put_thread_id, CONFIG_DTM_PUT_THREAD_STACK_SIZE, dtm_put_thread,
		NULL, NULL, NULL,
		CONFIG_DTM_PUT_THREAD_PRIORITY, 0, 0);

static void err_handler(const struct nrf_rpc_err_report *report)
{
	LOG_ERR("nRF RPC error %d ocurred. See nRF RPC logs for more details.", report->code);
	k_oops();
}

int main(void)
{
	int err;

	LOG_INF("RPC init begin");

	err = nrf_rpc_init(err_handler);
	if (err) {
		LOG_ERR("nrf_rpc_init failed: %d", err);
		return -EIO;
	}

	LOG_INF("RPC init done");

	return 0;
}
