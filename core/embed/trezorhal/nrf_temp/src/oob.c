
#include <zephyr/kernel.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>

#include <nfc_t4t_lib.h>
#include <nfc/t4t/ndef_file.h>

#include <nfc/ndef/msg.h>
#include <nfc/ndef/ch.h>
#include <nfc/ndef/ch_msg.h>
#include <nfc/ndef/le_oob_rec.h>
#include <nfc/ndef/le_oob_rec_parser.h>

#include <nfc/tnep/tag.h>
#include <nfc/tnep/ch.h>

#include "events.h"

#define NDEF_MSG_BUF_SIZE 256
#define AUTH_SC_FLAG 0x08

//#define NFC_FIELD_LED DK_LED2
//#define CON_STATUS_LED DK_LED1
//
//#define KEY_BOND_REMOVE_MASK DK_BTN4_MSK

#define NFC_NDEF_LE_OOB_REC_PARSER_BUFF_SIZE 150
#define NFC_TNEP_BUFFER_SIZE 1024


static struct bt_le_oob oob_local;
static struct k_work adv_work;
static uint8_t conn_cnt;
static uint8_t tk_value[NFC_NDEF_LE_OOB_REC_TK_LEN];
static uint8_t remote_tk_value[NFC_NDEF_LE_OOB_REC_TK_LEN];
static struct bt_le_oob oob_remote;

/* Bonded address queue. */
K_MSGQ_DEFINE(bonds_queue,
sizeof(bt_addr_le_t),
CONFIG_BT_MAX_PAIRED,
4);

static struct k_poll_signal pair_signal;
static uint8_t tnep_buffer[NFC_TNEP_BUFFER_SIZE];
static uint8_t tnep_swap_buffer[NFC_TNEP_BUFFER_SIZE];
static bool use_remote_tk;
static bool adv_permission;



static int tk_value_generate(void)
{
  int err;

  err = bt_rand(tk_value, sizeof(tk_value));
  if (err) {
    printk("Random TK value generation failed: %d\n", err);
  }

  return err;
}

static void pair_key_generate_init(void)
{
  k_poll_signal_init(&pair_signal);
  k_poll_event_init(events_get(NFC_TNEP_EVENTS_NUMBER),
                    K_POLL_TYPE_SIGNAL, K_POLL_MODE_NOTIFY_ONLY,
                    &pair_signal);
}

static int paring_key_generate(void)
{
  int err;

  printk("Generating new pairing keys\n");

  err = bt_le_oob_get_local(BT_ID_DEFAULT, &oob_local);
  if (err) {
    printk("Error while fetching local OOB data: %d\n", err);
  }

  return tk_value_generate();
}

static void paring_key_process(void)
{
  int err;

  if (events_get(NFC_TNEP_EVENTS_NUMBER)->state == K_POLL_STATE_SIGNALED) {
    err = paring_key_generate();
    if (err) {
      printk("Pairing key generation error: %d\n", err);
    }

    k_poll_signal_reset(events_get(NFC_TNEP_EVENTS_NUMBER)->signal);
    events_get(NFC_TNEP_EVENTS_NUMBER)->state = K_POLL_STATE_NOT_READY;
  }
}

static void bond_find(const struct bt_bond_info *info, void *user_data)
{
  int err;
  struct bt_conn *conn;

  /* Filter already connected peers. */
  conn = bt_conn_lookup_addr_le(BT_ID_DEFAULT, &info->addr);
  if (conn) {
    bt_conn_unref(conn);
    return;
  }

  err = k_msgq_put(&bonds_queue, (void *) &info->addr, K_NO_WAIT);
  if (err) {
    printk("No space in the queue for the bond\n");
  }
}


/**
 * @brief Callback function for handling NFC events.
 */
static void nfc_callback(void *context,
                         nfc_t4t_event_t event,
                         const uint8_t *data,
                         size_t data_length,
                         uint32_t flags)
{
  ARG_UNUSED(context);
  ARG_UNUSED(data);
  ARG_UNUSED(flags);

  switch (event) {
    case NFC_T4T_EVENT_FIELD_ON:
      printk("NFC callback 1\n");
      nfc_tnep_tag_on_selected();
      //dk_set_led_on(NFC_FIELD_LED);

      //adv_permission = true;

      break;

    case NFC_T4T_EVENT_FIELD_OFF:
      printk("NFC callback 2\n");
      nfc_tnep_tag_on_selected();
      //dk_set_led_off(NFC_FIELD_LED);
      break;

    case NFC_T4T_EVENT_NDEF_READ:
      printk("NFC callback 3\n");
//      if (adv_permission) {
//        advertising_start();
//        adv_permission = false;
//      }

      break;

    case NFC_T4T_EVENT_NDEF_UPDATED:
      printk("NFC callback 4\n");
      if (data_length > 0) {
        nfc_tnep_tag_rx_msg_indicate(nfc_t4t_ndef_file_msg_get(data),
                                     data_length);
      }

    default:
      break;
  }
}


/** .. include_startingpoint_pair_msg_rst */
static int tnep_initial_msg_encode(struct nfc_ndef_msg_desc *msg)
{
  int err;
  struct nfc_ndef_ch_msg_records ch_records;
  static struct nfc_ndef_le_oob_rec_payload_desc rec_payload;


  NFC_NDEF_LE_OOB_RECORD_DESC_DEF(oob_rec, '0', &rec_payload);
  NFC_NDEF_CH_AC_RECORD_DESC_DEF(oob_ac, NFC_AC_CPS_ACTIVE, 1, "0", 0);
  NFC_NDEF_CH_HS_RECORD_DESC_DEF(hs_rec, NFC_NDEF_CH_MSG_MAJOR_VER,
                                 NFC_NDEF_CH_MSG_MINOR_VER, 1);

  memset(&rec_payload, 0, sizeof(rec_payload));

  rec_payload.addr = &oob_local.addr;
  rec_payload.le_sc_data = &oob_local.le_sc_data;
  rec_payload.tk_value = tk_value;
  rec_payload.local_name = bt_get_name();
  rec_payload.le_role = NFC_NDEF_LE_OOB_REC_LE_ROLE(
          NFC_NDEF_LE_OOB_REC_LE_ROLE_PERIPH_ONLY);
  rec_payload.appearance = NFC_NDEF_LE_OOB_REC_APPEARANCE(
          CONFIG_BT_DEVICE_APPEARANCE);
  rec_payload.flags = NFC_NDEF_LE_OOB_REC_FLAGS(BT_LE_AD_NO_BREDR);

  ch_records.ac = &NFC_NDEF_CH_AC_RECORD_DESC(oob_ac);
  ch_records.carrier = &NFC_NDEF_LE_OOB_RECORD_DESC(oob_rec);
  ch_records.cnt = 1;

  err =  nfc_ndef_ch_msg_hs_create(msg,
                                   &NFC_NDEF_CH_RECORD_DESC(hs_rec),
                                   &ch_records);


  printk("mac0: %X:%X:%X:%X:%X:%X\n",
         rec_payload.addr->a.val[5],
         rec_payload.addr->a.val[4],
         rec_payload.addr->a.val[3],
         rec_payload.addr->a.val[2],
         rec_payload.addr->a.val[1],
         rec_payload.addr->a.val[0]);

  if (err) {
    return err;
  }

  return nfc_tnep_initial_msg_encode(msg, NULL, 0);
}
/** .. include_endpoint_pair_msg_rst */

static int check_oob_carrier(const struct nfc_tnep_ch_record *ch_record,
                             const struct nfc_ndef_record_desc **oob_data)
{
  const struct nfc_ndef_ch_ac_rec *ac_rec = NULL;

  for (size_t i = 0; i < ch_record->count; i++) {
    if (nfc_ndef_le_oob_rec_check(ch_record->carrier[i])) {
      *oob_data = ch_record->carrier[i];
    }
  }

  if (!oob_data) {
    printk("Connection Handover Requester not supporting OOB BLE\n");
    return -EINVAL;
  }

  /* Look for the corresponding Alternative Carrier Record. */
  for (size_t i = 0; i < ch_record->count; i++) {
    if (((*oob_data)->id_length == ch_record->ac[i].carrier_data_ref.length) &&
        (memcmp((*oob_data)->id,
                ch_record->ac[i].carrier_data_ref.data,
                (*oob_data)->id_length) == 0)) {
      ac_rec = &ch_record->ac[i];
    }
  }

  if (!ac_rec) {
    printk("No Alternative Carrier Record for OOB LE carrier\n");
    return -EINVAL;
  }

  /* Check carrier state */
  if ((ac_rec->cps != NFC_AC_CPS_ACTIVE) &&
      (ac_rec->cps != NFC_AC_CPS_ACTIVATING)) {
    printk("LE OBB Carrier inactive\n");
    return -EINVAL;
  }

  return 0;
}


static void lesc_oob_data_set(struct bt_conn *conn,
                              struct bt_conn_oob_info *oob_info)
{
  int err;
  char addr[BT_ADDR_LE_STR_LEN];
  struct bt_conn_info info;

  err = bt_conn_get_info(conn, &info);
  if (err) {
    return;
  }

  struct bt_le_oob_sc_data *oob_data_local =
          oob_info->lesc.oob_config != BT_CONN_OOB_REMOTE_ONLY
          ? &oob_local.le_sc_data
          : NULL;
  struct bt_le_oob_sc_data *oob_data_remote =
          oob_info->lesc.oob_config != BT_CONN_OOB_LOCAL_ONLY
          ? &oob_remote.le_sc_data
          : NULL;

  if (oob_data_remote &&
      bt_addr_le_cmp(info.le.remote, &oob_remote.addr)) {
    bt_addr_le_to_str(info.le.remote, addr, sizeof(addr));
    printk("No OOB data available for remote %s", addr);
    bt_conn_auth_cancel(conn);
    return;
  }

  if (oob_data_local &&
      bt_addr_le_cmp(info.le.local, &oob_local.addr)) {
    bt_addr_le_to_str(info.le.local, addr, sizeof(addr));
    printk("No OOB data available for local %s", addr);
    bt_conn_auth_cancel(conn);
    return;
  }

  err = bt_le_oob_set_sc_data(conn, oob_data_local, oob_data_remote);
  if (err) {
    printk("Error while setting OOB data: %d\n", err);
  }
}

//static void legacy_tk_value_set(struct bt_conn *conn)
//{
//  int err;
//  const uint8_t *tk = use_remote_tk ? remote_tk_value : tk_value;
//
//  err = bt_le_oob_set_legacy_tk(conn, tk);
//  if (err) {
//    printk("TK value set error: %d\n", err);
//  }
//
//  use_remote_tk = false;
//}

void auth_oob_data_request(struct bt_conn *conn,
                                  struct bt_conn_oob_info *info)
{
  printk("OOB data requested\n");

  if (info->type == BT_CONN_OOB_LE_SC) {
    printk("LESC OOB data requested\n");
    lesc_oob_data_set(conn, info);
  }

//  if (info->type == BT_CONN_OOB_LE_LEGACY) {
//    printk("Legacy TK value requested\n");
//    legacy_tk_value_set(conn);
//  }
}


static int oob_le_data_handle(const struct nfc_ndef_record_desc *rec,
                              bool request)
{
  int err;
  const struct nfc_ndef_le_oob_rec_payload_desc *oob;
  uint8_t desc_buf[NFC_NDEF_LE_OOB_REC_PARSER_BUFF_SIZE];
  uint32_t desc_buf_len = sizeof(desc_buf);

  err = nfc_ndef_le_oob_rec_parse(rec, desc_buf,
                                  &desc_buf_len);
  if (err) {
    printk("Error during NDEF LE OOB Record parsing, err: %d.\n",
           err);
  }

  oob = (struct nfc_ndef_le_oob_rec_payload_desc *) desc_buf;

  nfc_ndef_le_oob_rec_printout(oob);

  if ((*oob->le_role != NFC_NDEF_LE_OOB_REC_LE_ROLE_CENTRAL_ONLY) &&
      (*oob->le_role != NFC_NDEF_LE_OOB_REC_LE_ROLE_CENTRAL_PREFFERED)) {
    printk("Unsupported Device LE Role\n");
    return -EINVAL;
  }

  if (oob->le_sc_data) {
    bt_le_oob_set_sc_flag(true);
    oob_remote.le_sc_data = *oob->le_sc_data;
    bt_addr_le_copy(&oob_remote.addr, oob->addr);
  }

  if (oob->tk_value) {
    bt_le_oob_set_legacy_flag(true);
    memcpy(remote_tk_value, oob->tk_value, sizeof(remote_tk_value));
    use_remote_tk = request;
  }

  //advertising_start();

  return 0;
}

/** .. include_startingpoint_nfc_tnep_ch_tag_rst */
static int carrier_prepare(void)
{
  static struct nfc_ndef_le_oob_rec_payload_desc rec_payload;

  NFC_NDEF_LE_OOB_RECORD_DESC_DEF(oob_rec, '0', &rec_payload);
  NFC_NDEF_CH_AC_RECORD_DESC_DEF(oob_ac, NFC_AC_CPS_ACTIVE, 1, "0", 0);

  memset(&rec_payload, 0, sizeof(rec_payload));

  rec_payload.addr = &oob_local.addr;
  rec_payload.le_sc_data = &oob_local.le_sc_data;
  rec_payload.tk_value = tk_value;
  rec_payload.local_name = bt_get_name();
  rec_payload.le_role = NFC_NDEF_LE_OOB_REC_LE_ROLE(
          NFC_NDEF_LE_OOB_REC_LE_ROLE_PERIPH_ONLY);
  rec_payload.appearance = NFC_NDEF_LE_OOB_REC_APPEARANCE(
          CONFIG_BT_DEVICE_APPEARANCE);
  rec_payload.flags = NFC_NDEF_LE_OOB_REC_FLAGS(BT_LE_AD_NO_BREDR);

  return nfc_tnep_ch_carrier_set(&NFC_NDEF_CH_AC_RECORD_DESC(oob_ac),
                                 &NFC_NDEF_LE_OOB_RECORD_DESC(oob_rec),
                                 1);
}

#if defined(CONFIG_NFC_TAG_CH_REQUESTER)
static int tnep_ch_request_prepare(void)
{
	bt_le_adv_stop();
	return carrier_prepare();
}

static int tnep_ch_select_received(const struct nfc_tnep_ch_record *ch_select,
				   bool inactive)
{
	int err;
	const struct nfc_ndef_record_desc *oob_data = NULL;

	if (!ch_select->count) {
		return -EINVAL;
	}

	/* All alternative carrier are inactive */
	if (inactive) {
		/* Try send request again. */
		return carrier_prepare();
	}

	err = check_oob_carrier(ch_select, &oob_data);
	if (err) {
		return err;
	}

	err = oob_le_data_handle(oob_data, false);
	if (err) {
		return err;
	}

	return 0;

}
#endif /* defined(CONFIG_NFC_TAG_CH_REQUESTER) */

static int tnep_ch_request_received(const struct nfc_tnep_ch_request *ch_req)
{
  int err;
  const struct nfc_ndef_record_desc *oob_data = NULL;

  if (!ch_req->ch_record.count) {
    return -EINVAL;
  }

  err = check_oob_carrier(&ch_req->ch_record, &oob_data);
  if (err) {
    return err;
  }

  bt_le_adv_stop();

  err = oob_le_data_handle(oob_data, true);
  if (err) {
    return err;
  }

  return carrier_prepare();
}

static struct nfc_tnep_ch_cb ch_cb = {
#if defined(CONFIG_NFC_TAG_CH_REQUESTER)
        .request_msg_prepare = tnep_ch_request_prepare,
	.select_msg_recv = tnep_ch_select_received,
#endif
        .request_msg_recv = tnep_ch_request_received
};
/** .. include_endpoint_nfc_tnep_ch_tag_rst */

static void nfc_init(void)
{
  int err;

  /* TNEP init */
  err = nfc_tnep_tag_tx_msg_buffer_register(tnep_buffer, tnep_swap_buffer,
                                            sizeof(tnep_buffer));
  if (err) {
    printk("Cannot register tnep buffer, err: %d\n", err);
    return;
  }

  err = nfc_tnep_tag_init(events_get(0), NFC_TNEP_EVENTS_NUMBER,
                          nfc_t4t_ndef_rwpayload_set);
  if (err) {
    printk("Cannot initialize TNEP protocol, err: %d\n", err);
    return;
  }

  /* Set up NFC */
  err = nfc_t4t_setup(nfc_callback, NULL);
  if (err) {
    printk("Cannot setup NFC T4T library!\n");
    return;
  }

  err = nfc_tnep_tag_initial_msg_create(2, tnep_initial_msg_encode);
  if (err) {
    printk("Cannot create initial TNEP message, err: %d\n", err);
  }

  err = nfc_tnep_ch_service_init(&ch_cb);
  if (err) {
    printk("TNEP CH Service init error: %d\n", err);
    return;
  }

  /* Start sensing NFC field */
  err = nfc_t4t_emulation_start();
  if (err) {
    printk("Cannot start emulation!\n");
    return;
  }

  printk("NFC configuration done\n");
}


void oob_init(void) {
  paring_key_generate();
  pair_key_generate_init();
  nfc_init();
}

void oob_process(void) {
  nfc_tnep_tag_process();
  paring_key_process();
}

//K_THREAD_DEFINE(oob_thread_id, CONFIG_BT_NUS_THREAD_STACK_SIZE, oob_thread, NULL, NULL,
//        NULL, 7, 0, 0);

void oob_signal(void) {
  k_poll_signal_raise(&pair_signal, 0);
}


void oob_fetch_addr(void) {
  bt_le_oob_get_local(BT_ID_DEFAULT, &oob_local);
}
