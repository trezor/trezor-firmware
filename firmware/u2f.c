/*
 * This file is part of the TREZOR project.
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


#include <string.h>
#include <ecdsa.h>

#include "debug.h"
#include "storage.h"
#include "bip32.h"
#include "layout2.h"
#include "usb.h"
#include "buttons.h"
#include "trezor.h"
#include "nist256p1.h"
#include "rng.h"

#include "u2f/u2f.h"
#include "u2f/u2f_hid.h"
#include "u2f/u2f_keys.h"
#include "u2f.h"

#define MIN(a, b) (((a) < (b)) ? (a) : (b))

// About 1/2 Second according to values used in protect.c
#define U2F_TIMEOUT 840000/2
#define U2F_OUT_PKT_BUFFER_LEN 128

// Initialise without a cid
static uint32_t cid = CID_BROADCAST;

// Circular Output buffer
static uint32_t u2f_out_start = 0;
static uint32_t u2f_out_end = 0;
static uint8_t u2f_out_packets[U2F_OUT_PKT_BUFFER_LEN][HID_RPT_SIZE];

#define U2F_PUBKEY_LEN 65
#define KEY_HANDLE_LEN 64

// Auth/Register request state machine
typedef enum {
	INIT = 0,
	BTN_NO = 1,
	BTN_YES = 2,
	AUTH = 10,
	AUTH_FAIL = 11,
	AUTH_PASS = 12,
	REG = 20,
	REG_FAIL = 21,
	REG_PASS = 22
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

uint8_t buttonState(void)
{
	buttonUpdate();

	if ((button.NoDown > 10) || button.NoUp)
		return BTN_NO;
	if ((button.YesDown > 10) || button.YesUp)
		return BTN_YES;
	return 0;
}

void int2hex(uint8_t *dst, const uint32_t i)
{
	dst[0] = '0' + ((i >> 28) & 0x0F);
	dst[1] = '0' + ((i >> 24) & 0x0F);
	dst[2] = '0' + ((i >> 20) & 0x0F);
	dst[3] = '0' + ((i >> 16) & 0x0F);
	dst[4] = '0' + ((i >> 12) & 0x0F);
	dst[5] = '0' + ((i >> 8) & 0x0F);
	dst[6] = '0' + ((i >> 4) & 0x0F);
	dst[7] = '0' + (i & 0x0F);
	dst[8] = '\0';

	int t = 0;
	for (; t < 8; t++) {
		if (dst[t] > '9')
			dst[t] += 7; // 'A'-'9'+1
	}
}

char *debugInt(const uint32_t i)
{
	static uint8_t n = 0;
	static uint8_t id[8][9];
	int2hex(id[n], i);
	debugLog(0, "", (const char *)id[n]);
	char *ret = (char *)id[n];
	n = (n + 1) % 8;
	return ret;
}

static uint32_t dialog_timeout = 0;

void LayoutHomeAfterTimeout(void)
{
	static bool timeoutLock = false;

	if (timeoutLock || dialog_timeout == 0)
		return; // Dialog has cleared or already in loop

	timeoutLock = true;
	U2F_STATE rs = last_req_state;
	U2F_STATE bs = INIT;
	while (dialog_timeout-- && rs == last_req_state && bs == 0) {
		usbPoll(); // may trigger new request
		bs = buttonState();
	}
	timeoutLock = false;

	if (rs != last_req_state)
		return; // Reset by new request don't clear screen

	if (dialog_timeout == 0) {
		last_req_state += BTN_NO; // Timeout is like button no
	}
	else {
		last_req_state += bs;
		dialog_timeout = 0;
	}

	layoutHome();
}

uint32_t next_cid(void)
{
	// extremely unlikely but hey
	do {
		cid = random32();
	} while (cid == 0 || cid == CID_BROADCAST);
	return cid;
}

void u2fhid_read(const U2FHID_FRAME *f)
{
	static uint8_t seq, cmd;
	static uint32_t len;
	static uint8_t *buf_ptr;
	static uint8_t buf[7609];

	if ((f->cid != CID_BROADCAST) && (f->cid != cid)) {
		return; // Not for us
	}

	if (f->type & TYPE_INIT) {
		seq = 0;
		buf_ptr = buf;
		len = MSG_LEN(*f);
		cmd = f->type;
		memcpy(buf_ptr, f->init.data, sizeof(f->init.data));
		buf_ptr += sizeof(f->init.data);
	}
	else {
		if (f->cont.seq == seq) {
			seq++;
			memcpy(buf_ptr, f->cont.data, sizeof(f->cont.data));
			buf_ptr += sizeof(f->cont.data);
		}
		else {
			return send_u2fhid_error(ERR_INVALID_SEQ);
		}
	}

	// Broadcast is reserved for init
	if (cid == CID_BROADCAST && cmd != U2FHID_INIT)
		return;

	// Check length isnt bigger than spec max
	if (len > sizeof(buf))
		return send_u2fhid_error(ERR_INVALID_LEN);

	// Do we need to wait for more data
	if ((buf_ptr - buf) < (signed)len) {
		// debugLog(0, "", "u2fhid_read wait");
		return;
	}

	// We have all the data
	switch (cmd) {
		case U2FHID_PING:
			u2fhid_ping(buf, len);
			break;
		case U2FHID_MSG:
			u2fhid_msg((APDU *)buf, len);
			break;
		case U2FHID_LOCK:
			u2fhid_lock(buf, len);
			break;
		case U2FHID_INIT:
			u2fhid_init((const U2FHID_INIT_REQ *)buf);
			break;
		case U2FHID_WINK:
			u2fhid_wink(buf, len);
			break;
		// case U2FHID_SYNC:
		//	u2fhid_sync(buf, len);
			break;
		default:
			send_u2fhid_error(ERR_INVALID_CMD);
			break;
	}
}

void u2fhid_ping(const uint8_t *buf, uint32_t len)
{
	debugLog(0, "", "u2fhid_ping");
	send_u2fhid_msg(U2FHID_PING, buf, len);
}

void u2fhid_wink(const uint8_t *buf, uint32_t len)
{
	debugLog(0, "", "u2fhid_wink");
	(void)buf;

	if (len > 0)
		return send_u2fhid_error(ERR_INVALID_LEN);

	if (dialog_timeout > 0)
		dialog_timeout = U2F_TIMEOUT;

	U2FHID_FRAME f;
	bzero(&f, sizeof(f));
	f.cid = cid;
	f.init.cmd = U2FHID_WINK;
	f.init.bcntl = 0;
	queue_u2f_pkt(&f);
}

void u2fhid_sync(const uint8_t *buf, uint32_t len)
{
	debugLog(0, "", "u2fhid_sync");
	(void)buf;

	if (len > 0)
		return send_u2fhid_error(ERR_INVALID_LEN);

	// Abort things.
	dialog_timeout = 0;
}

void u2fhid_lock(const uint8_t *buf, uint32_t len)
{
	debugLog(0, "", "u2fhid_lock");
	(void)buf;
	(void)len;
	send_u2fhid_error(ERR_INVALID_CMD);
}

void u2fhid_init(const U2FHID_INIT_REQ *init_req)
{
	debugLog(0, "", "u2fhid_init");
	U2FHID_FRAME f;
	U2FHID_INIT_RESP *resp = (U2FHID_INIT_RESP *)f.init.data;

	bzero(&f, sizeof(f));
	f.cid = CID_BROADCAST;
	f.init.cmd = U2FHID_INIT;
	f.init.bcnth = 0;
	f.init.bcntl = sizeof(U2FHID_INIT_RESP);

	memcpy(resp->nonce, init_req->nonce, sizeof(init_req->nonce));
	resp->cid = next_cid();
	resp->versionInterface = U2FHID_IF_VERSION;
	resp->versionMajor = VERSION_MAJOR;
	resp->versionMinor = VERSION_MINOR;
	resp->versionBuild = VERSION_PATCH;
	resp->capFlags = CAPFLAG_WINK;

	queue_u2f_pkt(&f);
}

void queue_u2f_pkt(const U2FHID_FRAME *u2f_pkt)
{
	// debugLog(0, "", "u2f_write_pkt");
	uint32_t next = (u2f_out_end + 1) % U2F_OUT_PKT_BUFFER_LEN;
	if (u2f_out_start == next) {
		debugLog(0, "", "u2f_write_pkt full");
		return; // Buffer full :(
	}
	memcpy(u2f_out_packets[u2f_out_end], u2f_pkt, HID_RPT_SIZE);
	u2f_out_end = next;
}

uint8_t *u2f_out_data(void)
{
	if (u2f_out_start == u2f_out_end)
		return NULL; // No data
	// debugLog(0, "", "u2f_out_data");
	uint32_t t = u2f_out_start;
	u2f_out_start = (u2f_out_start + 1) % U2F_OUT_PKT_BUFFER_LEN;
	return u2f_out_packets[t];
}

void u2fhid_msg(const APDU *a, uint32_t len)
{
	static bool lock = false;

	if ((APDU_LEN(*a) + sizeof(APDU)) > len) {
		debugLog(0, "", "BAD APDU LENGTH");
		debugInt(APDU_LEN(*a));
		debugInt(len);
		return;
	}

	// Very crude locking, incase another message comes in while we wait.  This
	// actually can probably be removed as no code inside calls usbPoll anymore
	if (lock)
		return send_u2fhid_error(ERR_CHANNEL_BUSY);

	lock = true;

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

	lock = false;

	LayoutHomeAfterTimeout();
}

void send_u2fhid_msg(const uint8_t cmd, const uint8_t *data, const uint32_t len)
{
	U2FHID_FRAME f;
	uint8_t *p = (uint8_t *)data;
	uint32_t l = len;
	uint32_t psz;
	uint8_t seq = 0;

	// debugLog(0, "", "send_u2fhid_msg");

	bzero(&f, sizeof(f));
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
		bzero(&f.cont.data, sizeof(f.cont.data));
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

void send_u2fhid_error(uint8_t err)
{
	U2FHID_FRAME f;

	bzero(&f, sizeof(f));
	f.cid = cid;
	f.init.cmd = U2FHID_ERROR;
	f.init.bcntl = 1;
	f.init.data[0] = err;
	queue_u2f_pkt(&f);
}

void u2f_version(const APDU *a)
{
	// INCLUDES SW_NO_ERROR
	static const uint8_t version_response[] = {'U', '2', 'F',  '_',
						   'V', '2', 0x90, 0x00};
	(void)a;
	debugLog(0, "", "u2f version");
	send_u2f_msg(version_response, sizeof(version_response));
}

const HDNode *getDerivedNode(uint32_t *address_n, size_t address_n_count)
{
	static HDNode node;
	if (!storage_getRootNode(&node)) {
		layoutHome();
		debugLog(0, "", "ERR: Device not init");
		return 0;
	}
	if (!address_n || address_n_count == 0) {
		return &node;
	}
	if (hdnode_private_ckd_cached(&node, address_n, address_n_count) == 0) {
		layoutHome();
		debugLog(0, "", "ERR: Derive private failed");
		return 0;
	}
	return &node;
}

const HDNode *generateKeyHandle(const uint8_t app_id[], uint8_t key_handle[])
{
		uint8_t keybase[64];

		// Derivation path is m/'U2F/'r/'r/'r/'r/'r/'r/'r/'r
		uint32_t i, key_path[9];
		key_path[0] = U2F_KEY_PATH;
		for (i = 1; i < 9; i++) {
			// high bit for hardened keys
			key_path[i]= 0x80000000 | random32();
		}

		// First half of keyhandle is key_path
		memcpy(key_handle, &key_path[1], 32);

		// prepare keypair from /random data
		const HDNode *node =
			getDerivedNode(key_path, sizeof(key_path) / sizeof(uint32_t));

		// For second half of keyhandle
		// Signature of app_id and random data
		memcpy(&keybase[0], app_id, 32);
		memcpy(&keybase[32], key_handle, 32);
		uint8_t sig[64];
		ecdsa_sign(&nist256p1, node->private_key,
			(uint8_t *)&keybase, sizeof(keybase), sig,
			NULL);

		// Copy 32 bytes of signature into keyhandle
		memcpy(&key_handle[32], sig, 32);

		// Done!
		return node;
}


const HDNode *validateKeyHandle(const uint8_t app_id[], const uint8_t key_handle[])
{
	uint32_t key_path[9];
	key_path[0] = U2F_KEY_PATH;
	memcpy(&key_path[1], key_handle, 32);

	const HDNode *node =
		getDerivedNode(key_path, sizeof(key_path) / sizeof(uint32_t));

	uint8_t keybase[64];
	memcpy(&keybase[0], app_id, 32);
	memcpy(&keybase[32], key_handle, 32);


	uint8_t sig[64];
	ecdsa_sign(&nist256p1, node->private_key,
			(uint8_t *)&keybase, sizeof(keybase), sig,
			NULL);

	if (memcmp(&key_handle[32], sig, 32) !=0)
		return NULL;

	// Done!
	return node;
}


void u2f_register(const APDU *a)
{
	static U2F_REGISTER_REQ last_req;
	const U2F_REGISTER_REQ *req = (U2F_REGISTER_REQ *)a->data;

	// Validate basic request parameters
	debugLog(0, "", "u2f register");
	if (APDU_LEN(*a) != sizeof(U2F_REGISTER_REQ)) {
		debugLog(0, "", "u2f register - badlen");
		send_u2f_error(U2F_SW_WRONG_DATA);
		return;
	}

	// If this request is different from last request, reset state machine
	if (memcmp(&last_req, req, sizeof(last_req)) != 0) {
		memcpy(&last_req, req, sizeof(last_req));
		last_req_state = INIT;
	}

	// First Time request, return not present and display request dialog
	if (last_req_state == 0) {
		// wake up crypto system to be ready for signing
		getDerivedNode(NULL, 0);
		// error: testof-user-presence is required
		send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
		buttonUpdate(); // Clear button state
		layoutDialog(DIALOG_ICON_QUESTION, "Cancel", "Register",
				NULL, "Register U2F", "security key", "", "", "", NULL);
		dialog_timeout = U2F_TIMEOUT;
		last_req_state = REG;
		return;
	}

	// Still awaiting Keypress
	if (last_req_state == REG) {
		// error: testof-user-presence is required
		send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
		dialog_timeout = U2F_TIMEOUT;
		return;
	}

	// Buttons said no!
	if (last_req_state == REG_FAIL) {
		send_u2f_error(U2F_SW_WRONG_DATA); // error:bad key handle
		return;
	}

	// Buttons said yes
	if (last_req_state == REG_PASS) {
		uint8_t data[sizeof(U2F_REGISTER_RESP) + 2];
		U2F_REGISTER_RESP *resp = (U2F_REGISTER_RESP *)&data;
		bzero(data, sizeof(data));


		resp->registerId = U2F_REGISTER_ID;
		resp->keyHandleLen = KEY_HANDLE_LEN;
		// Generate keypair for this appId
		const HDNode *node =
			generateKeyHandle(req->appId, (uint8_t*)&resp->keyHandleCertSig);

		if (!node) {
			debugLog(0, "", "getDerivedNode Fail");
			send_u2f_error(U2F_SW_WRONG_DATA); // error:bad key handle
			return;
		}

		ecdsa_get_public_key65(&nist256p1, node->private_key,
				       (uint8_t *)&resp->pubKey);

		memcpy(resp->keyHandleCertSig + resp->keyHandleLen,
		       U2F_ATT_CERT, sizeof(U2F_ATT_CERT));

		uint8_t sig[64];
		U2F_REGISTER_SIG_STR sig_base;
		sig_base.reserved = 0;
		memcpy(sig_base.appId, req->appId, U2F_APPID_SIZE);
		memcpy(sig_base.chal, req->chal, U2F_CHAL_SIZE);
		memcpy(sig_base.keyHandle, &resp->keyHandleCertSig, KEY_HANDLE_LEN);
		memcpy(sig_base.pubKey, &resp->pubKey, U2F_PUBKEY_LEN);
		ecdsa_sign(&nist256p1, U2F_ATT_PRIV_KEY, (uint8_t *)&sig_base,
			   sizeof(sig_base), sig, NULL);

		// Where to write the signature in the response
		uint8_t *resp_sig = resp->keyHandleCertSig +
				    resp->keyHandleLen + sizeof(U2F_ATT_CERT);
		// Convert to der for the response
		const uint8_t sig_len = ecdsa_sig_to_der(sig, resp_sig);

		// Append success bytes
		memcpy(resp->keyHandleCertSig + resp->keyHandleLen +
			   sizeof(U2F_ATT_CERT) + sig_len,
		       "\x90\x00", 2);

		int l = 1 /* registerId */ + U2F_PUBKEY_LEN +
			1 /* keyhandleLen */ + resp->keyHandleLen +
			sizeof(U2F_ATT_CERT) + sig_len + 2;

		send_u2f_msg(data, l);
		return;
	}

	// Didnt expect to get here
	dialog_timeout = 0;
}

void u2f_authenticate(const APDU *a)
{
	const U2F_AUTHENTICATE_REQ *req = (U2F_AUTHENTICATE_REQ *)a->data;
	static U2F_AUTHENTICATE_REQ last_req;

	if (APDU_LEN(*a) < 64) { /// FIXME: decent value
		debugLog(0, "", "u2f authenticate - badlen");
		send_u2f_error(U2F_SW_WRONG_DATA);
		return;
	}

	if (req->keyHandleLen != KEY_HANDLE_LEN) {
		debugLog(0, "", "u2f auth - bad keyhandle len");
		send_u2f_error(U2F_SW_WRONG_DATA); // error:bad key handle
		return;
	}

	const HDNode *node =
	    validateKeyHandle(req->appId, req->keyHandle);

	if (!node) {
		debugLog(0, "", "u2f auth - bad keyhandle len");
		send_u2f_error(U2F_SW_WRONG_DATA); // error:bad key handle
		return;
	}

	if (a->p1 == U2F_AUTH_CHECK_ONLY) {
		debugLog(0, "", "u2f authenticate check");
		// This is a success for a good keyhandle
		// A failed check would have happened earlier
		// error: testof-user-presence is required
		send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
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
		send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
		buttonUpdate(); // Clear button state
		layoutDialog(DIALOG_ICON_QUESTION, "Cancel", "Authenticate", NULL,
				"Authenticate U2F", "security key", "", "", "", NULL);
		dialog_timeout = U2F_TIMEOUT;
		last_req_state = AUTH;
		return;
	}

	// Awaiting Keypress
	if (last_req_state == AUTH) {
		// error: testof-user-presence is required
		send_u2f_error(U2F_SW_CONDITIONS_NOT_SATISFIED);
		dialog_timeout = U2F_TIMEOUT;
		return;
	}

	// Buttons said no!
	if (last_req_state == AUTH_FAIL) {
		send_u2f_error(
			U2F_SW_WRONG_DATA); // error:bad key handle
		return;
	}

	// Buttons said yes
	if (last_req_state == AUTH_PASS) {
		uint8_t buf[sizeof(U2F_AUTHENTICATE_RESP) + 2];
		U2F_AUTHENTICATE_RESP *resp =
			(U2F_AUTHENTICATE_RESP *)&buf;

		const uint32_t ctr = storage_nextU2FCounter();
		resp->flags = U2F_AUTH_FLAG_TUP;
		resp->ctr[0] = ctr >> 24 & 0xff;
		resp->ctr[1] = ctr >> 16 & 0xff;
		resp->ctr[2] = ctr >> 8 & 0xff;
		resp->ctr[3] = ctr & 0xff;

		// Build and sign response
		U2F_AUTHENTICATE_SIG_STR sig_base;
		uint8_t sig[64];
		memcpy(sig_base.appId, req->appId, U2F_APPID_SIZE);
		sig_base.flags = resp->flags;
		memcpy(sig_base.ctr, resp->ctr, 4);
		memcpy(sig_base.chal, req->chal, U2F_CHAL_SIZE);
		ecdsa_sign(&nist256p1, node->private_key,
			   (uint8_t *)&sig_base, sizeof(sig_base), sig,
			   NULL);

		// Copy DER encoded signature into response
		const uint8_t sig_len = ecdsa_sig_to_der(sig, resp->sig);

		// Append OK
		memcpy(buf + sizeof(U2F_AUTHENTICATE_RESP) -
			   U2F_MAX_EC_SIG_SIZE + sig_len,
			   "\x90\x00", 2);
		send_u2f_msg(buf, sizeof(U2F_AUTHENTICATE_RESP) -
					  U2F_MAX_EC_SIG_SIZE + sig_len +
					  2);
		last_req_state = INIT;
	}
}

void send_u2f_error(const uint16_t err)
{
	uint8_t data[2];
	data[0] = err >> 8 & 0xFF;
	data[1] = err & 0xFF;
	send_u2f_msg(data, 2);
}

void send_u2f_msg(const uint8_t *data, const uint32_t len)
{
	send_u2fhid_msg(U2FHID_MSG, data, len);
}
