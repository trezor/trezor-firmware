/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2015 Mark Bryars <mbryars@google.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <ecdsa.h>
#include <string.h>

#include "bip32.h"
#include "buttons.h"
#include "config.h"
#include "curves.h"
#include "debug.h"
#include "gettext.h"
#include "hmac.h"
#include "layout2.h"
#include "memzero.h"
#include "nist256p1.h"
#include "rng.h"
#include "trezor.h"
#include "usb.h"
#include "util.h"

#include "u2f.h"
#include "u2f/u2f.h"
#include "u2f/u2f_hid.h"
#include "u2f/u2f_keys.h"
#include "u2f_knownapps.h"

// About 1/2 Second according to values used in protect.c
#define U2F_TIMEOUT (800000 / 2)
#define U2F_OUT_PKT_BUFFER_LEN 130

// Initialise without a cid
static uint32_t cid = 0;

// The channel ID of the last successful U2F_AUTHENTICATE check-only request.
static uint32_t last_good_auth_check_cid = 0;

// Circular Output buffer
static uint32_t u2f_out_start = 0;
static uint32_t u2f_out_end = 0;
static uint8_t u2f_out_packets[U2F_OUT_PKT_BUFFER_LEN][HID_RPT_SIZE];

#define U2F_PUBKEY_LEN 65
#define KEY_PATH_LEN 32
#define KEY_HANDLE_LEN (KEY_PATH_LEN + SHA256_DIGEST_LENGTH)

// Derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
#define KEY_PATH_ENTRIES (KEY_PATH_LEN / sizeof(uint32_t))

// Defined as UsbSignHandler.BOGUS_APP_ID_HASH
// in
// https://github.com/google/u2f-ref-code/blob/master/u2f-chrome-extension/usbsignhandler.js#L118
#define BOGUS_APPID_CHROME "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
#define BOGUS_APPID_FIREFOX \
  "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"

// Auth/Register request state machine
typedef enum {
  INIT = 0,
  AUTH = 10,
  AUTH_PASS = 11,
  REG = 20,
  REG_PASS = 21
} U2F_STATE;

static U2F_STATE last_req_state = INIT;

typedef struct {
  uint8_t reserved;
  uint8_t appId[U2F_APPID_SIZE];
  uint8_t chal[U2F_CHAL_SIZE];
  uint8_t keyHandle[KEY_HANDLE_LEN];
  uint8_t pubKey[U2F_PUBKEY_LEN];
} U2F_REGISTER_SIG_STR;

typedef struct {
  uint8_t appId[U2F_APPID_SIZE];
  uint8_t flags;
  uint8_t ctr[4];
  uint8_t chal[U2F_CHAL_SIZE];
} U2F_AUTHENTICATE_SIG_STR;

static uint32_t dialog_timeout = 0;

uint32_t next_cid(void) {
  // extremely unlikely but hey
  do {
    cid = random32();
  } while (cid == 0 || cid == CID_BROADCAST);
  return cid;
}

// https://fidoalliance.org/specs/fido-u2f-v1.2-ps-20170411/fido-u2f-hid-protocol-v1.2-ps-20170411.html#message--and-packet-structure
// states the following:
// With a packet size of 64 bytes (max for full-speed devices), this means that
// the maximum message payload length is 64 - 7 + 128 * (64 - 5) = 7609 bytes.
#define U2F_MAXIMUM_PAYLOAD_LENGTH 7609
typedef struct {
  uint8_t buf[U2F_MAXIMUM_PAYLOAD_LENGTH];
  uint8_t *buf_ptr;
  uint32_t len;
  uint8_t seq;
  uint8_t cmd;
} U2F_ReadBuffer;

U2F_ReadBuffer *reader;

void u2fhid_read(char tiny, const U2FHID_FRAME *f) {
  // Always handle init packets directly
  if (f->init.cmd == U2FHID_INIT) {
    u2fhid_init(f);
    if (tiny && reader && f->cid == cid) {
      // abort current channel
      reader->cmd = 0;
      reader->len = 0;
      reader->seq = 255;
    }
    return;
  }

  if (tiny) {
    // read continue packet
    if (reader == 0 || cid != f->cid) {
      send_u2fhid_error(f->cid, ERR_CHANNEL_BUSY);
      return;
    }

    if ((f->type & TYPE_INIT) && reader->seq == 255) {
      u2fhid_init_cmd(f);
      return;
    }

    if (reader->seq != f->cont.seq) {
      send_u2fhid_error(f->cid, ERR_INVALID_SEQ);
      reader->cmd = 0;
      reader->len = 0;
      reader->seq = 255;
      return;
    }

    // check out of bounds
    if ((reader->buf_ptr - reader->buf) >= (signed)reader->len ||
        (reader->buf_ptr + sizeof(f->cont.data) - reader->buf) >
            (signed)sizeof(reader->buf))
      return;
    reader->seq++;
    memcpy(reader->buf_ptr, f->cont.data, sizeof(f->cont.data));
    reader->buf_ptr += sizeof(f->cont.data);
    return;
  }

  u2fhid_read_start(f);
}

void u2fhid_init_cmd(const U2FHID_FRAME *f) {
  reader->seq = 0;
  reader->buf_ptr = reader->buf;
  reader->len = MSG_LEN(*f);
  reader->cmd = f->type;
  memcpy(reader->buf_ptr, f->init.data, sizeof(f->init.data));
  reader->buf_ptr += sizeof(f->init.data);
  cid = f->cid;
}

void u2fhid_read_start(const U2FHID_FRAME *f) {
  U2F_ReadBuffer readbuffer = {0};
  memzero(&readbuffer, sizeof(readbuffer));

  if (!(f->type & TYPE_INIT)) {
    return;
  }

  // Broadcast is reserved for init
  if (f->cid == CID_BROADCAST || f->cid == 0) {
    send_u2fhid_error(f->cid, ERR_INVALID_CID);
    return;
  }

  if ((unsigned)MSG_LEN(*f) > sizeof(reader->buf)) {
    send_u2fhid_error(f->cid, ERR_INVALID_LEN);
    return;
  }

  reader = &readbuffer;
  u2fhid_init_cmd(f);

  usbTiny(1);
  for (;;) {
    // Do we need to wait for more data
    while ((reader->buf_ptr - reader->buf) < (signed)reader->len) {
      uint8_t lastseq = reader->seq;
      uint8_t lastcmd = reader->cmd;
      int counter = U2F_TIMEOUT;
      while (reader->seq == lastseq && reader->cmd == lastcmd) {
        if (counter-- == 0) {
          // timeout
          send_u2fhid_error(cid, ERR_MSG_TIMEOUT);
          cid = 0;
          reader = 0;
          usbTiny(0);
          layoutHome();
          return;
        }
        usbPoll();
      }
    }

    // We have all the data
    switch (reader->cmd) {
      case 0:
        // message was aborted by init
        break;
      case U2FHID_PING:
        u2fhid_ping(reader->buf, reader->len);
        break;
      case U2FHID_MSG:
        u2fhid_msg((APDU *)reader->buf, reader->len);
        break;
      case U2FHID_WINK:
        u2fhid_wink(reader->buf, reader->len);
        break;
      default:
        send_u2fhid_error(cid, ERR_INVALID_CMD);
        break;
    }

    // wait for next commmand/ button press
    reader->cmd = 0;
    reader->seq = 255;
    while (dialog_timeout > 0 && reader->cmd == 0) {
      dialog_timeout--;
      usbPoll();  // may trigger new request
      buttonUpdate();
      if (button.YesUp && (last_req_state == AUTH || last_req_state == REG)) {
        last_req_state++;
        // standard requires to remember button press for 10 seconds.
        dialog_timeout = 10 * U2F_TIMEOUT;
      }
    }

    if (reader->cmd == 0) {
      last_req_state = INIT;
      cid = 0;
      reader = 0;
      usbTiny(0);
      layoutHome();
      return;
    }
  }
}

void u2fhid_ping(const uint8_t *buf, uint32_t len) {
  debugLog(0, "", "u2fhid_ping");
  send_u2fhid_msg(U2FHID_PING, buf, len);
}

void u2fhid_wink(const uint8_t *buf, uint32_t len) {
  debugLog(0, "", "u2fhid_wink");
  (void)buf;

  if (len > 0) return send_u2fhid_error(cid, ERR_INVALID_LEN);

  if (dialog_timeout > 0) dialog_timeout = U2F_TIMEOUT;

  U2FHID_FRAME f = {0};
  memzero(&f, sizeof(f));
  f.cid = cid;
  f.init.cmd = U2FHID_WINK;
  f.init.bcntl = 0;
  queue_u2f_pkt(&f);
}

void u2fhid_init(const U2FHID_FRAME *in) {
  const U2FHID_INIT_REQ *init_req = (const U2FHID_INIT_REQ *)&in->init.data;
  U2FHID_FRAME f = {0};
  U2FHID_INIT_RESP resp = {0};
  memzero(&resp, sizeof(resp));

  debugLog(0, "", "u2fhid_init");

  if (in->cid == 0) {
    send_u2fhid_error(in->cid, ERR_INVALID_CID);
    return;
  }

  memzero(&f, sizeof(f));
  f.cid = in->cid;
  f.init.cmd = U2FHID_INIT;
  f.init.bcnth = 0;
  f.init.bcntl = sizeof(resp);

  memcpy(resp.nonce, init_req->nonce, sizeof(init_req->nonce));
  resp.cid = in->cid == CID_BROADCAST ? next_cid() : in->cid;
  resp.versionInterface = U2FHID_IF_VERSION;
  resp.versionMajor = VERSION_MAJOR;
  resp.versionMinor = VERSION_MINOR;
  resp.versionBuild = VERSION_PATCH;
  resp.capFlags = CAPFLAG_WINK;
  memcpy(&f.init.data, &resp, sizeof(resp));

  queue_u2f_pkt(&f);
}

void queue_u2f_pkt(const U2FHID_FRAME *u2f_pkt) {
  // debugLog(0, "", "u2f_write_pkt");
  uint32_t next = (u2f_out_end + 1) % U2F_OUT_PKT_BUFFER_LEN;
  if (u2f_out_start == next) {
    debugLog(0, "", "u2f_write_pkt full");
    return;  // Buffer full :(
  }
  memcpy(u2f_out_packets[u2f_out_end], u2f_pkt, HID_RPT_SIZE);
  u2f_out_end = next;
}

uint8_t *u2f_out_data(void) {
  if (u2f_out_start == u2f_out_end) return NULL;  // No data
  // debugLog(0, "", "u2f_out_data");
  uint32_t t = u2f_out_start;
  u2f_out_start = (u2f_out_start + 1) % U2F_OUT_PKT_BUFFER_LEN;
  return u2f_out_packets[t];
}

void u2fhid_msg(const APDU *a, uint32_t len) {
  if ((APDU_LEN(*a) + sizeof(APDU)) > len) {
    debugLog(0, "", "BAD APDU LENGTH");
    debugInt(APDU_LEN(*a));
    debugInt(len);
    return;
  }

  if (a->cla != 0) {
    send_u2f_error(U2F_SW_CLA_NOT_SUPPORTED);
    return;
  }

  switch (a->ins) {
    case U2F_REGISTER:
      u2f_register(a);
      break;
    case U2F_AUTHENTICATE:
      u2f_authenticate(a);
      break;
    case U2F_VERSION:
      u2f_version(a);
      break;
    default:
      debugLog(0, "", "u2f unknown cmd");
      send_u2f_error(U2F_SW_INS_NOT_SUPPORTED);
  }
}

void send_u2fhid_msg(const uint8_t cmd, const uint8_t *data,
                     const uint32_t len) {
  if (len > U2F_MAXIMUM_PAYLOAD_LENGTH) {
    debugLog(0, "", "send_u2fhid_msg failed");
    return;
  }

  U2FHID_FRAME f = {0};
  uint8_t *p = (uint8_t *)data;
  uint32_t l = len;
  uint32_t psz = 0;
  uint8_t seq = 0;

  // debugLog(0, "", "send_u2fhid_msg");

  memzero(&f, sizeof(f));
  f.cid = cid;
  f.init.cmd = cmd;
  f.init.bcnth = len >> 8;
  f.init.bcntl = len & 0xff;

  // Init packet
  psz = MIN(sizeof(f.init.data), l);
  memcpy(f.init.data, p, psz);
  queue_u2f_pkt(&f);
  l -= psz;
  p += psz;

  // Cont packet(s)
  for (; l > 0; l -= psz, p += psz) {
    // debugLog(0, "", "send_u2fhid_msg con");
    memzero(&f.cont.data, sizeof(f.cont.data));
    f.cont.seq = seq++;
    psz = MIN(sizeof(f.cont.data), l);
    memcpy(f.cont.data, p, psz);
    queue_u2f_pkt(&f);
  }

  if (data + len != p) {
    debugLog(0, "", "send_u2fhid_msg is bad");
    debugInt(data + len - p);
  }
}

void send_u2fhid_error(uint32_t fcid, uint8_t err) {
  U2FHID_FRAME f = {0};

  memzero(&f, sizeof(f));
  f.cid = fcid;
  f.init.cmd = U2FHID_ERROR;
  f.init.bcntl = 1;
  f.init.data[0] = err;
  queue_u2f_pkt(&f);
}

void u2f_version(const APDU *a) {
  if (APDU_LEN(*a) != 0) {
    debugLog(0, "", "u2f version - badlen");
    send_u2f_error(U2F_SW_WRONG_LENGTH);
    return;
  }

  // INCLUDES SW_NO_ERROR
  static const uint8_t version_response[] = {'U', '2', 'F',  '_',
                                             'V', '2', 0x90, 0x00};
  debugLog(0, "", "u2f version");
  send_u2f_msg(version_response, sizeof(version_response));
}

static void getReadableAppId(const uint8_t appid[U2F_APPID_SIZE],
                             const char **appname) {
  static char buf[8 + 2 + 8 + 1];

  for (unsigned int i = 0; i < sizeof(u2f_well_known) / sizeof(U2FWellKnown);
       i++) {
    if (memcmp(appid, u2f_well_known[i].appid, U2F_APPID_SIZE) == 0) {
      *appname = u2f_well_known[i].appname;
      return;
    }
  }

  data2hex(appid, 4, &buf[0]);
  buf[8] = buf[9] = '.';
  data2hex(appid + (U2F_APPID_SIZE - 4), 4, &buf[10]);
  *appname = buf;
}

static const HDNode *getDerivedNode(uint32_t *address_n,
                                    size_t address_n_count) {
  static CONFIDENTIAL HDNode node;
  if (!config_getU2FRoot(&node)) {
    layoutHome();
    debugLog(0, "", "ERR: Device not init");
    return 0;
  }
  if (!address_n || address_n_count == 0) {
    return &node;
  }
  for (size_t i = 0; i < address_n_count; i++) {
    if (hdnode_private_ckd(&node, address_n[i]) == 0) {
      layoutHome();
      debugLog(0, "", "ERR: Derive private failed");
      return 0;
    }
  }
  return &node;
}

static const HDNode *generateKeyHandle(const uint8_t app_id[],
                                       uint8_t key_handle[]) {
  uint8_t keybase[U2F_APPID_SIZE + KEY_PATH_LEN] = {0};

  // Derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
  uint32_t key_path[KEY_PATH_ENTRIES] = {0};
  for (uint32_t i = 0; i < KEY_PATH_ENTRIES; i++) {
    // high bit for hardened keys
    key_path[i] = 0x80000000 | random32();
  }

  // First half of keyhandle is key_path
  memcpy(key_handle, key_path, KEY_PATH_LEN);

  // prepare keypair from /random data
  const HDNode *node = getDerivedNode(key_path, KEY_PATH_ENTRIES);
  if (!node) return NULL;

  // For second half of keyhandle
  // Signature of app_id and random data
  memcpy(&keybase[0], app_id, U2F_APPID_SIZE);
  memcpy(&keybase[U2F_APPID_SIZE], key_handle, KEY_PATH_LEN);
  hmac_sha256(node->private_key, sizeof(node->private_key), keybase,
              sizeof(keybase), &key_handle[KEY_PATH_LEN]);

  // Done!
  return node;
}

static const HDNode *validateKeyHandle(const uint8_t app_id[],
                                       const uint8_t key_handle[]) {
  uint32_t key_path[KEY_PATH_ENTRIES] = {0};
  memcpy(key_path, key_handle, KEY_PATH_LEN);
  for (unsigned int i = 0; i < KEY_PATH_ENTRIES; i++) {
    // check high bit for hardened keys
    if (!(key_path[i] & 0x80000000)) {
      return NULL;
    }
  }

  const HDNode *node = getDerivedNode(key_path, KEY_PATH_ENTRIES);
  if (!node) return NULL;

  uint8_t keybase[U2F_APPID_SIZE + KEY_PATH_LEN] = {0};
  memcpy(&keybase[0], app_id, U2F_APPID_SIZE);
  memcpy(&keybase[U2F_APPID_SIZE], key_handle, KEY_PATH_LEN);

  uint8_t hmac[SHA256_DIGEST_LENGTH] = {0};
  hmac_sha256(node->private_key, sizeof(node->private_key), keybase,
              sizeof(keybase), hmac);

  if (memcmp(&key_handle[KEY_PATH_LEN], hmac, SHA256_DIGEST_LENGTH) != 0)
    return NULL;

  // Done!
  return node;
}

void u2f_register(const APDU *a) {
  static U2F_REGISTER_REQ last_req;
  const U2F_REGISTER_REQ *req = (U2F_REGISTER_REQ *)a->data;

  if (!config_isInitialized()) {
    send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
    return;
  }

  // Validate basic request parameters
  debugLog(0, "", "u2f register");
  if (APDU_LEN(*a) != sizeof(U2F_REGISTER_REQ)) {
    debugLog(0, "", "u2f register - badlen");
    send_u2f_error(U2F_SW_WRONG_LENGTH);
    return;
  }

  // If this request is different from last request, reset state machine
  if (memcmp(&last_req, req, sizeof(last_req)) != 0) {
    memcpy(&last_req, req, sizeof(last_req));
    last_req_state = INIT;
  }

  // First Time request, return not present and display request dialog
  if (last_req_state == INIT) {
    // error: testof-user-presence is required
    buttonUpdate();  // Clear button state
    if (0 == memcmp(req->appId, BOGUS_APPID_CHROME, U2F_APPID_SIZE) ||
        0 == memcmp(req->appId, BOGUS_APPID_FIREFOX, U2F_APPID_SIZE)) {
      if (cid == last_good_auth_check_cid) {
        layoutDialog(&bmp_icon_warning, NULL, _("OK"), NULL,
                     _("Already registered."), NULL, _("This U2F device is"),
                     _("already registered"), _("in this application."), NULL);
      } else {
        layoutDialog(&bmp_icon_warning, NULL, _("OK"), NULL,
                     _("Not registered."), NULL, _("Another U2F device"),
                     _("was used to register"), _("in this application."),
                     NULL);
      }
    } else {
      const char *appname = NULL;
      getReadableAppId(req->appId, &appname);
      layoutU2FDialog(_("Register"), appname);
    }
    last_req_state = REG;
  }

  // Still awaiting Keypress
  if (last_req_state == REG) {
    // error: testof-user-presence is required
    send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
    dialog_timeout = U2F_TIMEOUT;
    return;
  }

  // Buttons said yes
  if (last_req_state == REG_PASS) {
    uint8_t data[sizeof(U2F_REGISTER_RESP) + 2] = {0};
    U2F_REGISTER_RESP *resp = (U2F_REGISTER_RESP *)&data;
    memzero(data, sizeof(data));

    resp->registerId = U2F_REGISTER_ID;
    resp->keyHandleLen = KEY_HANDLE_LEN;
    // Generate keypair for this appId
    const HDNode *node =
        generateKeyHandle(req->appId, (uint8_t *)&resp->keyHandleCertSig);

    if (!node) {
      debugLog(0, "", "getDerivedNode Fail");
      send_u2f_error(U2F_SW_WRONG_DATA);  // error:bad key handle
      return;
    }

    ecdsa_get_public_key65(node->curve->params, node->private_key,
                           (uint8_t *)&resp->pubKey);

    memcpy(resp->keyHandleCertSig + resp->keyHandleLen, U2F_ATT_CERT,
           sizeof(U2F_ATT_CERT));

    uint8_t sig[64] = {0};
    U2F_REGISTER_SIG_STR sig_base = {0};
    sig_base.reserved = 0;
    memcpy(sig_base.appId, req->appId, U2F_APPID_SIZE);
    memcpy(sig_base.chal, req->chal, U2F_CHAL_SIZE);
    memcpy(sig_base.keyHandle, &resp->keyHandleCertSig, KEY_HANDLE_LEN);
    memcpy(sig_base.pubKey, &resp->pubKey, U2F_PUBKEY_LEN);
    if (ecdsa_sign(&nist256p1, HASHER_SHA2, U2F_ATT_PRIV_KEY,
                   (uint8_t *)&sig_base, sizeof(sig_base), sig, NULL,
                   NULL) != 0) {
      send_u2f_error(U2F_SW_WRONG_DATA);
      return;
    }

    // Where to write the signature in the response
    uint8_t *resp_sig =
        resp->keyHandleCertSig + resp->keyHandleLen + sizeof(U2F_ATT_CERT);
    // Convert to der for the response
    const uint8_t sig_len = ecdsa_sig_to_der(sig, resp_sig);

    // Append success bytes
    memcpy(resp->keyHandleCertSig + resp->keyHandleLen + sizeof(U2F_ATT_CERT) +
               sig_len,
           "\x90\x00", 2);

    int l = 1 /* registerId */ + U2F_PUBKEY_LEN + 1 /* keyhandleLen */ +
            resp->keyHandleLen + sizeof(U2F_ATT_CERT) + sig_len + 2;

    last_req_state = INIT;
    dialog_timeout = 0;
    send_u2f_msg(data, l);
    return;
  }

  // Didnt expect to get here
  dialog_timeout = 0;
}

void u2f_authenticate(const APDU *a) {
  const U2F_AUTHENTICATE_REQ *req = (U2F_AUTHENTICATE_REQ *)a->data;
  static U2F_AUTHENTICATE_REQ last_req;

  if (!config_isInitialized()) {
    send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
    return;
  }

  if (APDU_LEN(*a) < 64) {  /// FIXME: decent value
    debugLog(0, "", "u2f authenticate - badlen");
    send_u2f_error(U2F_SW_WRONG_LENGTH);
    return;
  }

  if (req->keyHandleLen != KEY_HANDLE_LEN) {
    debugLog(0, "", "u2f auth - bad keyhandle len");
    send_u2f_error(U2F_SW_WRONG_DATA);  // error:bad key handle
    return;
  }

  const HDNode *node = validateKeyHandle(req->appId, req->keyHandle);

  if (!node) {
    debugLog(0, "", "u2f auth - bad keyhandle len");
    send_u2f_error(U2F_SW_WRONG_DATA);  // error:bad key handle
    return;
  }

  if (a->p1 == U2F_AUTH_CHECK_ONLY) {
    debugLog(0, "", "u2f authenticate check");
    // This is a success for a good keyhandle
    // A failed check would have happened earlier
    // error: testof-user-presence is required
    send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
    last_good_auth_check_cid = cid;
    return;
  }

  if (a->p1 != U2F_AUTH_ENFORCE) {
    debugLog(0, "", "u2f authenticate unknown");
    // error:bad key handle
    send_u2f_error(U2F_SW_WRONG_DATA);
    return;
  }

  debugLog(0, "", "u2f authenticate enforce");

  if (memcmp(&last_req, req, sizeof(last_req)) != 0) {
    memcpy(&last_req, req, sizeof(last_req));
    last_req_state = INIT;
  }

  if (last_req_state == INIT) {
    // error: testof-user-presence is required
    buttonUpdate();  // Clear button state
    const char *appname = NULL;
    getReadableAppId(req->appId, &appname);
    layoutU2FDialog(_("Authenticate"), appname);
    last_req_state = AUTH;
  }

  // Awaiting Keypress
  if (last_req_state == AUTH) {
    // error: testof-user-presence is required
    send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
    dialog_timeout = U2F_TIMEOUT;
    return;
  }

  // Buttons said yes
  if (last_req_state == AUTH_PASS) {
    uint8_t buf[(sizeof(U2F_AUTHENTICATE_RESP)) + 2] = {0};
    U2F_AUTHENTICATE_RESP *resp = (U2F_AUTHENTICATE_RESP *)&buf;

    const uint32_t ctr = config_nextU2FCounter();
    resp->flags = U2F_AUTH_FLAG_TUP;
    resp->ctr[0] = ctr >> 24 & 0xff;
    resp->ctr[1] = ctr >> 16 & 0xff;
    resp->ctr[2] = ctr >> 8 & 0xff;
    resp->ctr[3] = ctr & 0xff;

    // Build and sign response
    U2F_AUTHENTICATE_SIG_STR sig_base = {0};
    uint8_t sig[64] = {0};
    memcpy(sig_base.appId, req->appId, U2F_APPID_SIZE);
    sig_base.flags = resp->flags;
    memcpy(sig_base.ctr, resp->ctr, 4);
    memcpy(sig_base.chal, req->chal, U2F_CHAL_SIZE);
    if (ecdsa_sign(&nist256p1, HASHER_SHA2, node->private_key,
                   (uint8_t *)&sig_base, sizeof(sig_base), sig, NULL,
                   NULL) != 0) {
      send_u2f_error(U2F_SW_WRONG_DATA);
      return;
    }

    // Copy DER encoded signature into response
    const uint8_t sig_len = ecdsa_sig_to_der(sig, resp->sig);

    // Append OK
    memcpy(buf + sizeof(U2F_AUTHENTICATE_RESP) - U2F_MAX_EC_SIG_SIZE + sig_len,
           "\x90\x00", 2);
    last_req_state = INIT;
    dialog_timeout = 0;
    send_u2f_msg(
        buf, sizeof(U2F_AUTHENTICATE_RESP) - U2F_MAX_EC_SIG_SIZE + sig_len + 2);
  }
}

void send_u2f_error(const uint16_t err) {
  uint8_t data[2] = {0};
  data[0] = err >> 8 & 0xFF;
  data[1] = err & 0xFF;
  send_u2f_msg(data, 2);
}

void send_u2f_msg(const uint8_t *data, const uint32_t len) {
  send_u2fhid_msg(U2FHID_MSG, data, len);
}
