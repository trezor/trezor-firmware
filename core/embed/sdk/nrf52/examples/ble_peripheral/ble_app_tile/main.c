/**
 * Copyright (c) 2019 - 2021, Nordic Semiconductor ASA
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
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
 * 5. Any software provided in binary form under this license must not be reverse
 *    engineered, decompiled, modified and/or disassembled.
 *
 * THIS SOFTWARE IS PROVIDED BY NORDIC SEMICONDUCTOR ASA "AS IS" AND ANY EXPRESS
 * OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
 * GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */
/** @example examples/ble_peripheral/ble_app_tile/main.c
 *
 * @brief BLE Tile Service Sample Application main file.
 *
 * This file contains the source code for a sample application using the proprietary Tile service
 * (and also Battery and Device Information services). This application uses the
 * @ref srvlib_conn_params module.
 */

#include <stdbool.h>
#include <stdint.h>
#include "nordic_common.h"
#include "bsp.h"
#include "nrf_soc.h"
#include "ble_advdata.h"
#include "ble_conn_params.h"
#include "nrf_sdh.h"
#include "nrf_sdh_ble.h"
#include "nrf_sdh_soc.h"
#include "app_timer.h"


#include "nrf_pwr_mgmt.h"
#include "nrf_ble_gatt.h"

#include "nrf_log.h"
#include "nrf_log_ctrl.h"
#include "nrf_log_default_backends.h"

// TileLib include
#include "tile_service/tile_service.h"
#include "tile_features/tile_features.h"
#include "tile_config.h"
#include "tile_gap_driver.h"

#define APP_BLE_OBSERVER_PRIO     3                                      /**< Application's BLE observer priority. You shouldn't need to modify this value. */
#define APP_BLE_CONN_CFG_TAG      1                                      /**< A tag identifying the SoftDevice BLE configuration. */

#define APP_ADV_INTERVAL          64                                     /**< The advertising interval (in units of 0.625 ms. This value corresponds to 187.5 ms). */
#define APP_ADV_DURATION          BLE_GAP_ADV_TIMEOUT_GENERAL_UNLIMITED  /**< The advertising duration in units of 10 milliseconds. */

#define DEVICE_NAME                    "Nordic_Tile"                    /**< Name of device. Will be included in the advertising data. */

#define MIN_CONN_INTERVAL              MSEC_TO_UNITS(400, UNIT_1_25_MS) /**< Minimum acceptable connection interval (0.4 seconds). */
#define MAX_CONN_INTERVAL              MSEC_TO_UNITS(650, UNIT_1_25_MS) /**< Maximum acceptable connection interval (0.65 second). */
#define SLAVE_LATENCY                  0                                /**< Slave latency. */
#define CONN_SUP_TIMEOUT               MSEC_TO_UNITS(4000, UNIT_10_MS)  /**< Connection supervisory timeout (4 seconds). */

#define FIRST_CONN_PARAMS_UPDATE_DELAY APP_TIMER_TICKS(5000)            /**< Time from initiating event (connect or start of notification) to first time sd_ble_gap_conn_param_update is called (5 seconds). */
#define NEXT_CONN_PARAMS_UPDATE_DELAY  APP_TIMER_TICKS(30000)           /**< Time between each call to sd_ble_gap_conn_param_update after the first call (30 seconds). */
#define MAX_CONN_PARAMS_UPDATE_COUNT   3                                /**< Number of attempts before giving up the connection parameter negotiation. */

#define BUTTON_DETECTION_DELAY         APP_TIMER_TICKS(50)              /**< Delay from a GPIOTE event until a button is reported as pushed (in number of timer ticks). */

#define DEAD_BEEF                      0xDEADBEEF                       /**< Value used as error code on stack dump, can be used to identify stack location on stack unwind. */


NRF_BLE_GATT_DEF(m_gatt);       /**< GATT module instance. */

ble_advdata_t        g_advdata;
ble_gap_adv_params_t g_adv_params;

static uint16_t m_conn_handle = BLE_CONN_HANDLE_INVALID;            /**< Handle of the current connection. */
static uint8_t  m_adv_handle = BLE_GAP_ADV_SET_HANDLE_NOT_SET;      /**< Advertising handle used to identify an advertising set. */
static uint8_t  m_enc_advdata[BLE_GAP_ADV_SET_DATA_SIZE_MAX];       /**< Buffer for storing an encoded advertising set. */

/**@brief Struct that contains pointers to the encoded advertising data. */
static ble_gap_adv_data_t m_adv_data =
{
    .adv_data =
    {
        .p_data = m_enc_advdata,
        .len    = BLE_GAP_ADV_SET_DATA_SIZE_MAX
    },
    .scan_rsp_data =
    {
        .p_data = NULL,
        .len    = 0

    }
};


/**@brief Callback function for asserts in the SoftDevice.
 *
 * @details This function will be called in case of an assert in the SoftDevice.
 *
 * @warning This handler is an example only and does not fit a final product. You need to analyze
 *          how your product is supposed to react in case of Assert.
 * @warning On assert from the SoftDevice, the system can only recover on reset.
 *
 * @param[in] line_num    Line number of the failing ASSERT call.
 * @param[in] p_file_name File name of the failing ASSERT call.
 */
void assert_nrf_callback(uint16_t line_num, const uint8_t * p_file_name)
{
    app_error_handler(DEAD_BEEF, line_num, p_file_name);
}


/**@brief Function for the Timer initialization.
 *
 * @details Initializes the timer module.
 */
static void timers_init(void)
{
    // Initialize timer module, making it use the scheduler
    ret_code_t err_code = app_timer_init();
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for the GAP initialization.
 *
 * @details This function sets up all the necessary GAP (Generic Access Profile) parameters of the
 *          device including the device name, appearance, and the preferred connection parameters.
 */
static void gap_params_init(void)
{
    ret_code_t              err_code;
    ble_gap_conn_params_t   gap_conn_params;
    ble_gap_conn_sec_mode_t sec_mode;

    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&sec_mode);

    err_code = sd_ble_gap_device_name_set(&sec_mode, (const uint8_t *)DEVICE_NAME, strlen(DEVICE_NAME));
    APP_ERROR_CHECK(err_code);

    err_code = sd_ble_gap_appearance_set(BLE_APPEARANCE_GENERIC_TAG);
    APP_ERROR_CHECK(err_code);

    memset(&gap_conn_params, 0, sizeof(gap_conn_params));

    gap_conn_params.min_conn_interval = MIN_CONN_INTERVAL;
    gap_conn_params.max_conn_interval = MAX_CONN_INTERVAL;
    gap_conn_params.slave_latency     = SLAVE_LATENCY;
    gap_conn_params.conn_sup_timeout  = CONN_SUP_TIMEOUT;

    err_code = sd_ble_gap_ppcp_set(&gap_conn_params);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for initializing the GATT module.
 */
static void gatt_init(void)
{
    ret_code_t err_code = nrf_ble_gatt_init(&m_gatt, NULL);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for initializing the Advertising functionality.
*
* @details Encodes the required advertising data and passes it to the stack.
*          Also builds a structure to be passed to the stack when starting advertising.
*/
static void advertising_init(void)
{
    NRF_LOG_INFO("advertising_init\n");
    ret_code_t            err_code;
    uint16_t              uuid;

    uint16_t              tile_service_uuid;
    uint16_t              adv_interval;
    uint8_t               tile_service_data_length;
    uint8_t               tile_service_data[TILE_SERVICE_DATA_MAX_LENGTH];
    uint8_t               manuf;
    ble_advdata_service_data_t service_data_array[1];   /**< Array of Service data structures. */

    /* manufacturing data is available */
    ble_advdata_manuf_data_t   manuf_specific_data;     /**< Manufacturer specific data. */

    /* Set manufacturing data to default */ 
    memset(&manuf_specific_data, 0, sizeof(manuf_specific_data));

    // Set Tile default advertising parameters.
    memset(&g_adv_params, 0, sizeof(g_adv_params));

    g_adv_params.primary_phy     = BLE_GAP_PHY_1MBPS;
    g_adv_params.duration        = APP_ADV_DURATION;
    g_adv_params.properties.type = BLE_GAP_ADV_TYPE_CONNECTABLE_SCANNABLE_UNDIRECTED;
    g_adv_params.p_peer_addr     = NULL;
    g_adv_params.filter_policy   = BLE_GAP_ADV_FP_ANY;

    // Build and set Tile advertising data.
    memset(&g_advdata, 0, sizeof(g_advdata));

    g_advdata.name_type               = BLE_ADVDATA_NO_NAME;
    g_advdata.include_appearance      = false;
    g_advdata.flags                   = BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE;

    /* Get current advertising data and params */
    (void) tile_gap_get_adv_params(&adv_interval, &tile_service_uuid, &tile_service_data_length, tile_service_data, &manuf);

    g_adv_params.interval = adv_interval;

    if (0 != tile_service_data_length) 
    {
        service_data_array[0].service_uuid  = tile_service_uuid; 
        service_data_array[0].data.size     = tile_service_data_length; 
        service_data_array[0].data.p_data   = tile_service_data; 
        g_advdata.p_service_data_array      = service_data_array; 
        g_advdata.service_data_count        = 1;
    }

    uuid = tile_service_uuid;
    ble_uuid_t adv_uuids[]             = {{uuid, BLE_UUID_TYPE_BLE}};
    g_advdata.uuids_complete.uuid_cnt  = 1;
    g_advdata.uuids_complete.p_uuids   = adv_uuids;

    m_adv_data.adv_data.len = BLE_GAP_ADV_SET_DATA_SIZE_MAX;

    err_code = ble_advdata_encode(&g_advdata, m_adv_data.adv_data.p_data, &m_adv_data.adv_data.len);
    APP_ERROR_CHECK(err_code);

    err_code = sd_ble_gap_adv_set_configure(&m_adv_handle, &m_adv_data, &g_adv_params);
    APP_ERROR_CHECK(err_code);
}


/**
 * @brief Function for updating advertising payload
 */
void advertising_update(void)
{
    NRF_LOG_INFO("advertising_update\n");
    ret_code_t err_code;

    /* Stop Advertising, so as to enable it to be updated */
    err_code = sd_ble_gap_adv_stop(m_adv_handle);
    APP_ERROR_CHECK(err_code);
  
    /* Init Advertising data */ 
    advertising_init();

    /* Restart Advertising */
    err_code = sd_ble_gap_adv_start(m_adv_handle, APP_BLE_CONN_CFG_TAG);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for starting advertising.
 */
static void advertising_start(void)
{
    ret_code_t err_code;
      
    advertising_init();

    err_code = sd_ble_gap_adv_start(m_adv_handle, APP_BLE_CONN_CFG_TAG);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for handling the Connection Parameters Module.
 *
 * @details This function will be called for all events in the Connection Parameters Module which
 *          are passed to the application.
 *          @note All this function does is to disconnect. This could have been done by simply
 *                setting the disconnect_on_fail config parameter, but instead we use the event
 *                handler mechanism to demonstrate its use.
 *
 * @param[in] p_evt  Event received from the Connection Parameters Module.
 */
static void on_conn_params_evt(ble_conn_params_evt_t * p_evt)
{
    ret_code_t err_code;

    if (p_evt->evt_type == BLE_CONN_PARAMS_EVT_FAILED)
    {
        err_code = sd_ble_gap_disconnect(m_conn_handle, BLE_HCI_CONN_INTERVAL_UNACCEPTABLE);
        APP_ERROR_CHECK(err_code);
    }
}


/**@brief Function for handling a Connection Parameters error.
 *
 * @param[in] nrf_error  Error code containing information about what went wrong.
 */
static void conn_params_error_handler(uint32_t nrf_error)
{
    APP_ERROR_HANDLER(nrf_error);
}


/**@brief Function for initializing the Connection Parameters module.
 */
static void conn_params_init(void)
{
    ret_code_t             err_code;
    ble_conn_params_init_t cp_init;

    memset(&cp_init, 0, sizeof(cp_init));

    cp_init.p_conn_params                  = NULL;
    cp_init.first_conn_params_update_delay = FIRST_CONN_PARAMS_UPDATE_DELAY;
    cp_init.next_conn_params_update_delay  = NEXT_CONN_PARAMS_UPDATE_DELAY;
    cp_init.max_conn_params_update_count   = MAX_CONN_PARAMS_UPDATE_COUNT;
    cp_init.start_on_notify_cccd_handle    = BLE_GATT_HANDLE_INVALID;
    cp_init.disconnect_on_fail             = false;
    cp_init.evt_handler                    = on_conn_params_evt;
    cp_init.error_handler                  = conn_params_error_handler;

    err_code = ble_conn_params_init(&cp_init);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for handling BLE events.
 *
 * @param[in]   p_ble_evt   Bluetooth stack event.
 * @param[in]   p_context   Unused.
 */
static void ble_evt_handler(ble_evt_t const * p_ble_evt, void * p_context)
{
    ret_code_t err_code;

    switch (p_ble_evt->header.evt_id)
    {
        case BLE_GAP_EVT_CONNECTED:
            NRF_LOG_INFO("Connected.");
            bsp_board_led_on(BSP_BOARD_LED_0);
            m_conn_handle = p_ble_evt->evt.gap_evt.conn_handle;
            break;

        case BLE_GAP_EVT_DISCONNECTED:
            NRF_LOG_INFO("Disconnected, reason %d.", p_ble_evt->evt.gap_evt.params.disconnected.reason);
            bsp_board_led_off(BSP_BOARD_LED_0);
            m_conn_handle = BLE_CONN_HANDLE_INVALID;
            advertising_start();
            break;

        case BLE_GAP_EVT_SEC_PARAMS_REQUEST:
            NRF_LOG_DEBUG("BLE_GAP_EVT_SEC_PARAMS_REQUEST");
            // Pairing not supported
            err_code = sd_ble_gap_sec_params_reply(m_conn_handle,
                                                   BLE_GAP_SEC_STATUS_PAIRING_NOT_SUPP,
                                                   NULL,
                                                   NULL);
            APP_ERROR_CHECK(err_code);
            break;

        case BLE_GAP_EVT_PHY_UPDATE_REQUEST:
        {
            NRF_LOG_DEBUG("PHY update request.");
            ble_gap_phys_t const phys =
            {
                .rx_phys = BLE_GAP_PHY_AUTO,
                .tx_phys = BLE_GAP_PHY_AUTO,
            };
            err_code = sd_ble_gap_phy_update(p_ble_evt->evt.gap_evt.conn_handle, &phys);
            APP_ERROR_CHECK(err_code);
        } break;

        case BLE_GATTS_EVT_SYS_ATTR_MISSING:
            // No system attributes have been stored.
            err_code = sd_ble_gatts_sys_attr_set(m_conn_handle, NULL, 0, 0);
            APP_ERROR_CHECK(err_code);
            break;

        case BLE_GATTC_EVT_TIMEOUT:
            // Disconnect on GATT Client timeout event.
            NRF_LOG_DEBUG("GATT Client Timeout.");
            err_code = sd_ble_gap_disconnect(p_ble_evt->evt.gattc_evt.conn_handle,
                                             BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
            APP_ERROR_CHECK(err_code);
            break;

        case BLE_GATTS_EVT_TIMEOUT:
            // Disconnect on GATT Server timeout event.
            NRF_LOG_DEBUG("GATT Server Timeout.");
            err_code = sd_ble_gap_disconnect(p_ble_evt->evt.gatts_evt.conn_handle,
                                             BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
            APP_ERROR_CHECK(err_code);
            break;
        
        case BLE_GAP_EVT_AUTH_KEY_REQUEST:
            NRF_LOG_INFO("BLE_GAP_EVT_AUTH_KEY_REQUEST");
            break;

        case BLE_GAP_EVT_LESC_DHKEY_REQUEST:
            NRF_LOG_INFO("BLE_GAP_EVT_LESC_DHKEY_REQUEST");
            break;

         case BLE_GAP_EVT_AUTH_STATUS:
             NRF_LOG_INFO("BLE_GAP_EVT_AUTH_STATUS: status=0x%x bond=0x%x lv4: %d kdist_own:0x%x kdist_peer:0x%x",
                          p_ble_evt->evt.gap_evt.params.auth_status.auth_status,
                          p_ble_evt->evt.gap_evt.params.auth_status.bonded,
                          p_ble_evt->evt.gap_evt.params.auth_status.sm1_levels.lv4,
                          *((uint8_t *)&p_ble_evt->evt.gap_evt.params.auth_status.kdist_own),
                          *((uint8_t *)&p_ble_evt->evt.gap_evt.params.auth_status.kdist_peer));
            break;

        default:
            // No implementation needed.
            break;
    }
}


/**@brief Function for initializing the BLE stack.
 *
 * @details Initializes the SoftDevice and the BLE event interrupt.
 */
static void ble_stack_init(void)
{
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
    NRF_SDH_BLE_OBSERVER(m_ble_observer, APP_BLE_OBSERVER_PRIO, ble_evt_handler, NULL);
}


/**@brief Function for handling events from the button handler module.
 *
 * @param[in] pin_no        The pin that the event applies to.
 * @param[in] button_action The button action (press/release).
 */
static void button_event_handler(uint8_t pin_no, uint8_t button_action)
{
    NRF_LOG_INFO("button_event_handler: pin_no: %u, button_action:%u\r\n",pin_no, button_action);
    if(TILE_BUTTON == pin_no && true == button_action)
    {
        NRF_LOG_INFO("button press detected successfully\r\n");
        tile_button_was_pressed();
    }
}


/**@brief Function for initializing the button handler module.
 */
static void buttons_init(void)
{
    ret_code_t err_code;

    //The array must be static because a pointer to it will be saved in the button handler module.
    static app_button_cfg_t buttons[] =
    {
        {TILE_BUTTON, APP_BUTTON_ACTIVE_LOW, BUTTON_PULL, button_event_handler}
    };

    err_code = app_button_init(buttons, ARRAY_SIZE(buttons),
                               BUTTON_DETECTION_DELAY);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for initializing logging. */
static void log_init(void)
{
    ret_code_t err_code = NRF_LOG_INIT(NULL);
    APP_ERROR_CHECK(err_code);

    NRF_LOG_DEFAULT_BACKENDS_INIT();
}


/**@brief Function for initializing LEDs. */
static void leds_init(void)
{
    ret_code_t err_code = bsp_init(BSP_INIT_LEDS, NULL);
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for initializing power management.
 */
static void power_management_init(void)
{
    ret_code_t err_code;
    err_code = nrf_pwr_mgmt_init();
    APP_ERROR_CHECK(err_code);
}


/**@brief Function for handling the idle state (main loop).
 *
 * @details If there is no pending log operation, then sleep until next the next event occurs.
 */
static void idle_state_handle(void)
{
    if (NRF_LOG_PROCESS() == false)
    {
        nrf_pwr_mgmt_run();
    }
}


/**
 * @brief Function for application main entry.
 */
int main(void)
{
    // Initialize.
    log_init();
    leds_init();
    timers_init();
    buttons_init();
    power_management_init();
    ble_stack_init();
    gap_params_init();
    gatt_init();
    conn_params_init();
    tile_service_init();

    // Start execution.
    NRF_LOG_INFO("Tile example started.");

    advertising_start();

    uint32_t err_code = app_button_enable();
    APP_ERROR_CHECK(err_code);

    // Enter main loop.
    for (;;)
    {
        idle_state_handle();
    }
}


/**
 * @}
 */
