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
#include "ble_advdata.h"
#include "ble_advertising.h"
#include "ble_conn_params.h"
#include "ble_hci.h"
#include "ble_nus.h"
#include "bsp_btn_ble.h"
#include "nordic_common.h"
#include "nrf.h"
#include "nrf_ble_gatt.h"
#include "nrf_ble_qwr.h"
#include "nrf_drv_spi.h"
#include "nrf_pwr_mgmt.h"
#include "nrf_sdh.h"
#include "nrf_sdh_ble.h"
#include "nrf_sdh_soc.h"
#include "peer_manager.h"
#include "peer_manager_handler.h"

#if defined(UART_PRESENT)
#include "nrf_uart.h"
#endif
#if defined(UARTE_PRESENT)
#include "nrf_uarte.h"
#endif

#include "nrf_log.h"
#include "nrf_log_ctrl.h"
#include "nrf_log_default_backends.h"

#include "dis.h"
#include "int_comm.h"

#define APP_BLE_CONN_CFG_TAG \
  1 /**< A tag identifying the SoftDevice BLE configuration. */

#define DEVICE_NAME                                                       \
  "Trezor" /**< Name of device. Will be included in the advertising data. \
            */
#define NUS_SERVICE_UUID_TYPE                                           \
  BLE_UUID_TYPE_VENDOR_BEGIN /**< UUID type for the Nordic UART Service \
                                (vendor specific). */

#define APP_BLE_OBSERVER_PRIO                                              \
  3 /**< Application's BLE observer priority. You shouldn't need to modify \
       this value. */

#define APP_ADV_INTERVAL                                             \
  64 /**< The advertising interval (in units of 0.625 ms. This value \
        corresponds to 40 ms). */

#define APP_ADV_DURATION                                           \
  18000 /**< The advertising duration (180 seconds) in units of 10 \
           milliseconds. */

#define MIN_CONN_INTERVAL                                                    \
  MSEC_TO_UNITS(                                                             \
      20, UNIT_1_25_MS) /**< Minimum acceptable connection interval (20 ms), \
                           Connection interval uses 1.25 ms units. */
#define MAX_CONN_INTERVAL                                                    \
  MSEC_TO_UNITS(                                                             \
      75, UNIT_1_25_MS) /**< Maximum acceptable connection interval (75 ms), \
                           Connection interval uses 1.25 ms units. */
#define SLAVE_LATENCY 0 /**< Slave latency. */
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

NRF_BLE_GATT_DEF(m_gatt);           /**< GATT module instance. */
NRF_BLE_QWR_DEF(m_qwr);             /**< Context for the Queued Write module.*/
BLE_ADVERTISING_DEF(m_advertising); /**< Advertising module instance. */

#define SEC_PARAM_BOND 1     /**< Perform bonding. */
#define SEC_PARAM_MITM 0     /**< Man In The Middle protection not required. */
#define SEC_PARAM_LESC 0     /**< LE Secure Connections not enabled. */
#define SEC_PARAM_KEYPRESS 0 /**< Keypress notifications not enabled. */
#define SEC_PARAM_IO_CAPABILITIES \
  BLE_GAP_IO_CAPS_KEYBOARD_DISPLAY /**< No I/O capabilities. */
#define SEC_PARAM_OOB 0            /**< Out Of Band data not available. */
#define SEC_PARAM_MIN_KEY_SIZE 7   /**< Minimum encryption key size. */
#define SEC_PARAM_MAX_KEY_SIZE 16  /**< Maximum encryption key size. */

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

static pm_peer_id_t
    m_peer_id; /**< Device reference handle to the current bonded central. */
static uint16_t m_conn_handle =
    BLE_CONN_HANDLE_INVALID; /**< Handle of the current connection. */
static uint16_t m_ble_nus_max_data_len =
    BLE_GATT_ATT_MTU_DEFAULT -
    3; /**< Maximum length of data (in bytes) that can be transmitted to the
          peer by the Nordic UART service module. */
static ble_uuid_t m_adv_uuids[] = /**< Universally unique service identifier. */
    {{BLE_UUID_NUS_SERVICE, NUS_SERVICE_UUID_TYPE}};

/**@brief Function for assert macro callback.
 *
 * @details This function will be called in case of an assert in the SoftDevice.
 *
 * @warning This handler is an example only and does not fit a final product.
 * You need to analyse how your product is supposed to react in case of Assert.
 * @warning On assert from the SoftDevice, the system can only recover on reset.
 *
 * @param[in] line_num    Line number of the failing ASSERT call.
 * @param[in] p_file_name File name of the failing ASSERT call.
 */
void assert_nrf_callback(uint16_t line_num, const uint8_t *p_file_name) {
  app_error_handler(DEAD_BEEF, line_num, p_file_name);
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
  nus_init(&m_conn_handle);
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

/**@brief Function for putting the chip into sleep mode.
 *
 * @note This function will not return.
 */
static void sleep_mode_enter(void) {
  uint32_t err_code = bsp_indication_set(BSP_INDICATE_IDLE);
  APP_ERROR_CHECK(err_code);

  // Prepare wakeup buttons.
  err_code = bsp_btn_ble_sleep_mode_prepare();
  APP_ERROR_CHECK(err_code);

  // Go to system-off mode (this function will not return; wakeup will cause a
  // reset).
  err_code = sd_power_system_off();
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for setting filtered device identities.
 *
 * @param[in] skip  Filter passed to @ref pm_peer_id_list.
 */
static void identities_set(pm_peer_id_list_skip_t skip) {
  pm_peer_id_t peer_ids[BLE_GAP_DEVICE_IDENTITIES_MAX_COUNT];
  uint32_t peer_id_count = BLE_GAP_DEVICE_IDENTITIES_MAX_COUNT;

  ret_code_t err_code =
      pm_peer_id_list(peer_ids, &peer_id_count, PM_PEER_ID_INVALID, skip);
  APP_ERROR_CHECK(err_code);

  err_code = pm_device_identities_list_set(peer_ids, peer_id_count);
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for handling advertising events.
 *
 * @details This function will be called for advertising events which are passed
 * to the application.
 *
 * @param[in] ble_adv_evt  Advertising event.
 */
static void on_adv_evt(ble_adv_evt_t ble_adv_evt) {
  uint32_t err_code;

  switch (ble_adv_evt) {
    case BLE_ADV_EVT_DIRECTED_HIGH_DUTY:
      NRF_LOG_INFO("High Duty Directed advertising.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_DIRECTED);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_DIRECTED:
      NRF_LOG_INFO("Directed advertising.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_DIRECTED);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_FAST:
      NRF_LOG_INFO("Fast advertising.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_SLOW:
      NRF_LOG_INFO("Slow advertising.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_SLOW);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_FAST_WHITELIST:
      NRF_LOG_INFO("Fast advertising with whitelist.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_WHITELIST);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_SLOW_WHITELIST:
      NRF_LOG_INFO("Slow advertising with whitelist.");
      err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_WHITELIST);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_IDLE:
      sleep_mode_enter();
      break;

    case BLE_ADV_EVT_WHITELIST_REQUEST: {
      ble_gap_addr_t whitelist_addrs[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
      ble_gap_irk_t whitelist_irks[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
      uint32_t addr_cnt = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;
      uint32_t irk_cnt = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;

      err_code = pm_whitelist_get(whitelist_addrs, &addr_cnt, whitelist_irks,
                                  &irk_cnt);
      APP_ERROR_CHECK(err_code);
      NRF_LOG_DEBUG(
          "pm_whitelist_get returns %d addr in whitelist and %d irk whitelist",
          addr_cnt, irk_cnt);

      // Set the correct identities list (no excluding peers with no Central
      // Address Resolution).
      identities_set(PM_PEER_ID_LIST_SKIP_NO_IRK);

      // Apply the whitelist.
      err_code = ble_advertising_whitelist_reply(
          &m_advertising, whitelist_addrs, addr_cnt, whitelist_irks, irk_cnt);
      APP_ERROR_CHECK(err_code);
    } break;  // BLE_ADV_EVT_WHITELIST_REQUEST

    case BLE_ADV_EVT_PEER_ADDR_REQUEST: {
      pm_peer_data_bonding_t peer_bonding_data;

      // Only Give peer address if we have a handle to the bonded peer.
      if (m_peer_id != PM_PEER_ID_INVALID) {
        err_code = pm_peer_data_bonding_load(m_peer_id, &peer_bonding_data);
        if (err_code != NRF_ERROR_NOT_FOUND) {
          APP_ERROR_CHECK(err_code);

          // Manipulate identities to exclude peers with no Central Address
          // Resolution.
          identities_set(PM_PEER_ID_LIST_SKIP_ALL);

          ble_gap_addr_t *p_peer_addr =
              &(peer_bonding_data.peer_ble_id.id_addr_info);
          err_code =
              ble_advertising_peer_addr_reply(&m_advertising, p_peer_addr);
          APP_ERROR_CHECK(err_code);
        }
      }
    } break;  // BLE_ADV_EVT_PEER_ADDR_REQUEST

    default:
      break;
  }
}

/**@brief Function for handling BLE events.
 *
 * @param[in]   p_ble_evt   Bluetooth stack event.
 * @param[in]   p_context   Unused.
 */
static void ble_evt_handler(ble_evt_t const *p_ble_evt, void *p_context) {
  uint32_t err_code;

  switch (p_ble_evt->header.evt_id) {
    case BLE_GAP_EVT_CONNECTED:
      NRF_LOG_INFO("Connected");
      err_code = bsp_indication_set(BSP_INDICATE_CONNECTED);
      APP_ERROR_CHECK(err_code);

      send_connected_event();
      m_conn_handle = p_ble_evt->evt.gap_evt.conn_handle;
      err_code = nrf_ble_qwr_conn_handle_assign(&m_qwr, m_conn_handle);
      APP_ERROR_CHECK(err_code);
      break;

    case BLE_GAP_EVT_DISCONNECTED:
      NRF_LOG_INFO("Disconnected");
      // LED indication will be changed when advertising starts.
      send_disconnected_event();
      m_conn_handle = BLE_CONN_HANDLE_INVALID;
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

    case BLE_GAP_EVT_AUTH_KEY_REQUEST: {
      NRF_LOG_INFO("Key requested.");

      uint8_t p_key[6] = {0};

      bool ok = send_auth_key_request(p_key, sizeof(p_key));

      if (ok) {
        NRF_LOG_INFO("Received data: %c", p_key);
        err_code =
            sd_ble_gap_auth_key_reply(p_ble_evt->evt.gap_evt.conn_handle,
                                      BLE_GAP_AUTH_KEY_TYPE_PASSKEY, p_key);
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
  if ((m_conn_handle == p_evt->conn_handle) &&
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

/**@brief Function for handling events from the BSP module.
 *
 * @param[in]   event   Event generated by button press.
 */
void bsp_event_handler(bsp_event_t event) {
  uint32_t err_code;
  switch (event) {
    case BSP_EVENT_SLEEP:
      sleep_mode_enter();
      break;

    case BSP_EVENT_DISCONNECT:
      err_code = sd_ble_gap_disconnect(
          m_conn_handle, BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
      if (err_code != NRF_ERROR_INVALID_STATE) {
        APP_ERROR_CHECK(err_code);
      }
      break;

    case BSP_EVENT_WHITELIST_OFF:
      if (m_conn_handle == BLE_CONN_HANDLE_INVALID) {
        err_code = ble_advertising_restart_without_whitelist(&m_advertising);
        if (err_code != NRF_ERROR_INVALID_STATE) {
          APP_ERROR_CHECK(err_code);
        }
      }
      break;

    default:
      break;
  }
}

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

static void advertising_init(void) {
  uint32_t err_code;
  uint8_t adv_flags;
  ble_advertising_init_t init;

  memset(&init, 0, sizeof(init));

  adv_flags = BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE;
  init.advdata.name_type = BLE_ADVDATA_FULL_NAME;
  init.advdata.include_appearance = true;
  init.advdata.flags = adv_flags;
  init.advdata.uuids_complete.uuid_cnt =
      sizeof(m_adv_uuids) / sizeof(m_adv_uuids[0]);
  init.advdata.uuids_complete.p_uuids = m_adv_uuids;

  init.config.ble_adv_whitelist_enabled = true;
  init.config.ble_adv_directed_high_duty_enabled = true;
  init.config.ble_adv_directed_enabled = false;
  init.config.ble_adv_directed_interval = 0;
  init.config.ble_adv_directed_timeout = 0;
  init.config.ble_adv_fast_enabled = true;
  init.config.ble_adv_fast_interval = APP_ADV_INTERVAL;
  init.config.ble_adv_fast_timeout = APP_ADV_DURATION;

  init.evt_handler = on_adv_evt;

  err_code = ble_advertising_init(&m_advertising, &init);
  APP_ERROR_CHECK(err_code);

  ble_advertising_conn_cfg_tag_set(&m_advertising, APP_BLE_CONN_CFG_TAG);
}

/**@brief Function for initializing buttons and leds.
 *
 * @param[out] p_erase_bonds  Will be true if the clear bonding button was
 * pressed to wake the application up.
 */
static void buttons_leds_init(bool *p_erase_bonds) {
  bsp_event_t startup_event;

  uint32_t err_code =
      bsp_init(BSP_INIT_LEDS | BSP_INIT_BUTTONS, bsp_event_handler);
  APP_ERROR_CHECK(err_code);

  err_code = bsp_btn_ble_init(NULL, &startup_event);
  APP_ERROR_CHECK(err_code);

  *p_erase_bonds = (startup_event == BSP_EVENT_CLEAR_BONDING_DATA);
}

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

/**@brief Function for setting filtered whitelist.
 *
 * @param[in] skip  Filter passed to @ref pm_peer_id_list.
 */
static void whitelist_set(pm_peer_id_list_skip_t skip) {
  pm_peer_id_t peer_ids[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
  uint32_t peer_id_count = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;

  ret_code_t err_code =
      pm_peer_id_list(peer_ids, &peer_id_count, PM_PEER_ID_INVALID, skip);
  APP_ERROR_CHECK(err_code);

  NRF_LOG_INFO("\tm_whitelist_peer_cnt %d, MAX_PEERS_WLIST %d",
               peer_id_count + 1, BLE_GAP_WHITELIST_ADDR_MAX_COUNT);

  err_code = pm_whitelist_set(peer_ids, peer_id_count);
  APP_ERROR_CHECK(err_code);
}

///**@brief Clear bond information from persistent storage. */
static void delete_bonds(void) {
  ret_code_t err_code;

  NRF_LOG_INFO("Erase bonds!");

  err_code = pm_peers_delete();
  APP_ERROR_CHECK(err_code);
}

static void advertising_start(bool erase_bonds) {
  if (erase_bonds == true) {
    delete_bonds();
    // Advertising is started by PM_EVT_PEERS_DELETE_SUCCEEDED event.
  } else {
    whitelist_set(PM_PEER_ID_LIST_SKIP_NO_ID_ADDR);

    ret_code_t ret = ble_advertising_start(&m_advertising, BLE_ADV_MODE_FAST);
    APP_ERROR_CHECK(ret);
  }
}

/**@brief Function for handling Peer Manager events.
 *
 * @param[in] p_evt  Peer Manager event.
 */
static void pm_evt_handler(pm_evt_t const *p_evt) {
  pm_handler_on_pm_evt(p_evt);
  pm_handler_disconnect_on_sec_failure(p_evt);
  pm_handler_flash_clean(p_evt);

  switch (p_evt->evt_id) {
    case PM_EVT_CONN_SEC_SUCCEEDED:
      m_peer_id = p_evt->peer_id;
      break;

    case PM_EVT_PEERS_DELETE_SUCCEEDED:
      advertising_start(false);
      break;

    case PM_EVT_PEER_DATA_UPDATE_SUCCEEDED:
      if (p_evt->params.peer_data_update_succeeded.flash_changed &&
          (p_evt->params.peer_data_update_succeeded.data_id ==
           PM_PEER_DATA_ID_BONDING)) {
        NRF_LOG_INFO("New Bond, add the peer to the whitelist if possible");
        // Note: You should check on what kind of white list policy your
        // application should use.

        whitelist_set(PM_PEER_ID_LIST_SKIP_NO_ID_ADDR);
      }
      break;
    case PM_EVT_CONN_SEC_CONFIG_REQ: {
      bool ok = send_repair_request();

      if (ok) {
        // Allow pairing request from an already bonded peer.
        pm_conn_sec_config_t conn_sec_config = {.allow_repairing = true};
        pm_conn_sec_config_reply(p_evt->conn_handle, &conn_sec_config);
      } else {
        // Reject pairing request from an already bonded peer.
        pm_conn_sec_config_t conn_sec_config = {.allow_repairing = false};
        pm_conn_sec_config_reply(p_evt->conn_handle, &conn_sec_config);
      }

    } break;
    default:
      break;
  }
}

/**@brief Function for the Peer Manager initialization.
 */
static void peer_manager_init(void) {
  ble_gap_sec_params_t sec_param;
  ret_code_t err_code;

  err_code = pm_init();
  APP_ERROR_CHECK(err_code);

  memset(&sec_param, 0, sizeof(ble_gap_sec_params_t));

  // Security parameters to be used for all security procedures.
  sec_param.bond = SEC_PARAM_BOND;
  sec_param.mitm = SEC_PARAM_MITM;
  sec_param.lesc = SEC_PARAM_LESC;
  sec_param.keypress = SEC_PARAM_KEYPRESS;
  sec_param.io_caps = SEC_PARAM_IO_CAPABILITIES;
  sec_param.oob = SEC_PARAM_OOB;
  sec_param.min_key_size = SEC_PARAM_MIN_KEY_SIZE;
  sec_param.max_key_size = SEC_PARAM_MAX_KEY_SIZE;
  sec_param.kdist_own.enc = 1;
  sec_param.kdist_own.id = 1;
  sec_param.kdist_peer.enc = 1;
  sec_param.kdist_peer.id = 1;

  err_code = pm_sec_params_set(&sec_param);
  APP_ERROR_CHECK(err_code);

  err_code = pm_register(pm_evt_handler);
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for the Event Scheduler initialization.
 */
static void scheduler_init(void) {
  APP_SCHED_INIT(SCHED_MAX_EVENT_DATA_SIZE, SCHED_QUEUE_SIZE);
}

/**@brief Application main function.
 */
int main(void) {
  bool erase_bonds;

  // Initialize.
  spi_init();
  uart_init();
  log_init();
  timers_init();
  buttons_leds_init(&erase_bonds);
  power_management_init();
  ble_stack_init();
  scheduler_init();
  gap_params_init();
  gatt_init();
  services_init();
  advertising_init();
  conn_params_init();
  peer_manager_init();

  // Start execution.
  advertising_start(erase_bonds);

  send_initialized();

  // Enter main loop.
  for (;;) {
    idle_state_handle();
  }
}

/**
 * @}
 */
