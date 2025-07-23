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

LOG_MODULE_REGISTER(serialize_layer);

NRF_RPC_IPC_TRANSPORT(hci_group_tr, DEVICE_DT_GET(DT_NODELABEL(ipc0)), "dtm_ept");
NRF_RPC_GROUP_DEFINE(hci_group, "hci_remote", &hci_group_tr, NULL, NULL, NULL);

NET_BUF_POOL_DEFINE(tx_buf, CONFIG_DTM_HCI_QUEUE_COUNT, CONFIG_DTM_HCI_QUEUE_SIZE, 0, NULL);

static hci_uart_read_cb callback;

static void rsp_error_code_handle(const struct nrf_rpc_group *group, struct nrf_rpc_cbor_ctx *ctx,
				  void *handler_data)
{
	int32_t val;

	if (zcbor_int32_decode(ctx->zs, &val)) {
		*(int *)handler_data = (int)val;
	} else {
		*(int *)handler_data = -NRF_EINVAL;
	}
}

/* Incoming event from application core (uart) */
static void dtm_hci_put_handler(const struct nrf_rpc_group *group, struct nrf_rpc_cbor_ctx *ctx,
				void *handler_data)
{
	struct net_buf *buf;
	uint8_t type;
	struct zcbor_string tmp;

	LOG_DBG("Call from dtm_hci_put");

	if (!zcbor_uint_decode(ctx->zs, &type, sizeof(type))) {
		goto error_exit;
	}

	if (!zcbor_bstr_decode(ctx->zs, &tmp)) {
		goto error_exit;
	}

	buf = net_buf_alloc(&tx_buf, K_NO_WAIT);
	net_buf_add_mem(buf, tmp.value, tmp.len);
	buf->user_data[0] = type;

	nrf_rpc_cbor_decoding_done(group, ctx);

	callback(buf);

	return;

error_exit:
	__ASSERT_NO_MSG(false);
}

NRF_RPC_CBOR_EVT_DECODER(hci_group, dtm_hci_put, RPC_DTM_HCI_PUT_EVT, dtm_hci_put_handler, NULL);

/* Outgoing to application core (uart), save callback locally. */
int hci_uart_init(hci_uart_read_cb cb)
{
	int result;
	int err;
	struct nrf_rpc_cbor_ctx ctx;
	size_t buffer_size_max = 0;

	LOG_DBG("Call to hci_init");
	callback = cb;

	NRF_RPC_CBOR_ALLOC(&hci_group, ctx, buffer_size_max);

	err = nrf_rpc_cbor_cmd(&hci_group, RPC_HCI_UART_INIT_CMD, &ctx,
			       rsp_error_code_handle, &result);
	if (err < 0) {
		return err;
	}

	return result;
}

/* Outgoing to application core (uart) */
int hci_uart_write(uint8_t type, const uint8_t *hdr, size_t hdr_len, const uint8_t *pld, size_t len)
{
	int result;
	int err;
	struct nrf_rpc_cbor_ctx ctx;
	size_t buffer_size_max = 20;

	LOG_DBG("Call to hci_uart_write");

	buffer_size_max += hdr_len + len;

	NRF_RPC_CBOR_ALLOC(&hci_group, ctx, buffer_size_max);

	if (!zcbor_uint_encode(ctx.zs, &type, sizeof(type))) {
		goto error_exit;
	}

	if (!zcbor_bstr_encode_ptr(ctx.zs, hdr, hdr_len)) {
		goto error_exit;
	}

	if (!zcbor_bstr_encode_ptr(ctx.zs, pld, len)) {
		goto error_exit;
	}

	err = nrf_rpc_cbor_cmd(&hci_group, RPC_HCI_UART_WRITE_CMD, &ctx,
			       rsp_error_code_handle, &result);
	if (err < 0) {
		return err;
	}

	return result;

error_exit:
	__ASSERT_NO_MSG(false);
}

static void err_handler(const struct nrf_rpc_err_report *report)
{
	LOG_ERR("nRF RPC error %d ocurred. See nRF RPC logs for more details.",
	       report->code);
	k_oops();
}

static int serialization_init(void)
{
	int err;

	LOG_INF("RPC init begin\n");

	err = nrf_rpc_init(err_handler);
	if (err) {
		return -NRF_EINVAL;
	}

	LOG_INF("RPC init done\n");

	return 0;
}

SYS_INIT(serialization_init, POST_KERNEL, CONFIG_APPLICATION_INIT_PRIORITY);
