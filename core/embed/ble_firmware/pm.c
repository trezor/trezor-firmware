

#include "nrf_log.h"
#include "peer_manager_handler.h"

#include "int_comm.h"
#include "pm.h"

#define SEC_PARAM_BOND 1     /**< Perform bonding. */
#define SEC_PARAM_MITM 1     /**< Man In The Middle protection not required. */
#define SEC_PARAM_LESC 1     /**< LE Secure Connections not enabled. */
#define SEC_PARAM_KEYPRESS 0 /**< Keypress notifications not enabled. */
#define SEC_PARAM_IO_CAPABILITIES \
  BLE_GAP_IO_CAPS_KEYBOARD_DISPLAY /**< No I/O capabilities. */
#define SEC_PARAM_OOB 0            /**< Out Of Band data not available. */
#define SEC_PARAM_MIN_KEY_SIZE 7   /**< Minimum encryption key size. */
#define SEC_PARAM_MAX_KEY_SIZE 16  /**< Maximum encryption key size. */

static pm_peer_id_t
    m_peer_id; /**< Device reference handle to the current bonded central. */

pm_peer_id_t get_peer_id(void) { return m_peer_id; }

/**@brief Function for setting filtered whitelist.
 *
 * @param[in] skip  Filter passed to @ref pm_peer_id_list.
 */
void whitelist_set(pm_peer_id_list_skip_t skip) {
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

/**@brief Function for handling Peer Manager events.
 *
 * @param[in] p_evt  Peer Manager event.
 */
void pm_evt_handler(pm_evt_t const *p_evt) {
  pm_handler_on_pm_evt(p_evt);
  pm_handler_disconnect_on_sec_failure(p_evt);
  pm_handler_flash_clean(p_evt);

  switch (p_evt->evt_id) {
    case PM_EVT_CONN_SEC_SUCCEEDED:
      m_peer_id = p_evt->peer_id;
      break;

    case PM_EVT_PEERS_DELETE_SUCCEEDED:
      // advertising_start(false);
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
void peer_manager_init(void) {
  ble_gap_sec_params_t sec_param;
  pm_privacy_params_t privacy_params;
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

  privacy_params.p_device_irk = NULL;
  privacy_params.privacy_mode = BLE_GAP_PRIVACY_MODE_DEVICE_PRIVACY;
  privacy_params.private_addr_cycle_s = 0;
  privacy_params.private_addr_type =
      BLE_GAP_ADDR_TYPE_RANDOM_PRIVATE_RESOLVABLE;
  pm_privacy_set(&privacy_params);

  err_code = pm_register(pm_evt_handler);
  APP_ERROR_CHECK(err_code);
}

/**@brief Function for setting filtered device identities.
 *
 * @param[in] skip  Filter passed to @ref pm_peer_id_list.
 */
void identities_set(pm_peer_id_list_skip_t skip) {
  pm_peer_id_t peer_ids[BLE_GAP_DEVICE_IDENTITIES_MAX_COUNT];
  uint32_t peer_id_count = BLE_GAP_DEVICE_IDENTITIES_MAX_COUNT;

  ret_code_t err_code =
      pm_peer_id_list(peer_ids, &peer_id_count, PM_PEER_ID_INVALID, skip);
  APP_ERROR_CHECK(err_code);

  err_code = pm_device_identities_list_set(peer_ids, peer_id_count);
  APP_ERROR_CHECK(err_code);
}

/////**@brief Clear bond information from persistent storage. */
void delete_bonds(void) {
  ret_code_t err_code;

  NRF_LOG_INFO("Erase bonds!");

  // pm_whitelist_set(NULL, 0);
  err_code = pm_peers_delete();
  APP_ERROR_CHECK(err_code);
}
