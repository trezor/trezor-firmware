/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2018 ZuluCrypto <zulucrypto@protonmail.com>
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

void fsm_msgStellarGetAddress(StellarGetAddress *msg)
{
    RESP_INIT(StellarAddress);

    CHECK_INITIALIZED

    CHECK_PIN

    HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
    if (!node) {
        fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to derive private key"));
        return;
    }

    if (msg->has_show_display && msg->show_display) {
        const char **str_addr_rows = stellar_lineBreakAddress(node->public_key + 1);
        layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), _("Share public account ID?"),
            str_addr_rows[0],
            str_addr_rows[1],
            str_addr_rows[2],
            NULL,
            NULL, NULL
            );
        if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
            fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
            layoutHome();
            return;
        }
    }

    resp->has_address = true;
    stellar_publicAddressAsStr(node->public_key + 1, resp->address, sizeof(resp->address));

    msg_write(MessageType_MessageType_StellarAddress, resp);

    layoutHome();
}

// void fsm_msgStellarGetPublicKey(StellarGetPublicKey *msg)
// {
//     RESP_INIT(StellarPublicKey);

//     CHECK_INITIALIZED

//     CHECK_PIN

//     HDNode *node = stellar_deriveNode(msg->address_n, msg->address_n_count);
//     if (!node) {
//         fsm_sendFailure(FailureType_Failure_ProcessError, _("Failed to derive private key"));
//         return;
//     }

//     if (msg->has_show_display && msg->show_display) {
//         char hex[32 * 2 + 1];
//         data2hex(node->public_key + 1, 32, hex);
//         const char **str_pubkey_rows = split_message((const uint8_t *)hex, 32 * 2, 16);
//         layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), _("Share public account ID?"),
//             str_pubkey_rows[0],
//             str_pubkey_rows[1],
//             str_pubkey_rows[2],
//             str_pubkey_rows[3],
//             NULL, NULL
//             );
//         if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
//             fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
//             layoutHome();
//             return;
//         }
//     }

//     // Read public key and write it to the response
//     resp->has_public_key = true;
//     resp->public_key.size = 32;
//     memcpy(resp->public_key.bytes, node->public_key + 1, 32);

//     msg_write(MessageType_MessageType_StellarPublicKey, resp);

//     layoutHome();
// }

void fsm_msgStellarSignTx(StellarSignTx *msg)
{
    CHECK_INITIALIZED
    CHECK_PIN

    stellar_signingInit(msg);

    // Confirm transaction basics
    stellar_layoutTransactionSummary(msg);

    // Respond with a request for the first operation
    RESP_INIT(StellarTxOpRequest);

    msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
}

void fsm_msgStellarCreateAccountOp(StellarCreateAccountOp *msg)
{
    if (!stellar_confirmCreateAccountOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarPaymentOp(StellarPaymentOp *msg)
{
    // This will display additional dialogs to the user
    if (!stellar_confirmPaymentOp(msg)) return;

    // Last operation was confirmed, send a StellarSignedTx
    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarPathPaymentOp(StellarPathPaymentOp *msg)
{
    if (!stellar_confirmPathPaymentOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarManageOfferOp(StellarManageOfferOp *msg)
{
    if (!stellar_confirmManageOfferOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarCreatePassiveOfferOp(StellarCreatePassiveOfferOp *msg)
{
    if (!stellar_confirmCreatePassiveOfferOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarSetOptionsOp(StellarSetOptionsOp *msg)
{
    if (!stellar_confirmSetOptionsOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarChangeTrustOp(StellarChangeTrustOp *msg)
{
    if (!stellar_confirmChangeTrustOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarAllowTrustOp(StellarAllowTrustOp *msg)
{
    if (!stellar_confirmAllowTrustOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarAccountMergeOp(StellarAccountMergeOp *msg)
{
    if (!stellar_confirmAccountMergeOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarManageDataOp(StellarManageDataOp *msg)
{
    if (!stellar_confirmManageDataOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}

void fsm_msgStellarBumpSequenceOp(StellarBumpSequenceOp *msg)
{
    if (!stellar_confirmBumpSequenceOp(msg)) return;

    if (stellar_allOperationsConfirmed()) {
        RESP_INIT(StellarSignedTx);

        stellar_fillSignedTx(resp);
        msg_write(MessageType_MessageType_StellarSignedTx, resp);
        layoutHome();
    }
    // Request the next operation to sign
    else {
        RESP_INIT(StellarTxOpRequest);

        msg_write(MessageType_MessageType_StellarTxOpRequest, resp);
    }
}
