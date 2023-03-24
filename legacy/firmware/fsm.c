/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include <libopencm3/stm32/flash.h>

#include "address.h"
#include "aes/aes.h"
#include "base58.h"
#include "bip32.h"
#include "bip39.h"
#include "coins.h"
#include "config.h"
#include "crypto.h"
#include "curves.h"
#include "debug.h"
#include "ecdsa.h"
#include "fsm.h"
#include "fw_signatures.h"
#include "gettext.h"
#include "hmac.h"
#include "layout2.h"
#include "memory.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "oled.h"
#include "pinmatrix.h"
#include "protect.h"
#include "recovery.h"
#include "reset.h"
#include "rng.h"
#include "secp256k1.h"
#include "signing.h"
#include "supervise.h"
#include "timer.h"
#include "transaction.h"
#include "trezor.h"
#include "usb.h"
#include "util.h"

#if !BITCOIN_ONLY
#include "ethereum.h"
#include "ethereum_definitions.h"
#include "ethereum_networks.h"
#include "nem.h"
#include "nem2.h"
#include "stellar.h"
#endif

#if EMULATOR
#include <stdio.h>
#endif

// message methods

static uint8_t msg_resp[MSG_OUT_DECODED_SIZE] __attribute__((aligned));

// Authorization message type triggered by DoPreauthorized.
static MessageType authorization_type = 0;

static uint32_t unlock_path = 0;

#define RESP_INIT(TYPE)                                                    \
  TYPE *resp = (TYPE *)(void *)msg_resp;                                   \
  _Static_assert(sizeof(msg_resp) >= sizeof(TYPE), #TYPE " is too large"); \
  memzero(resp, sizeof(TYPE));

#define CHECK_INITIALIZED                                      \
  if (!config_isInitialized()) {                               \
    fsm_sendFailure(FailureType_Failure_NotInitialized, NULL); \
    return;                                                    \
  }

#define CHECK_NOT_INITIALIZED                                             \
  if (config_isInitialized()) {                                           \
    fsm_sendFailure(FailureType_Failure_UnexpectedMessage,                \
                    _("Device is already initialized. Use Wipe first.")); \
    return;                                                               \
  }

#define CHECK_PIN          \
  if (!protectPin(true)) { \
    layoutHome();          \
    return;                \
  }

#define CHECK_PIN_UNCACHED  \
  if (!protectPin(false)) { \
    layoutHome();           \
    return;                 \
  }

#define CHECK_UNLOCKED                                              \
  if (!session_isUnlocked()) {                                      \
    fsm_sendFailure(FailureType_Failure_ProcessError, _("Locked")); \
    layoutHome();                                                   \
    return;                                                         \
  }

#define CHECK_PARAM(cond, errormsg)                             \
  if (!(cond)) {                                                \
    fsm_sendFailure(FailureType_Failure_DataError, (errormsg)); \
    layoutHome();                                               \
    return;                                                     \
  }

void fsm_sendSuccess(const char *text) {
  RESP_INIT(Success);
  if (text) {
    resp->has_message = true;
    strlcpy(resp->message, text, sizeof(resp->message));
  }
  msg_write(MessageType_MessageType_Success, resp);
}

#if DEBUG_LINK
void fsm_sendFailureDebug(FailureType code, const char *text,
                          const char *source)
#else
void fsm_sendFailure(FailureType code, const char *text)
#endif
{
  if (protectAbortedByCancel) {
    protectAbortedByCancel = false;
  }
  if (protectAbortedByInitialize) {
    fsm_msgInitialize((Initialize *)0);
    protectAbortedByInitialize = false;
    return;
  }
  RESP_INIT(Failure);
  resp->has_code = true;
  resp->code = code;
  if (!text) {
    switch (code) {
      case FailureType_Failure_UnexpectedMessage:
        text = _("Unexpected message");
        break;
      case FailureType_Failure_ButtonExpected:
        text = _("Button expected");
        break;
      case FailureType_Failure_DataError:
        text = _("Data error");
        break;
      case FailureType_Failure_ActionCancelled:
        text = _("Action cancelled by user");
        break;
      case FailureType_Failure_PinExpected:
        text = _("PIN expected");
        break;
      case FailureType_Failure_PinCancelled:
        text = _("PIN cancelled");
        break;
      case FailureType_Failure_PinInvalid:
        text = _("PIN invalid");
        break;
      case FailureType_Failure_InvalidSignature:
        text = _("Invalid signature");
        break;
      case FailureType_Failure_ProcessError:
        text = _("Process error");
        break;
      case FailureType_Failure_NotEnoughFunds:
        text = _("Not enough funds");
        break;
      case FailureType_Failure_NotInitialized:
        text = _("Device not initialized");
        break;
      case FailureType_Failure_PinMismatch:
        text = _("PIN mismatch");
        break;
      case FailureType_Failure_WipeCodeMismatch:
        text = _("Wipe code mismatch");
        break;
      case FailureType_Failure_InvalidSession:
        text = _("Invalid session");
        break;
      case FailureType_Failure_FirmwareError:
        text = _("Firmware error");
        break;
    }
  }
#if DEBUG_LINK
  resp->has_message = true;
  strlcpy(resp->message, source, sizeof(resp->message));
  if (text) {
    strlcat(resp->message, text, sizeof(resp->message));
  }
#else
  if (text) {
    resp->has_message = true;
    strlcpy(resp->message, text, sizeof(resp->message));
  }
#endif
  msg_write(MessageType_MessageType_Failure, resp);
}

static const CoinInfo *fsm_getCoin(bool has_name, const char *name) {
  const CoinInfo *coin = NULL;
  if (has_name) {
    coin = coinByName(name);
  } else {
    coin = coinByName("Bitcoin");
  }
  if (!coin) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid coin name"));
    layoutHome();
    return 0;
  }
  return coin;
}

static HDNode *fsm_getDerivedNode(const char *curve, const uint32_t *address_n,
                                  size_t address_n_count,
                                  uint32_t *fingerprint) {
  static CONFIDENTIAL HDNode node;
  if (fingerprint) {
    *fingerprint = 0;
  }
  if (!config_getRootNode(&node, curve)) {
    layoutHome();
    return 0;
  }
  if (!address_n || address_n_count == 0) {
    return &node;
  }
  if (hdnode_private_ckd_cached(&node, address_n, address_n_count,
                                fingerprint) == 0) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Failed to derive private key"));
    layoutHome();
    return 0;
  }
  return &node;
}

static bool fsm_getSlip21Key(const char *path[], size_t path_count,
                             uint8_t key[32]) {
  const uint8_t *seed = config_getSeed();
  if (seed == NULL) {
    return false;
  }

  static CONFIDENTIAL Slip21Node node;
  slip21_from_seed(seed, 64, &node);
  for (size_t i = 0; i < path_count; ++i) {
    slip21_derive_path(&node, (uint8_t *)path[i], strlen(path[i]));
  }
  memcpy(key, slip21_key(&node), 32);
  memzero(&node, sizeof(node));

  return true;
}

static bool fsm_layoutAddress(const char *address, const char *desc,
                              bool ignorecase, size_t prefixlen,
                              const uint32_t *address_n, size_t address_n_count,
                              bool address_is_account,
                              const MultisigRedeemScriptType *multisig,
                              int multisig_index, uint32_t multisig_xpub_magic,
                              const CoinInfo *coin) {
  int screen = 0, screens = 2;
  if (multisig) {
    screens += 2 * cryptoMultisigPubkeyCount(multisig);
  }
  for (;;) {
    switch (screen) {
      case 0: {  // show address
        const char *display_addr = address;
        // strip cashaddr prefix
        if (prefixlen) {
          display_addr += prefixlen;
        }
        layoutAddress(display_addr, desc, false, ignorecase, address_n,
                      address_n_count, address_is_account);
        break;
      }
      case 1: {  // show QR code
        layoutAddress(address, desc, true, ignorecase, address_n,
                      address_n_count, address_is_account);
        break;
      }
      default: {  // show XPUBs
        int index = (screen - 2) / 2;
        int page = (screen - 2) % 2;
        char xpub[XPUB_MAXLEN] = {0};
        const HDNodeType *node_ptr = NULL;
        if (multisig->nodes_count) {  // use multisig->nodes
          node_ptr = &(multisig->nodes[index]);
        } else if (multisig->pubkeys_count) {  // use multisig->pubkeys
          node_ptr = &(multisig->pubkeys[index].node);
        }

        if (!node_ptr) {
          strlcat(xpub, "ERROR", sizeof(xpub));
        } else {
          HDNode node;
          if (!hdnode_from_xpub(node_ptr->depth, node_ptr->child_num,
                                node_ptr->chain_code.bytes,
                                node_ptr->public_key.bytes, coin->curve_name,
                                &node)) {
            strlcat(xpub, "ERROR", sizeof(xpub));
          } else {
            hdnode_serialize_public(&node, node_ptr->fingerprint,
                                    multisig_xpub_magic, xpub, sizeof(xpub));
          }
        }
        layoutXPUBMultisig(xpub, index, page, multisig_index == index);
        break;
      }
    }
    if (protectButton(ButtonRequestType_ButtonRequest_Address, false)) {
      return true;
    }
    if (protectAbortedByCancel || protectAbortedByInitialize) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return false;
    }
    screen = (screen + 1) % screens;
  }
}

static bool fsm_layoutPaginated(const char *description, const uint8_t *msg,
                                uint32_t len, bool is_ascii) {
  const char **str = NULL;
  const uint32_t row_len = is_ascii ? 18 : 8;
  do {
    const uint32_t show_len = MIN(len, row_len * 4);
    if (is_ascii) {
      str = split_message(msg, show_len, row_len);
    } else {
      str = split_message_hex(msg, show_len);
    }

    msg += show_len;
    len -= show_len;

    const char *label = len > 0 ? _("Next") : _("Confirm");
    layoutDialogSwipeEx(&bmp_icon_question, _("Cancel"), label, description,
                        str[0], str[1], str[2], str[3], NULL, NULL, FONT_FIXED);

    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      return false;
    }
  } while (len > 0);

  return true;
}

bool fsm_layoutSignMessage(const uint8_t *msg, uint32_t len) {
  if (is_valid_ascii(msg, len)) {
    return fsm_layoutPaginated(_("Sign message?"), msg, len, true);
  } else {
    return fsm_layoutPaginated(_("Sign binary message?"), msg, len, false);
  }
}

bool fsm_layoutVerifyMessage(const uint8_t *msg, uint32_t len) {
  if (is_valid_ascii(msg, len)) {
    return fsm_layoutPaginated(_("Verified message?"), msg, len, true);
  } else {
    return fsm_layoutPaginated(_("Verified binary message?"), msg, len, false);
  }
}

bool fsm_layoutCommitmentData(const uint8_t *msg, uint32_t len) {
  if (is_valid_ascii(msg, len)) {
    return fsm_layoutPaginated(_("Commitment data"), msg, len, true);
  } else {
    return fsm_layoutPaginated(_("Binary commitment data"), msg, len, false);
  }
}

void fsm_msgRebootToBootloader(void) {
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Do you want to"), _("restart device in"),
                    _("bootloader mode?"), NULL, NULL, NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }
  oledClear();
  oledRefresh();
  fsm_sendSuccess(_("Rebooting"));
  // make sure the outgoing message is sent
  usbFlush(500);
#if !EMULATOR
  svc_reboot_to_bootloader();
#else
  printf("Reboot!\n");
#endif
}

void fsm_abortWorkflows(void) {
  recovery_abort();
  signing_abort();
  authorization_type = 0;
  unlock_path = 0;
#if !BITCOIN_ONLY
  ethereum_signing_abort();
  stellar_signingAbort();
#endif
}

void fsm_postMsgCleanup(MessageType message_type) {
  if (message_type != MessageType_MessageType_DoPreauthorized) {
    authorization_type = 0;
  }

  if (message_type != MessageType_MessageType_UnlockPath) {
    unlock_path = 0;
  }
}

bool fsm_layoutPathWarning(void) {
  layoutDialogSwipe(&bmp_icon_warning, _("Abort"), _("Continue"), NULL,
                    _("Wrong address path"), _("for selected coin."), NULL,
                    _("Continue at your"), _("own risk!"), NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_UnknownDerivationPath,
                     false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    return false;
  }
  return true;
}

#include "fsm_msg_coin.h"
#include "fsm_msg_common.h"
#include "fsm_msg_crypto.h"
#include "fsm_msg_debug.h"

#if !BITCOIN_ONLY

#include "fsm_msg_ethereum.h"
#include "fsm_msg_nem.h"
#include "fsm_msg_stellar.h"

#endif
