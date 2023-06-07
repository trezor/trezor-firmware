/**
 * Copyright (c) 2014 - 2021, Nordic Semiconductor ASA
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form, except as embedded into a Nordic
 *    Semiconductor ASA integrated circuit in a product or a software update for
 *    such product, must reproduce the above copyright notice, this list of
 *    conditions and the following disclaimer in the documentation and/or other
 *    materials provided with the distribution.
 *
 * 3. Neither the name of Nordic Semiconductor ASA nor the names of its
 *    contributors may be used to endorse or promote products derived from this
 *    software without specific prior written permission.
 *
 * 4. This software, with or without modification, must only be used with a
 *    Nordic Semiconductor ASA integrated circuit.
 *
 * 5. Any software provided in binary form under this license must not be
 * reverse engineered, decompiled, modified and/or disassembled.
 *
 * THIS SOFTWARE IS PROVIDED BY NORDIC SEMICONDUCTOR ASA "AS IS" AND ANY EXPRESS
 * OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 */
/** @file
 *
 * @defgroup ble_sdk_uart_over_ble_main main.c
 * @{
 * @ingroup  ble_sdk_app_nus_eval
 * @brief    UART over BLE application main file.
 *
 * This file contains the source code for a sample application that uses the
 * Nordic UART service. This application uses the @ref srvlib_conn_params
 * module.
 */

#include <stdint.h>
#include <string.h>
#include "app_scheduler.h"
#include "app_timer.h"
#include "app_uart.h"
#include "app_util_platform.h"
#include "ble_conn_params.h"
#include "ble_hci.h"
#include "nordic_common.h"
#include "nrf.h"
#include "nrf_ble_gatt.h"
#include "nrf_ble_qwr.h"
#include "nrf_drv_uart.h"
#include "nrf_gpio.h"
#include "nrf_pwr_mgmt.h"
#include "nrf_sdh.h"
#include "nrf_sdh_ble.h"
#include "nrf_sdh_soc.h"
#include "trezor_t3w1_d1_NRF.h"

#if defined(SOFTDEVICE_PRESENT) && SOFTDEVICE_PRESENT
#include "nrf_sdm.h"
#endif

#if defined(UART_PRESENT)
#include "nrf_uart.h"
#endif
#if defined(UARTE_PRESENT)
#include "nrf_uarte.h"
#endif

#include "nrf_log.h"
#include "nrf_log_ctrl.h"
#include "nrf_log_default_backends.h"

#include "advertising.h"
#include "ble_nus.h"
#include "connection.h"
#include "defs.h"
#include "dis.h"
#include "int_comm.h"
#include "nrf_ble_lesc.h"
#include "pm.h"
#include "power.h"

#define DEVICE_NAME                                                       \
  "Trezor" /**< Name of device. Will be included in the advertising data. \
            */

#define APP_BLE_OBSERVER_PRIO                                              \
  3 /**< Application's BLE observer priority. You shouldn't need to modify \
       this value. */

#define MIN_CONN_INTERVAL                                                     \
  MSEC_TO_UNITS(                                                              \
      7.5, UNIT_1_25_MS) /**< Minimum acceptable connection interval (20 ms), \
                           Connection interval uses 1.25 ms units. */
#define MAX_CONN_INTERVAL                                                     \
  MSEC_TO_UNITS(                                                              \
      7.5, UNIT_1_25_MS) /**< Maximum acceptable connection interval (75 ms), \
                           Connection interval uses 1.25 ms units. */
#define SLAVE_LATENCY 0  /**< Slave latency. */
#define CONN_SUP_TIMEOUT                                                     \
  MSEC_TO_UNITS(4000,                                                        \
                UNIT_10_MS) /**< Connection supervisory timeout (4 seconds), \
                               Supervision Timeout uses 10 ms units. */
#define FIRST_CONN_PARAMS_UPDATE_DELAY                                         \
  APP_TIMER_TICKS(                                                             \
      5000) /**< Time from initiating event (connect or start of notification) \
               to first time sd_ble_gap_conn_param_update is called (5         \
               seconds). */
#define NEXT_CONN_PARAMS_UPDATE_DELAY                                          \
  APP_TIMER_TICKS(                                                             \
      30000) /**< Time between each call to sd_ble_gap_conn_param_update after \
                the first call (30 seconds). */
#define MAX_CONN_PARAMS_UPDATE_COUNT                                  \
  3 /**< Number of attempts before giving up the connection parameter \
       negotiation. */

#define DEAD_BEEF                                                        \
  0xDEADBEEF /**< Value used as error code on stack dump, can be used to \
                identify stack location on stack unwind. */

#define UART_TX_BUF_SIZE 256 /**< UART TX buffer size. */
#define UART_RX_BUF_SIZE 256 /**< UART RX buffer size. */

NRF_BLE_GATT_DEF(m_gatt); /**< GATT module instance. */
NRF_BLE_QWR_DEF(m_qwr);   /**< Context for the Queued Write module.*/

#define SCHED_MAX_EVENT_DATA_SIZE \
  APP_TIMER_SCHED_EVENT_DATA_SIZE /**< Maximum size of scheduler events. */
#ifdef SVCALL_AS_NORMAL_FUNCTION
#define SCHED_QUEUE_SIZE                                                     \
  20 /**< Maximum number of events in the scheduler queue. More is needed in \
        case of Serialization. */
#else
#define SCHED_QUEUE_SIZE \
  10 /**< Maximum number of events in the scheduler queue. */
#endif

static uint16_t m_ble_nus_max_data_len =
    BLE_GATT_ATT_MTU_DEFAULT -
    3; /**< Maximum length of data (in bytes) that can be transmitted to the
          peer by the Nordic UART service module. */

/**@brief Function for assert macro callback.
 *
 * @details This function will be called in case of an assert in the SoftDevice.
 *
 * @warning On assert from the SoftDevice, the system can only recover on reset.
 *
 * @param[in] line_num    Line number of the failing ASSERT call.
 * @param[in] p_file_name File name of the failing ASSERT call.
 */
void assert_nrf_callback(uint16_t line_num, const uint8_t *p_file_name) {
  app_error_handler(DEAD_BEEF, line_num, p_file_name);
}

/*lint -save -e14 */
/**
 * Function is implemented as weak so that it can be overwritten by custom
 * application error handler when needed.
 */
void app_error_fault_handler(uint32_t id, uint32_t pc, uint32_t info) {
  __disable_irq();

  // signalize firmware not running
  nrf_gpio_pin_clear(GPIO_2_PIN);

  NRF_LOG_FINAL_FLUSH();

#ifndef DEBUG
  NRF_LOG_ERROR("Fatal error");
#else
  switch (id) {
#if defined(SOFTDEVICE_PRESENT) && SOFTDEVICE_PRESENT
    case NRF_FAULT_ID_SD_ASSERT:
      NRF_LOG_ERROR("SOFTDEVICE: ASSERTION FAILED");
      break;
    case NRF_FAULT_ID_APP_MEMACC:
      NRF_LOG_ERROR("SOFTDEVICE: INVALID MEMORY ACCESS");
      break;
#endif
    case NRF_FAULT_ID_SDK_ASSERT: {
      assert_info_t *p_info = (assert_info_t *)info;
      NRF_LOG_ERROR("ASSERTION FAILED at %s:%u", p_info->p_file_name,
                    p_info->line_num);
      break;
    }
    case NRF_FAULT_ID_SDK_ERROR: {
      error_info_t *p_info = (error_info_t *)info;
      NRF_LOG_ERROR("ERROR %u [%s] at %s:%u\r\nPC at: 0x%08x", p_info->err_code,
                    nrf_strerror_get(p_info->err_code), p_info->p_file_name,
                    p_info->line_num, pc);
      NRF_LOG_ERROR("End of error report");
      break;
    }
    default:
      NRF_LOG_ERROR("UNKNOWN FAULT at 0x%08X", pc);
      break;
  }
#endif

  NRF_BREAKPOINT_COND;
  // On assert, the system can only recover with a reset.

#ifndef DEBUG
  NRF_LOG_WARNING("System reset");
  NVIC_SystemReset();
#else
  app_error_save_and_stop(id, pc, info);
#endif  // DEBUG
}

/**@brief Function for initializing the timer module.
 */
static void timers_init(void) {
  ret_code_t err_code = app_timer_init();
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for the GAP initialization.
 *
 * @details This function will set up all the necessary GAP (Generic Access
 * Profile) parameters of the device. It also sets the permissions and
 * appearance.
 */
static void gap_params_init(void) {
  uint32_t err_code;
  ble_gap_conn_params_t gap_conn_params;
  ble_gap_conn_sec_mode_t sec_mode;

  BLE_GAP_CONN_SEC_MODE_SET_OPEN(&sec_mode);

  err_code = sd_ble_gap_device_name_set(&sec_mode, (const uint8_t *)DEVICE_NAME,
                                        strlen(DEVICE_NAME));
  APP_ERROR_CHECK(err_code);

  err_code = sd_ble_gap_appearance_set(BLE_APPEARANCE_UNKNOWN);
  APP_ERROR_CHECK(err_code);

  memset(&gap_conn_params, 0, sizeof(gap_conn_params));

  gap_conn_params.min_conn_interval = MIN_CONN_INTERVAL;
  gap_conn_params.max_conn_interval = MAX_CONN_INTERVAL;
  gap_conn_params.slave_latency = SLAVE_LATENCY;
  gap_conn_params.conn_sup_timeout = CONN_SUP_TIMEOUT;

  err_code = sd_ble_gap_ppcp_set(&gap_conn_params);
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for handling Queued Write Module errors.
 *
 * @details A pointer to this function will be passed to each service which may
 * need to inform the application about an error.
 *
 * @param[in]   nrf_error   Error code containing information about what went
 * wrong.
 */
static void nrf_qwr_error_handler(uint32_t nrf_error) {
  APP_ERROR_HANDLER(nrf_error);
}

/**@brief Function for initializing services that will be used by the
 * application.
 */
static void services_init(void) {
  uint32_t err_code;
  nrf_ble_qwr_init_t qwr_init = {0};

  // Initialize Queued Write Module.
  qwr_init.error_handler = nrf_qwr_error_handler;

  err_code = nrf_ble_qwr_init(&m_qwr, &qwr_init);
  APP_ERROR_CHECK(err_code);

  dis_init();
  nus_init();
}

/**@brief Function for handling errors from the Connection Parameters module.
 *
 * @param[in] nrf_error  Error code containing information about what went
 * wrong.
 */
static void conn_params_error_handler(uint32_t nrf_error) {
  APP_ERROR_HANDLER(nrf_error);
}

/**@brief Function for initializing the Connection Parameters module.
 */
static void conn_params_init(void) {
  uint32_t err_code;
  ble_conn_params_init_t cp_init;

  memset(&cp_init, 0, sizeof(cp_init));

  cp_init.p_conn_params = NULL;
  cp_init.first_conn_params_update_delay = FIRST_CONN_PARAMS_UPDATE_DELAY;
  cp_init.next_conn_params_update_delay = NEXT_CONN_PARAMS_UPDATE_DELAY;
  cp_init.max_conn_params_update_count = MAX_CONN_PARAMS_UPDATE_COUNT;
  cp_init.start_on_notify_cccd_handle = BLE_GATT_HANDLE_INVALID;
  cp_init.disconnect_on_fail = false;
  cp_init.evt_handler = NULL;
  cp_init.error_handler = conn_params_error_handler;

  err_code = ble_conn_params_init(&cp_init);
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for handling BLE events.
 *
 * @param[in]   p_ble_evt   Bluetooth stack event.
 * @param[in]   p_context   Unused.
 */
static void ble_evt_handler(ble_evt_t const *p_ble_evt, void *p_context) {
  uint32_t err_code;
  char passkey[BLE_GAP_PASSKEY_LEN + 1] = {0};

  switch (p_ble_evt->header.evt_id) {
    case BLE_GAP_EVT_CONNECTED:
      NRF_LOG_INFO("Connected");
      //      err_code = bsp_indication_set(BSP_INDICATE_CONNECTED);
      //      APP_ERROR_CHECK(err_code);

      uint16_t handle = p_ble_evt->evt.gap_evt.conn_handle;
      set_connection_handle(handle);
      send_status_event();
      err_code = nrf_ble_qwr_conn_handle_assign(&m_qwr, handle);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_GAP_EVT_DISCONNECTED:
      NRF_LOG_INFO("Disconnected");
      //      bsp_indication_set(BSP_INDICATE_IDLE);
      set_connection_handle(BLE_CONN_HANDLE_INVALID);
      send_status_event();
      break;

    case BLE_GAP_EVT_PHY_UPDATE_REQUEST: {
      NRF_LOG_DEBUG("PHY update request.");
      ble_gap_phys_t const phys = {
          .rx_phys = BLE_GAP_PHY_AUTO,
          .tx_phys = BLE_GAP_PHY_AUTO,
      };
      err_code =
          sd_ble_gap_phy_update(p_ble_evt->evt.gap_evt.conn_handle, &phys);
      APP_ERROR_CHECK(err_code);
    } break;

    case BLE_GAP_EVT_PASSKEY_DISPLAY:
      memcpy(passkey, p_ble_evt->evt.gap_evt.params.passkey_display.passkey,
             BLE_GAP_PASSKEY_LEN);

      NRF_LOG_INFO("BLE_GAP_EVT_PASSKEY_DISPLAY: passkey=%s match_req=%d",
                   nrf_log_push(passkey),
                   p_ble_evt->evt.gap_evt.params.passkey_display.match_request);

      if (p_ble_evt->evt.gap_evt.params.passkey_display.match_request) {
        bool ok =
            send_comparison_request((uint8_t *)passkey, BLE_GAP_PASSKEY_LEN);

        if (ok) {
          sd_ble_gap_auth_key_reply(p_ble_evt->evt.gap_evt.conn_handle,
                                    BLE_GAP_AUTH_KEY_TYPE_PASSKEY, NULL);
        } else {
          sd_ble_gap_auth_key_reply(p_ble_evt->evt.gap_evt.conn_handle,
                                    BLE_GAP_AUTH_KEY_TYPE_NONE, NULL);
        }
      }
      break;
    case BLE_GAP_EVT_LESC_DHKEY_REQUEST:
      NRF_LOG_INFO("BLE_GAP_EVT_LESC_DHKEY_REQUEST");
      break;

    case BLE_GAP_EVT_AUTH_KEY_REQUEST: {
      NRF_LOG_INFO("Key requested.");

      bool ok = send_auth_key_request((uint8_t *)passkey, BLE_GAP_PASSKEY_LEN);

      sd_ble_gap_auth_key_reply(p_ble_evt->evt.gap_evt.conn_handle,
                                BLE_GAP_AUTH_KEY_TYPE_PASSKEY,
                                (uint8_t *)passkey);

      if (ok) {
        NRF_LOG_INFO("Received data: %c", passkey);
      } else {
        NRF_LOG_INFO("Auth key request failed.");
      }

      // APP_ERROR_CHECK(err_code);
      break;
    }
    case BLE_GATTC_EVT_TIMEOUT:
      // Disconnect on GATT Client timeout event.
      err_code =
          sd_ble_gap_disconnect(p_ble_evt->evt.gattc_evt.conn_handle,
                                BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_GATTS_EVT_TIMEOUT:
      // Disconnect on GATT Server timeout event.
      err_code =
          sd_ble_gap_disconnect(p_ble_evt->evt.gatts_evt.conn_handle,
                                BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
      APP_ERROR_CHECK(err_code);
      break;

    default:
      // No implementation needed.
      break;
  }
}

/**@brief Function for the SoftDevice initialization.
 *
 * @details This function initializes the SoftDevice and the BLE event
 * interrupt.
 */
static void ble_stack_init(void) {
  ret_code_t err_code;

  err_code = nrf_sdh_enable_request();
  APP_ERROR_CHECK(err_code);

  // Configure the BLE stack using the default settings.
  // Fetch the start address of the application RAM.
  uint32_t ram_start = 0;
  err_code = nrf_sdh_ble_default_cfg_set(APP_BLE_CONN_CFG_TAG, &ram_start);
  APP_ERROR_CHECK(err_code);

  // Enable BLE stack.
  err_code = nrf_sdh_ble_enable(&ram_start);
  APP_ERROR_CHECK(err_code);

  // Register a handler for BLE events.
  NRF_SDH_BLE_OBSERVER(m_ble_observer, APP_BLE_OBSERVER_PRIO, ble_evt_handler,
                       NULL);
}

/**@brief Function for handling events from the GATT library. */
void gatt_evt_handler(nrf_ble_gatt_t *p_gatt, nrf_ble_gatt_evt_t const *p_evt) {
  if ((get_connection_handle() == p_evt->conn_handle) &&
      (p_evt->evt_id == NRF_BLE_GATT_EVT_ATT_MTU_UPDATED)) {
    m_ble_nus_max_data_len =
        p_evt->params.att_mtu_effective - OPCODE_LENGTH - HANDLE_LENGTH;
    NRF_LOG_INFO("Data len is set to 0x%X(%d)", m_ble_nus_max_data_len,
                 m_ble_nus_max_data_len);
  }
  NRF_LOG_DEBUG("ATT MTU exchange completed. central 0x%x peripheral 0x%x",
                p_gatt->att_mtu_desired_central,
                p_gatt->att_mtu_desired_periph);
}

/**@brief Function for initializing the GATT library. */
void gatt_init(void) {
  ret_code_t err_code;

  err_code = nrf_ble_gatt_init(&m_gatt, gatt_evt_handler);
  APP_ERROR_CHECK(err_code);

  err_code =
      nrf_ble_gatt_att_mtu_periph_set(&m_gatt, NRF_SDH_BLE_GATT_MAX_MTU_SIZE);
  APP_ERROR_CHECK(err_code);
}

///**@brief Function for handling events from the BSP module.
// *
// * @param[in]   event   Event generated by button press.
// */
// void bsp_event_handler(bsp_event_t event) {
//  uint32_t err_code;
//  switch (event) {
//    case BSP_EVENT_SLEEP:
//      sleep_mode_enter();
//      break;
//
//    case BSP_EVENT_DISCONNECT:
//      err_code = sd_ble_gap_disconnect(
//          get_connection_handle(), BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
//      if (err_code != NRF_ERROR_INVALID_STATE) {
//        APP_ERROR_CHECK(err_code);
//      }
//      break;
//
//    case BSP_EVENT_WHITELIST_OFF:
//      if (get_connection_handle() == BLE_CONN_HANDLE_INVALID) {
//        advertising_restart_without_whitelist();
//      }
//      break;
//
//    default:
//      break;
//  }
//}

/**@brief  Function for initializing the UART module.
 */
/**@snippet [UART Initialization] */
static void uart_init(void) {
  uint32_t err_code;
  app_uart_comm_params_t const comm_params = {
    .rx_pin_no = RX_PIN_NUMBER,
    .tx_pin_no = TX_PIN_NUMBER,
    .rts_pin_no = RTS_PIN_NUMBER,
    .cts_pin_no = CTS_PIN_NUMBER,
    .flow_control = APP_UART_FLOW_CONTROL_ENABLED,
    .use_parity = false,
#if defined(UART_PRESENT)
    .baud_rate = NRF_UART_BAUDRATE_1000000
#else
    .baud_rate = NRF_UARTE_BAUDRATE_1000000
#endif
  };

  APP_UART_FIFO_INIT(&comm_params, UART_RX_BUF_SIZE, UART_TX_BUF_SIZE,
                     uart_event_handle, APP_IRQ_PRIORITY_LOWEST, err_code);
  APP_ERROR_CHECK(err_code);
}
/**@snippet [UART Initialization] */

///**@brief Function for initializing buttons and leds.
// *
// * @param[out] p_erase_bonds  Will be true if the clear bonding button was
// * pressed to wake the application up.
// */
// static void buttons_leds_init(bool *p_erase_bonds) {
//  bsp_event_t startup_event;
//
//  uint32_t err_code =
//      bsp_init(BSP_INIT_LEDS | BSP_INIT_BUTTONS, bsp_event_handler);
//  APP_ERROR_CHECK(err_code);
//
//  err_code = bsp_btn_ble_init(NULL, &startup_event);
//  APP_ERROR_CHECK(err_code);
//
//  *p_erase_bonds = (startup_event == BSP_EVENT_CLEAR_BONDING_DATA);
//}

/**@brief Function for initializing the nrf log module.
 */
static void log_init(void) {
  ret_code_t err_code = NRF_LOG_INIT(NULL);
  APP_ERROR_CHECK(err_code);

  NRF_LOG_DEFAULT_BACKENDS_INIT();
}

/**@brief Function for initializing power management.
 */
static void power_management_init(void) {
  ret_code_t err_code;
  err_code = nrf_pwr_mgmt_init();
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for handling the idle state (main loop).
 *
 * @details If there is no pending log operation, then sleep until next the next
 * event occurs.
 */
static void idle_state_handle(void) {
  app_sched_execute();
  if (NRF_LOG_PROCESS() == false) {
    nrf_pwr_mgmt_run();
  }
}

/**@brief Function for the Event Scheduler initialization.
 */
static void scheduler_init(void) {
  APP_SCHED_INIT(SCHED_MAX_EVENT_DATA_SIZE, SCHED_QUEUE_SIZE);
}

/**@brief Application main function.
 */
int main(void) {
  bool erase_bonds = false;

  nrf_gpio_cfg_output(GPIO_1_PIN);
  nrf_gpio_cfg_output(GPIO_2_PIN);
  nrf_gpio_pin_clear(GPIO_1_PIN);

  // Initialize.
  spi_init();
  uart_init();
  log_init();
  timers_init();
  // buttons_leds_init(&erase_bonds);
  power_management_init();
  ble_stack_init();
  scheduler_init();
  gap_params_init();
  gatt_init();
  services_init();
  advertising_init();
  conn_params_init();
  peer_manager_init();

  // signalize firmware running
  nrf_gpio_pin_set(GPIO_2_PIN);
  send_status_event();

  if (erase_bonds) {
    delete_bonds();
  }

  // Enter main loop.
  for (;;) {
    nrf_ble_lesc_request_handler();
    idle_state_handle();
  }
}

/**
 * @}
 */
