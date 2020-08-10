/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
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

void fsm_msgGetPublicKey(const GetPublicKey *msg) {
  RESP_INIT(PublicKey);

  CHECK_INITIALIZED

  CHECK_PIN

  InputScriptType script_type =
      msg->has_script_type ? msg->script_type : InputScriptType_SPENDADDRESS;

  const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
  if (!coin) return;

  const char *curve = coin->curve_name;
  if (msg->has_ecdsa_curve_name) {
    curve = msg->ecdsa_curve_name;
  }
  uint32_t fingerprint;
  HDNode *node = node = fsm_getDerivedNode(curve, msg->address_n,
                                           msg->address_n_count, &fingerprint);
  if (!node) return;
  hdnode_fill_public_key(node);

  if (msg->has_show_display && msg->show_display) {
    layoutPublicKey(node->public_key);
    if (!protectButton(ButtonRequestType_ButtonRequest_PublicKey, true)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  resp->has_node = true;
  resp->node.depth = node->depth;
  resp->node.fingerprint = fingerprint;
  resp->node.child_num = node->child_num;
  resp->node.chain_code.size = 32;
  memcpy(resp->node.chain_code.bytes, node->chain_code, 32);
  resp->node.has_private_key = false;
  resp->node.has_public_key = true;
  resp->node.public_key.size = 33;
  memcpy(resp->node.public_key.bytes, node->public_key, 33);
  if (node->public_key[0] == 1) {
    /* ed25519 public key */
    resp->node.public_key.bytes[0] = 0;
  }

  resp->has_xpub = true;
  if (coin->xpub_magic && (script_type == InputScriptType_SPENDADDRESS ||
                           script_type == InputScriptType_SPENDMULTISIG)) {
    hdnode_serialize_public(node, fingerprint, coin->xpub_magic, resp->xpub,
                            sizeof(resp->xpub));
  } else if (coin->has_segwit && coin->xpub_magic_segwit_p2sh &&
             script_type == InputScriptType_SPENDP2SHWITNESS) {
    hdnode_serialize_public(node, fingerprint, coin->xpub_magic_segwit_p2sh,
                            resp->xpub, sizeof(resp->xpub));
  } else if (coin->has_segwit && coin->xpub_magic_segwit_native &&
             script_type == InputScriptType_SPENDWITNESS) {
    hdnode_serialize_public(node, fingerprint, coin->xpub_magic_segwit_native,
                            resp->xpub, sizeof(resp->xpub));
  } else {
    fsm_sendFailure(FailureType_Failure_DataError,
                    _("Invalid combination of coin and script_type"));
    layoutHome();
    return;
  }

  msg_write(MessageType_MessageType_PublicKey, resp);
  layoutHome();
}

void fsm_msgSignTx(const SignTx *msg) {
  CHECK_INITIALIZED

  CHECK_PARAM(msg->inputs_count > 0,
              _("Transaction must have at least one input"));
  CHECK_PARAM(msg->outputs_count > 0,
              _("Transaction must have at least one output"));
  CHECK_PARAM(msg->inputs_count + msg->outputs_count >= msg->inputs_count,
              _("Value overflow"));

  CHECK_PIN

  const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
  if (!coin) return;

  CHECK_PARAM((coin->decred || coin->overwintered) || !msg->has_expiry,
              _("Expiry not enabled on this coin."))
  CHECK_PARAM(coin->timestamp || !msg->has_timestamp,
              _("Timestamp not enabled on this coin."))
  CHECK_PARAM(!coin->timestamp || msg->timestamp, _("Timestamp must be set."))

  const HDNode *node = fsm_getDerivedNode(coin->curve_name, NULL, 0, NULL);
  if (!node) return;

  signing_init(msg, coin, node);
}

void fsm_msgTxAck(TxAck *msg) {
  CHECK_PARAM(msg->has_tx, _("No transaction provided"));

  signing_txack(&(msg->tx));
}

void fsm_msgGetAddress(const GetAddress *msg) {
  RESP_INIT(Address);

  CHECK_INITIALIZED

  CHECK_PIN

  const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
  if (!coin) return;
  HDNode *node = fsm_getDerivedNode(coin->curve_name, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;
  hdnode_fill_public_key(node);

  char address[MAX_ADDR_SIZE];
  if (msg->has_multisig) {  // use progress bar only for multisig
    layoutProgress(_("Computing address"), 0);
  }
  if (!compute_address(coin, msg->script_type, node, msg->has_multisig,
                       &msg->multisig, address)) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Can't encode address"));
    layoutHome();
    return;
  }

  if (msg->has_show_display && msg->show_display) {
    char desc[20] = {0};
    int multisig_index = 0;
    if (msg->has_multisig) {
      strlcpy(desc, "Multisig __ of __:", sizeof(desc));
      const uint32_t m = msg->multisig.m;
      const uint32_t n = cryptoMultisigPubkeyCount(&(msg->multisig));
      desc[9] = (m < 10) ? ' ' : ('0' + (m / 10));
      desc[10] = '0' + (m % 10);
      desc[15] = (n < 10) ? ' ' : ('0' + (n / 10));
      desc[16] = '0' + (n % 10);
      multisig_index =
          cryptoMultisigPubkeyIndex(coin, &(msg->multisig), node->public_key);
    } else {
      strlcpy(desc, _("Address:"), sizeof(desc));
    }

    if (!coin_known_path_check(coin, msg->script_type, msg->address_n_count,
                               msg->address_n, true)) {
      layoutDialogSwipe(&bmp_icon_warning, _("Abort"), _("Continue"), NULL,
                        _("Wrong address path"), _("for selected coin."), NULL,
                        _("Continue at your"), _("own risk!"), NULL);
      if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        layoutHome();
        return;
      }
    }

    bool is_cashaddr = coin->cashaddr_prefix != NULL;
    bool is_bech32 = msg->script_type == InputScriptType_SPENDWITNESS;
    if (!fsm_layoutAddress(address, desc, is_cashaddr || is_bech32,
                           is_cashaddr ? strlen(coin->cashaddr_prefix) + 1 : 0,
                           msg->address_n, msg->address_n_count, false,
                           msg->has_multisig ? &(msg->multisig) : NULL,
                           multisig_index, coin)) {
      return;
    }
  }

  strlcpy(resp->address, address, sizeof(resp->address));
  msg_write(MessageType_MessageType_Address, resp);
  layoutHome();
}

void fsm_msgSignMessage(const SignMessage *msg) {
  // CHECK_PARAM(is_ascii_only(msg->message.bytes, msg->message.size), _("Cannot
  // sign non-ASCII strings"));

  RESP_INIT(MessageSignature);

  CHECK_INITIALIZED

  layoutSignMessage(msg->message.bytes, msg->message.size);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  CHECK_PIN

  const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
  if (!coin) return;
  HDNode *node = fsm_getDerivedNode(coin->curve_name, msg->address_n,
                                    msg->address_n_count, NULL);
  if (!node) return;

  layoutProgressSwipe(_("Signing"), 0);
  if (cryptoMessageSign(coin, node, msg->script_type, msg->message.bytes,
                        msg->message.size, resp->signature.bytes) == 0) {
    resp->has_address = true;
    hdnode_fill_public_key(node);
    if (!compute_address(coin, msg->script_type, node, false, NULL,
                         resp->address)) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Error computing address"));
      layoutHome();
      return;
    }
    resp->has_signature = true;
    resp->signature.size = 65;
    msg_write(MessageType_MessageType_MessageSignature, resp);
  } else {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Error signing message"));
  }
  layoutHome();
}

void fsm_msgVerifyMessage(const VerifyMessage *msg) {
  CHECK_PARAM(msg->has_address, _("No address provided"));
  CHECK_PARAM(msg->has_message, _("No message provided"));

  const CoinInfo *coin = fsm_getCoin(msg->has_coin_name, msg->coin_name);
  if (!coin) return;
  layoutProgressSwipe(_("Verifying"), 0);
  if (msg->signature.size == 65 &&
      cryptoMessageVerify(coin, msg->message.bytes, msg->message.size,
                          msg->address, msg->signature.bytes) == 0) {
    layoutVerifyAddress(coin, msg->address);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
    layoutVerifyMessage(msg->message.bytes, msg->message.size);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
    fsm_sendSuccess(_("Message verified"));
  } else {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid signature"));
  }
  layoutHome();
}
