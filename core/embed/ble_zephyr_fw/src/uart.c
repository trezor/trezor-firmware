#include <zephyr/types.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>

#include <dk_buttons_and_leds.h>

#include <zephyr/settings/settings.h>
#include <zephyr/logging/log.h>

#include "uart.h"
#include "int_comm.h"
#include "int_comm_defs.h"
#include "events.h"

#define LOG_MODULE_NAME fw_uart
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define UART_WAIT_FOR_BUF_DELAY K_MSEC(50)
#define UART_WAIT_FOR_RX CONFIG_BT_NUS_UART_RX_WAIT_TIME

const struct device *uart = DEVICE_DT_GET(DT_CHOSEN(nordic_nus_uart));

static K_FIFO_DEFINE(fifo_uart_tx_data);
static K_FIFO_DEFINE(fifo_uart_rx_data);
static K_FIFO_DEFINE(fifo_uart_rx_data_int);
static K_FIFO_DEFINE(fifo_uart_rx_data_pb);


static struct k_poll_signal fifo_uart_rx_data_int_signal;


static void uart_cb(const struct device *dev, struct uart_event *evt, void *user_data)
{
  ARG_UNUSED(dev);

  static size_t aborted_len;
  uart_data_t *buf;
  static uint8_t *aborted_buf;
  static bool disable_req;
  static uint8_t rx_phase = 0;
  static uint8_t rx_msg_type = 0;
  static uint8_t rx_data_len = 0;
  static uint8_t rx_len = 0;

  switch (evt->type) {
    case UART_TX_DONE:
      LOG_DBG("UART_TX_DONE");
      if ((evt->data.tx.len == 0) ||
          (!evt->data.tx.buf)) {
        return;
      }

      if (aborted_buf) {
        buf = CONTAINER_OF(aborted_buf, uart_data_t,
        data);
        aborted_buf = NULL;
        aborted_len = 0;
      } else {
        buf = CONTAINER_OF(evt->data.tx.buf, uart_data_t,
        data);
      }

      k_free(buf);

      buf = k_fifo_get(&fifo_uart_tx_data, K_NO_WAIT);
      if (!buf) {
        return;
      }

      if (uart_tx(uart, buf->data, buf->len, SYS_FOREVER_MS)) {
        LOG_WRN("Failed to send data over UART");
      }

      break;

    case UART_RX_RDY:
      LOG_DBG("UART_RX_RDY");
      buf = CONTAINER_OF(evt->data.rx.buf, uart_data_t, data);
      buf->len += evt->data.rx.len;

      switch(rx_phase) {
        case 0:
          if (buf->len == 1 && (buf->data[0] == INTERNAL_EVENT || buf->data[0] == INTERNAL_MESSAGE || buf->data[0] == EXTERNAL_MESSAGE) ) {
            rx_phase = 1;
            rx_msg_type = buf->data[0];
          } else {
            rx_phase = 0;
          }
          break;
        case 1:
          if (buf->len == 2) {
            rx_data_len = buf->data[0] << 8 | buf->data[1];
            rx_phase = 2;
          } else{
            rx_phase = 0;
          }
          break;
        case 2:
          if (buf->len == rx_data_len - 3) {
            rx_phase = 3;
          } else {
            rx_phase = 0;
          }
          break;
      }

//		if (disable_req) {
//			return;
//		}

//		if ((evt->data.rx.buf[buf->len - 1] == '\n') ||
//		    (evt->data.rx.buf[buf->len - 1] == '\r')) {
//			disable_req = true;
//			uart_rx_disable(uart);
//		}

      break;

    case UART_RX_DISABLED:
      LOG_DBG("UART_RX_DISABLED");
      disable_req = false;

      buf = k_malloc(sizeof(*buf));

      if (buf) {

        switch (rx_phase) {
          case 0:
            rx_len = 1;
            break;
          case 1:
            rx_len = 2;
            break;
          case 2:
            rx_len = rx_data_len - 3;
            break;

          default:
            rx_len = 1;
            break;
        }

        buf->len = 0;
        uart_rx_enable(uart, buf->data, rx_len, SYS_FOREVER_US);
      } else {
        LOG_WRN("Not able to allocate UART receive buffer");
      }

//		buf = k_malloc(sizeof(*buf));
//		if (buf) {
//			buf->len = 0;
//		} else {
//			LOG_WRN("Not able to allocate UART receive buffer");
//			k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
//			return;
//		}
//
//		uart_rx_enable(uart, buf->data, sizeof(buf->data),
//			       UART_WAIT_FOR_RX);

      break;

//	case UART_RX_BUF_REQUEST:
//		LOG_INF("UART_RX_BUF_REQUEST");
//		buf = k_malloc(sizeof(*buf));
//
//
//		if (buf) {
//
//      switch (rx_phase) {
//        case 0:
//          rx_len = 1;
//          break;
//        case 1:
//          rx_len = 2;
//          break;
//        default:
//          rx_len = 1;
//          break;
//      }
//
//			buf->len = 0;
//      LOG_INF("Providing buf %d", rx_len);
//			uart_rx_buf_rsp(uart, buf->data, rx_len);
//		} else {
//			LOG_WRN("Not able to allocate UART receive buffer");
//		}
//
//		break;

    case UART_RX_BUF_RELEASED:
      LOG_DBG("UART_RX_BUF_RELEASED");
      buf = CONTAINER_OF(evt->data.rx_buf.buf, uart_data_t,
      data);

      if (rx_phase == 3 && buf->len > 0) {
        buf->len -= 1;
        if (rx_msg_type == EXTERNAL_MESSAGE) {
          k_fifo_put(&fifo_uart_rx_data, buf);
        }
        else  if (rx_msg_type == INTERNAL_EVENT) {
          k_fifo_put(&fifo_uart_rx_data_int, buf);
          k_poll_signal_raise(&fifo_uart_rx_data_int_signal, 0);
        }
        else {
          k_fifo_put(&fifo_uart_rx_data_pb, buf);
        }
        rx_data_len= 0;
        rx_len = 0;
        rx_msg_type = 0;
        rx_phase = 0;
      } else {
        k_free(buf);
      }
      break;

    case UART_TX_ABORTED:
      LOG_DBG("UART_TX_ABORTED");
      if (!aborted_buf) {
        aborted_buf = (uint8_t *)evt->data.tx.buf;
      }

      aborted_len += evt->data.tx.len;
      buf = CONTAINER_OF(aborted_buf, uart_data_t,
      data);

      uart_tx(uart, &buf->data[aborted_len],
              buf->len - aborted_len, SYS_FOREVER_MS);

      break;

    default:
      break;
  }
}


int uart_init(void)
{
  int err;
  uart_data_t *rx;



  if (!device_is_ready(uart)) {
    return -ENODEV;
  }

  k_poll_signal_init(&fifo_uart_rx_data_int_signal);
  k_poll_event_init(events_get(INT_COMM_EVENT_NUM),
                    K_POLL_TYPE_SIGNAL, K_POLL_MODE_NOTIFY_ONLY,
                    &fifo_uart_rx_data_int_signal);

  struct uart_config cfg = {
          .baudrate = 1000000,
          .parity = UART_CFG_PARITY_NONE,
          .stop_bits = UART_CFG_STOP_BITS_1,
          .data_bits = UART_CFG_DATA_BITS_8,
          .flow_ctrl = UART_CFG_FLOW_CTRL_RTS_CTS,

  };

  uart_configure(uart, &cfg);

  rx = k_malloc(sizeof(*rx));
  if (rx) {
    rx->len = 0;
  } else {
    return -ENOMEM;
  }

  err = uart_callback_set(uart, uart_cb, NULL);
  if (err) {
    LOG_ERR("Cannot initialize UART callback (err: %d) FF", err);
    k_free(rx);
    return err;
  }

  // receive message type
  err = uart_rx_enable(uart, rx->data, 1, SYS_FOREVER_US);
  if (err) {
    LOG_ERR("Cannot enable uart reception (err: %d)", err);
    /* Free the rx buffer only because the tx buffer will be handled in the callback */
    k_free(rx);
  }

  return err;
}


void uart_send_ext(uart_data_t *tx)
{
  k_fifo_put(&fifo_uart_rx_data, tx);
}

uart_data_t *uart_get_data_ext(void)
{
  return k_fifo_get(&fifo_uart_rx_data, K_FOREVER);
}

uart_data_t *uart_get_data_int(void)
{
  return k_fifo_get(&fifo_uart_rx_data_int, K_NO_WAIT);
}

uart_data_t *uart_get_data_pb(void)
{
  return k_fifo_get(&fifo_uart_rx_data_pb, K_MSEC(100));
}

void uart_data_pb_flush(void){
  while(uart_get_data_pb() != NULL);
}

void uart_send(uart_data_t *tx)
{
  int err = uart_tx(uart, tx->data, tx->len, SYS_FOREVER_MS);
  if (err) {
    k_fifo_put(&fifo_uart_tx_data, tx);
  }
}

