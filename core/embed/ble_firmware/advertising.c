#include "ble_gap.h"

#include "advertising.h"
#include "ble_advdata.h"
#include "ble_advertising.h"
#include "ble_nus.h"
#include "connection.h"
#include "defs.h"
#include "nrf_log.h"
#include "pm.h"
#include "power.h"

#define APP_ADV_INTERVAL                                             \
  64 /**< The advertising interval (in units of 0.625 ms. This value \
        corresponds to 40 ms). */

#define APP_ADV_DURATION                                           \
  18000 /**< The advertising duration (180 seconds) in units of 10 \
           milliseconds. */

#define NUS_SERVICE_UUID_TYPE                                           \
  BLE_UUID_TYPE_VENDOR_BEGIN /**< UUID type for the Nordic UART Service \
                                (vendor specific). */

static ble_uuid_t m_adv_uuids[] = /**< Universally unique service identifier. */
    {{BLE_UUID_NUS_SERVICE, NUS_SERVICE_UUID_TYPE}};

BLE_ADVERTISING_DEF(m_advertising); /**< Advertising module instance. */

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
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_DIRECTED);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_DIRECTED:
      NRF_LOG_INFO("Directed advertising.");
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_DIRECTED);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_FAST:
      NRF_LOG_INFO("Fast advertising.");
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_SLOW:
      NRF_LOG_INFO("Slow advertising.");
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_SLOW);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_FAST_WHITELIST:
      NRF_LOG_INFO("Fast advertising with whitelist.");
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_WHITELIST);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_SLOW_WHITELIST:
      NRF_LOG_INFO("Slow advertising with whitelist.");
      // err_code = bsp_indication_set(BSP_INDICATE_ADVERTISING_WHITELIST);
      // APP_ERROR_CHECK(err_code);
      break;

    case BLE_ADV_EVT_IDLE:
      // sleep_mode_enter();
      break;

    case BLE_ADV_EVT_WHITELIST_REQUEST: {
      ble_gap_addr_t whitelist_addrs[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
      ble_gap_irk_t whitelist_irks[BLE_GAP_WHITELIST_ADDR_MAX_COUNT];
      uint32_t addr_cnt = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;
      uint32_t irk_cnt = BLE_GAP_WHITELIST_ADDR_MAX_COUNT;

      err_code = pm_whitelist_get(whitelist_addrs, &addr_cnt, whitelist_irks,
                                  &irk_cnt);
      if (err_code != NRF_ERROR_NOT_FOUND) {
        APP_ERROR_CHECK(err_code);
      } else {
        break;
      }
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
      if (get_peer_id() != PM_PEER_ID_INVALID) {
        err_code = pm_peer_data_bonding_load(get_peer_id(), &peer_bonding_data);
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

void advertising_init(void) {
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

void advertising_start(bool whitelist) {
  m_advertising.adv_modes_config.ble_adv_on_disconnect_disabled = false;
  if (m_advertising.adv_mode_current != BLE_ADV_MODE_FAST &&
      get_connection_handle() == BLE_CONN_HANDLE_INVALID) {
    whitelist_set(PM_PEER_ID_LIST_SKIP_NO_ID_ADDR);

    ret_code_t ret = ble_advertising_start(&m_advertising, BLE_ADV_MODE_FAST);
    APP_ERROR_CHECK(ret);
  }

  if (!whitelist) {
    ret_code_t ret = ble_advertising_restart_without_whitelist(&m_advertising);
    APP_ERROR_CHECK(ret);
  }
}

void advertising_stop(void) {
  m_advertising.adv_modes_config.ble_adv_on_disconnect_disabled = true;
  ret_code_t ret = ble_advertising_start(&m_advertising, BLE_ADV_MODE_IDLE);
  APP_ERROR_CHECK(ret);
  //  ret =sd_ble_gap_disconnect(get_connection_handle(),
  //  BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION); APP_ERROR_CHECK(ret);
}

void advertising_restart_without_whitelist(void) {
  ret_code_t ret = ble_advertising_restart_without_whitelist(&m_advertising);
  APP_ERROR_CHECK(ret);
}

bool is_advertising(void) {
  return m_advertising.adv_mode_current != BLE_ADV_MODE_IDLE;
}
