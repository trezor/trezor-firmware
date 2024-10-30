#include <zephyr/types.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>

#include <dk_buttons_and_leds.h>

#include <zephyr/settings/settings.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/crc.h>

#include "uart.h"
#include "int_comm.h"
#include "int_comm_defs.h"
#include "events.h"

#define LOG_MODULE_NAME fw_uart
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define UART_WAIT_FOR_BUF_DELAY K_MSEC(50)
#define UART_WAIT_FOR_RX CONFIG_BT_NUS_UART_RX_WAIT_TIME

static const struct device *uart = DEVICE_DT_GET(DT_CHOSEN(nordic_nus_uart));

static K_FIFO_DEFINE(fifo_uart_tx_data);
static K_FIFO_DEFINE(fifo_uart_rx_data);
static K_FIFO_DEFINE(fifo_uart_rx_data_int);


static struct k_work_delayable uart_work;



static volatile bool g_uart_rx_running = false;


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
  static uint8_t crc = 0;

  switch (evt->type) {
    case UART_TX_DONE:
      LOG_DBG("UART_TX_DONE");


      if (evt->data.tx.buf == NULL) {
        return;
      }

      if (evt->data.tx.len == 0) {
        buf = CONTAINER_OF(evt->data.tx.buf, uart_data_t, data);

      	LOG_DBG("Free uart data");
      	k_free(buf);
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

      LOG_DBG("Free uart data");
      k_free(buf);

      buf = k_fifo_get(&fifo_uart_tx_data, K_NO_WAIT);
      if (!buf) {
        return;
      }

      if (!uart_tx(uart, buf->data, buf->len, SYS_FOREVER_MS)) {
        LOG_WRN("FREE: Failed to send data over UART");
      }

      break;

    case UART_RX_RDY:
//      LOG_WRN("UART_RX_RDY");
      buf = CONTAINER_OF(evt->data.rx.buf, uart_data_t, data);
      buf->len += evt->data.rx.len;

      switch(rx_phase) {
        case 0:
          if (buf->len == 1 && (buf->data[0] == INTERNAL_EVENT || buf->data[0] == EXTERNAL_MESSAGE) ) {
            rx_phase = 1;
            rx_msg_type = buf->data[0];
            crc = crc8(buf->data, buf->len, 0x07, 0x00, false);
          } else {
            rx_phase = 0;
          }
          break;
        case 1:
          if (buf->len == 1) {
            rx_data_len = buf->data[0];
            crc = crc8(buf->data, buf->len, 0x07, crc, false);
            rx_phase = 2;
          } else{
            rx_phase = 0;
          }
          break;
        case 2:
          if (buf->len != rx_data_len - COMM_HEADER_SIZE) {
            rx_phase = 0;
          }

          crc = crc8(buf->data, buf->len - 1, 0x07, crc, false);

          if (crc != buf->data[buf->len - 1]) {
            LOG_WRN("UART_RX CRC ERROR");
            rx_phase = 0;
          }

          rx_phase = 3;
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

      LOG_DBG("UART_RX_MALLOC");
      buf = k_malloc(sizeof(*buf));

      if (buf) {

        switch (rx_phase) {
          case 0:
            rx_len = 1;
            break;
          case 1:
            rx_len = 1;
            break;
          case 2:
            rx_len = rx_data_len - COMM_HEADER_SIZE;
            break;

          default:
            rx_len = 1;
            break;
        }

        buf->len = 0;
        uart_rx_enable(uart, buf->data, rx_len, SYS_FOREVER_US);
      } else {
        LOG_WRN("Not able to allocate UART receive buffer");
        k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
        g_uart_rx_running = false;
      }

//		buf = k_malloc(sizeof(*buf));
//		if (buf) {
//			buf->len = 0;
//		} else {
//			LOG_WRN("Not able to allocate UART receive buffer");
//
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
        buf->len -= COMM_FOOTER_SIZE;
        if (rx_msg_type == EXTERNAL_MESSAGE) {
          k_fifo_put(&fifo_uart_rx_data, buf);
        }
        else  if (rx_msg_type == INTERNAL_EVENT) {
          k_fifo_put(&fifo_uart_rx_data_int, buf);
        } else {
      		//LOG_WRN("UART_RX BAD MASSAGE TYPE");
          k_free(buf);
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


int uart_start_rx(void) {
  int err;
  uart_data_t *rx;

  rx = k_malloc(sizeof(*rx));
  if (rx) {
    rx->len = 0;
  } else {
    return -ENOMEM;
  }

  // receive message type
  err = uart_rx_enable(uart, rx->data, 1, SYS_FOREVER_US);
  if (err) {
    LOG_ERR("Cannot enable uart reception (err: %d)", err);
    /* Free the rx buffer only because the tx buffer will be handled in the callback */
    k_free(rx);
  } else {
    g_uart_rx_running = true;
  }

  return err;
}

static void uart_work_handler(struct k_work *item)
{
	uart_data_t *buf;

	buf = k_malloc(sizeof(*buf));
	if (buf) {
		buf->len = 0;
	} else {
		LOG_WRN("Not able to allocate UART receive buffer");
		k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
		return;
	}

	uart_rx_enable(uart, buf->data, 1, SYS_FOREVER_US);
}


int uart_init(void)
{
  int err;


  if (!device_is_ready(uart)) {
    return -ENODEV;
  }


  k_work_init_delayable(&uart_work, uart_work_handler);

  struct uart_config cfg = {
          .baudrate = 1000000,
          .parity = UART_CFG_PARITY_NONE,
          .stop_bits = UART_CFG_STOP_BITS_1,
          .data_bits = UART_CFG_DATA_BITS_8,
          .flow_ctrl = UART_CFG_FLOW_CTRL_RTS_CTS,

  };

  uart_configure(uart, &cfg);

  err = uart_callback_set(uart, uart_cb, NULL);
  if (err) {
    LOG_ERR("Cannot initialize UART callback");
    return err;
  }

  return uart_start_rx();
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
  return k_fifo_get(&fifo_uart_rx_data_int, K_FOREVER);
}
//
//uart_data_t *uart_get_data_pb(void)
//{
//  return k_fifo_get(&fifo_uart_rx_data_pb, K_MSEC(100));
//}
//
//void uart_data_pb_flush(void){
//  while(uart_get_data_pb() != NULL);
//}

void uart_send(uart_data_t *tx)
{
  int err = uart_tx(uart, tx->data, tx->len, SYS_FOREVER_MS);
  if (err) {
    k_fifo_put(&fifo_uart_tx_data, tx);
  }
}

